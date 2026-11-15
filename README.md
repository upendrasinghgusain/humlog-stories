# Humlog Stories

A private family oral-history site: a parent's life told in their own voice, as a timeline of moments
you can play, with Hindi and English captions, illustrated story chapters and real family photographs.

It is a companion to [Humlog](https://github.com/upendrasinghgusain/humlog) (the family photo slideshow)
and is served from the same site, behind the same family login:

| Who | Address |
|---|---|
| Family (phone, laptop) | `https://<humlog domain>/stories/` — Cloudflare Access login |
| Parents' LG TV (old webOS browser) | `https://<humlog domain>/tv/stories/?key=<TV key>` — no login, key checked by Cloudflare |

## This repository holds code only

The family archive — recordings, transcripts, photos, life events, chapter words and audio — is **never
committed** (see `.gitignore`). It lives on the owner's machine in `media/` and `archive/`, and the
built sites (`site/`, `site-tv/`) contain it, so they are ignored too. Secrets (`.env`) are ignored.

## How it fits together

```
media/                  originals (private): interview audio, photos, photos.json, family-context.md
archive/derived/        AI drafts (private): transcripts, events.json, edited photos
stories/<chapter>/      a chapter: story.config.json, scenes, audio, paintings (private) + index.html (player)
site-src/               the site: index.html (phones/desktop), tv.html (the TV)
tools/                  the pipeline (Python)
deploy.ps1              build + publish to the Humlog storage account
```

| Step | Tool |
|---|---|
| Transcribe an interview (Gemini, 1-minute chunks for accurate timestamps) | `tools/transcribe_chunked.py` |
| Extract life events, each linked to its recording and minute | `tools/extract_events.py` |
| Prepare photos (only crop / straighten / tone; originals untouched) | `tools/photos.py` |
| Paint illustrations for a chapter (clearly labelled as illustrations) | `tools/illustrate.py` |
| Build a chapter: cut Dad's passages, join with room tone, music bed | `tools/build_story.py` |
| Render a chapter to MP4 (parallel headless Chrome, frame by frame) | `tools/render_video.py` |
| Build both sites | `tools/build_site.py` |
| Serve locally (with audio seeking) | `tools/serve.py` |
| Publish | `deploy.ps1` |

Requirements: Python 3.12 (+ `playwright`, `pillow`), ffmpeg, Azure CLI, a Gemini API key in `.env`
(`GEMINI_API_KEY=...`).

## Principles

From the project spec (`spec.md`): preserve original voices and never modify originals; AI assists with
transcription, translation and illustration but never invents memories; illustrations, photographs,
approximate dates and unchecked AI transcripts are always labelled as such; private by default.
