<#
.SYNOPSIS
  Builds the Humlog Stories site and publishes it to https://humlog.upendragusain.co.uk/stories/

.DESCRIPTION
  The Stories site lives in a "stories/" folder of Humlog's website storage account (static website, $web).
  That account is firewalled to Cloudflare and Humlog's sync function only. To upload, this script
  briefly allows this PC's public IP, uploads, and ALWAYS removes the rule again (try/finally).
  Humlog's sync function only uploads its own files and never deletes, so it leaves stories/ alone.
  Privacy comes from Cloudflare Access (family login) on the whole hostname, as for Humlog.

.EXAMPLE
  ./deploy.ps1            # build + publish
  ./deploy.ps1 -SkipBuild # publish the existing site/ folder
  ./deploy.ps1 -SkipTv    # website only; leave the TV version as it is
#>
param(
    [string] $Subscription = 'UpendraPractice',
    [string] $ResourceGroup = 'rg-family-gallery',
    [string] $Prefix = 'stories',
    [switch] $SkipBuild,
    [switch] $SkipTv
)

$ErrorActionPreference = 'Continue'
function Invoke-Az { az @args; if ($LASTEXITCODE -ne 0) { throw "az $($args[0..2] -join ' ') failed" } }

$root = $PSScriptRoot
$site = Join-Path $root 'site'

if (-not $SkipBuild) {
    Write-Host 'Building site/'
    python -I -X utf8 (Join-Path $root 'tools/build_site.py')
    if ($LASTEXITCODE -ne 0) { throw 'build failed' }
}
if (-not (Test-Path (Join-Path $site 'index.html'))) { throw 'site/index.html missing' }

Invoke-Az account set --subscription $Subscription
$suffix = (az account show --query id -o tsv).Substring(0, 6)
$account = "sthumlog$suffix"
$key = az storage account keys list -n $account -g $ResourceGroup --query '[0].value' -o tsv
# This connection leaves through a small pool of public IPv4 addresses (different ones per
# connection), so allow the smallest aligned block (at least /29) that covers all of them.
$seen = foreach ($u in 'https://api.ipify.org', 'https://ifconfig.me/ip', 'https://ipv4.icanhazip.com', 'https://api.ipify.org') {
    try { (Invoke-RestMethod $u -TimeoutSec 8).Trim() } catch { }
}
$seen = $seen | Where-Object { $_ -match '^\d+\.\d+\.\d+\.\d+$' } | Sort-Object -Unique
if (-not $seen) { throw 'Could not determine this PC''s public IP' }
$toInt = { param($a) $o = $a.Split('.') | ForEach-Object { [uint32]$_ }; ($o[0] -shl 24) -bor ($o[1] -shl 16) -bor ($o[2] -shl 8) -bor $o[3] }
$ints = $seen | ForEach-Object { & $toInt $_ }
$lo = ($ints | Measure-Object -Minimum).Minimum; $hi = ($ints | Measure-Object -Maximum).Maximum
$bits = 29
while ($bits -gt 24 -and (([uint32]$lo -shr (32 - $bits)) -ne ([uint32]$hi -shr (32 - $bits)))) { $bits-- }
$base = ([uint32]$lo -shr (32 - $bits)) -shl (32 - $bits)
$ip = '{0}.{1}.{2}.{3}/{4}' -f (($base -shr 24) -band 255), (($base -shr 16) -band 255), (($base -shr 8) -band 255), ($base -band 255), $bits
Write-Host "Public addresses seen: $($seen -join ', ') -> allowing $ip"

# A blob named exactly "stories" redirects /stories to /stories/ so relative paths work.
$redirect = Join-Path ([IO.Path]::GetTempPath()) 'stories-redirect.html'
"<!doctype html><meta charset=utf-8><meta http-equiv=refresh content=`"0;url=/$Prefix/`"><link rel=canonical href=`"/$Prefix/`">" |
    Set-Content -Encoding utf8 $redirect

Write-Host "Temporarily allowing $ip on $account"
Invoke-Az storage account network-rule add -n $account -g $ResourceGroup --ip-address $ip -o none
try {
    # Firewall changes take a while to apply: wait until this PC can actually list the container.
    $ok = $false
    foreach ($i in 1..18) {
        az storage blob list --account-name $account --account-key $key -c '$web' --num-results 1 --only-show-errors -o none 2>$null
        if ($LASTEXITCODE -eq 0) { $ok = $true; break }
        Write-Host "  waiting for the firewall rule to apply ($($i * 10)s)"
        Start-Sleep -Seconds 10
    }
    if (-not $ok) { throw 'Storage still blocked after 3 minutes' }
    $common = @('--account-name', $account, '--account-key', $key, '-d', '$web', '--overwrite', '--only-show-errors')

    Write-Host "Uploading media, images, chapters -> `$web/$Prefix/"
    Invoke-Az storage blob upload-batch @common -s $site --destination-path $Prefix --pattern '*.m4a' `
        --content-type 'audio/mp4' --content-cache-control 'public, max-age=86400' -o none
    Invoke-Az storage blob upload-batch @common -s $site --destination-path $Prefix --pattern '*.jpg' `
        --content-type 'image/jpeg' --content-cache-control 'public, max-age=86400' -o none
    Invoke-Az storage blob upload-batch @common -s $site --destination-path $Prefix --pattern '*.js' `
        --content-type 'text/javascript; charset=utf-8' --content-cache-control 'no-cache' -o none
    Invoke-Az storage blob upload-batch @common -s $site --destination-path $Prefix --pattern '*.html' `
        --content-type 'text/html; charset=utf-8' --content-cache-control 'no-cache' -o none
    Invoke-Az storage blob upload --account-name $account --account-key $key -c '$web' -n $Prefix -f $redirect `
        --overwrite --content-type 'text/html; charset=utf-8' --content-cache-control 'no-cache' --only-show-errors -o none

    # TV version (site-tv/) under tv/stories/: Humlog's /tv rules apply there - no family login
    # (the TV's old browser can't do it), but Cloudflare requires the TV key on every request.
    $tv = Join-Path $root 'site-tv'
    if ($SkipTv) { Write-Host 'Skipping the TV version (-SkipTv)' }
    elseif (Test-Path (Join-Path $tv 'index.html')) {
        Write-Host "Uploading TV version -> `$web/tv/$Prefix/"
        $tvDest = "tv/$Prefix"
        foreach ($t in @(@('*.mp4', 'video/mp4', 'public, max-age=86400'), @('*.m4a', 'audio/mp4', 'public, max-age=86400'),
                         @('*.jpg', 'image/jpeg', 'public, max-age=86400'), @('*.js', 'text/javascript; charset=utf-8', 'no-cache'),
                         @('*.html', 'text/html; charset=utf-8', 'no-cache'))) {
            Invoke-Az storage blob upload-batch @common -s $tv --destination-path $tvDest --pattern $t[0] `
                --content-type $t[1] --content-cache-control $t[2] -o none
        }
    }

    # Count in PowerShell: a JMESPath "length(@)" breaks in az's Windows cmd shim (and echoes the command, key included).
    $count = @(az storage blob list --account-name $account --account-key $key -c '$web' --prefix "$Prefix/" --num-results 2000 --query '[].name' -o tsv --only-show-errors).Count
    Write-Host "Published $count files under $Prefix/"
}
finally {
    Write-Host "Removing $ip from $account firewall"
    az storage account network-rule remove -n $account -g $ResourceGroup --ip-address $ip -o none
    if ($LASTEXITCODE -ne 0) { Write-Warning "Could not remove firewall rule for $ip - remove it manually!" }
}
Write-Host "`nhttps://humlog.upendragusain.co.uk/$Prefix/"
