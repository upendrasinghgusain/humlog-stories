# The Stories That Made Us
## Family Oral History & Digital Archive
**Project Specification – Version 0.1**

**Status:** Initial concept / Discovery and MVP  
**Project type:** Personal family history, digital preservation and AI-assisted storytelling

---

# 1. Project Overview

## 1.1 Vision

Create a digital family history project that captures, preserves and presents the life stories, memories and experiences of three generations of the family:

- Grandmother
- Father
- Mother

The project will use recorded interviews, photographs, documents and other historical material to build a structured family archive.

The ultimate ambition is to create two complementary experiences:

**1. A cinematic family documentary**

An understated, high-quality documentary that tells the stories of family members through their own voices, personal photographs, historical context and carefully selected visual material.

**2. An interactive family history archive**

A structured and accessible representation of the family's history, allowing future generations to explore people, relationships, life events, locations, photographs and personal stories through timelines, family trees and other visualisations.

The project does not need to determine its final output immediately. The initial priority is to capture and organise information in a way that supports multiple future uses.

## 1.2 Guiding principles

1. Preserve original voices and memories. The recordings themselves are primary historical artefacts.
2. Authenticity over production value. Avoid artificial, exaggerated or overly sentimental storytelling.
3. Preserve before transforming. Original recordings and transcripts must remain unchanged.
4. Support multiple languages, particularly Hindi and English.
5. Distinguish personal recollections from independently verified historical facts.
6. Make the information accessible to people who are not technically inclined.
7. Design for future generations, not just current family members.
8. Use AI to assist with transcription, organisation, translation and creative production, not to invent memories.

---

# 2. Current State

The project has already started with some initial recordings.

### Existing material

| Person | Current material |
|---|---|
| Father | 3 interview recordings, approximately 10 minutes each |
| Father | Hindi transcripts generated using Google Recorder |
| Mother | Future recordings planned |
| Grandmother | Future recordings planned |

The existing recordings capture conversations about the father's life and experiences.

The recordings are currently relatively unstructured from a data perspective. They need to be organised, reviewed and converted into reusable information.

### Initial assumptions

- Interviews will primarily be conducted in Hindi.
- English translations may be required for wider family accessibility.
- Interviews will be recorded using a smartphone.
- Additional photographs and historical documents may be collected.
- The project will initially be private and accessible only to the family.

---

# 3. Overall Concept and Outputs

The project has one central information repository and multiple potential outputs.

## 3.1 Core family archive

The archive is the foundation of everything else.

It will contain:

- People and family relationships.
- Original audio recordings.
- Original Hindi transcripts.
- Corrected transcripts.
- English translations.
- Life events and milestones.
- Personal stories and memories.
- Photographs and documents.
- Locations and geographical information.
- Links between stories, people, events and source recordings.

The archive should be independent of any particular presentation format.

## 3.2 Output A: Cinematic family documentary

**Working title:** The Stories That Made Us

Create a documentary featuring the grandmother, father and mother.

The documentary should feel like an intimate, professionally produced personal-history film rather than an AI-generated slideshow.

### Potential content

- Childhood and family origins.
- Parents and grandparents.
- Growing up in India.
- Education and early experiences.
- Marriage and relationships.
- Work and professional life.
- Raising a family.
- Major life events and turning points.
- Changes in Indian society across generations.
- Personal reflections and lessons for future generations.

### Presentation style

- Use original recordings as the primary narration.
- Incorporate genuine family photographs and documents.
- Use subtle music and restrained transitions.
- Include historical photographs and geographical context where appropriate.
- Use AI-generated scenes selectively to illustrate memories that cannot be represented through existing photographs.
- Include Hindi audio with optional English subtitles.
- Use contemporary portraits and footage where possible.

### Important creative constraints

- Avoid AI avatars pretending to be family members.
- Do not fabricate historical events or present generated imagery as genuine archival material.
- Do not use AI voice cloning by default.
- Preserve the original recordings and their context.
- Clearly distinguish reconstructed scenes from real historical photographs.

### Potential deliverables

- A combined family documentary.
- Individual short documentaries for each family member.
- Short chapter-based videos.
- A collection of audio stories.

The final duration and format remain undecided.

## 3.3 Output B: Interactive family history archive

Create a simple visual interface that allows family members to explore their history.

The interface should prioritise accessibility and clarity over technical complexity.

### A. Family timeline

The primary view should be a chronological representation of significant family events.

Example:

| Period | Event | Person |
|---|---|---|
| 1950s | Childhood and early family life | Grandmother |
| 1960s | School and growing up | Father |
| 1970s | Early adulthood | Mother |
| Later years | Marriage and family | Mother and Father |
| Subsequent generations | Children and grandchildren | Family |

These dates are illustrative, not established historical facts.

Timeline capabilities:

- Display events chronologically.
- Filter by family member.
- Display approximate and confirmed dates differently.
- Group events by historical period.
- Open an event to see its associated story.
- Link events to photographs, recordings and transcripts.
- Show events involving multiple family members.

### B. Individual biographies

Each family member should have a profile.

Potential information:

- Name and family relationships.
- Birthplace and approximate birth date.
- Childhood.
- Education.
- Work and career.
- Marriage and children.
- Important life events.
- Places lived.
- Personal stories.
- Photographs and documents.
- Audio and video recordings.

### C. Family relationship graph

Provide a family tree or relationship visualisation.

It should show:

- Parents and children.
- Siblings.
- Spouses.
- Grandparents and earlier generations.
- Relationships between the three main interview subjects.

Selecting a person should open their profile.

### D. Geographical history

Optionally introduce a map showing:

- Birthplaces.
- Villages and towns where family members grew up.
- Schools and workplaces.
- Places lived.
- Significant family locations.

Each location can be linked to memories, photographs and events.

### E. Story explorer

Allow users to explore memories by topic rather than only by date.

Example categories:

- Childhood.
- Education.
- Marriage.
- Family.
- Food and traditions.
- Work.
- Relationships.
- Historical events.
- Life lessons.

---

# 4. Information Model

The archive should use structured information rather than relying exclusively on unstructured transcripts.

The initial data model should contain the following entities.

## 4.1 Person

Represents an individual in the family.

Suggested attributes:

- Person ID.
- Full name.
- Alternative names and spellings.
- Date of birth (if known).
- Place of birth.
- Biography.
- Family relationships.
- Associated photographs.

## 4.2 Recording

Represents an original interview or recording.

Suggested attributes:

- Recording ID.
- Person interviewed.
- Recording date.
- Original filename.
- File location.
- Duration.
- Language.
- Recording description.
- Associated transcript.
- Topics covered.

## 4.3 Transcript

Represents the written version of a recording.

Maintain separate versions:

- Original machine-generated transcript.
- Corrected original-language transcript.
- English translation.
- Optional edited narrative version.

Each transcript should retain timestamps or segment references to the original recording wherever possible.

## 4.4 Story

Represents a meaningful recollection or narrative extracted from an interview.

Suggested attributes:

- Story ID.
- Title.
- Description.
- Person or people involved.
- Approximate historical period.
- Location.
- Associated events.
- Source recording.
- Transcript start and end timestamps.
- Photographs.
- Topics or tags.

## 4.5 Event

Represents a significant occurrence in family history.

Examples:

- Birth.
- Starting school.
- Moving to another town.
- First job.
- Marriage.
- Birth of a child.
- Retirement.

Suggested attributes:

- Event ID.
- Title.
- Description.
- Date or approximate date.
- People involved.
- Location.
- Related stories.
- Evidence and source references.
- Confidence or verification status.

## 4.6 Place

Represents a geographical location.

Suggested attributes:

- Place ID.
- Name.
- Alternative names.
- Region.
- Country.
- Coordinates, if known.
- Description.
- Associated people and events.

## 4.7 Media

Represents photographs, scanned documents and other supporting material.

Suggested attributes:

- Media ID.
- File location.
- Media type.
- Description.
- Date or approximate date.
- People depicted.
- Related stories and events.
- Original or restored status.

---

# 5. AI-Assisted Processing Pipeline

AI should help convert raw recordings into structured, reusable family-history information.

The processing pipeline should be repeatable.

### Step 1: Ingestion

Import the original audio recording and the Google Recorder transcript.

Preserve both without modification.

### Step 2: Transcript correction

Review the Hindi transcript.

Correct:
- Speech recognition mistakes.
- Names and locations.
- Incorrect words.
- Punctuation and paragraph structure.

Do not rewrite the person's speech into polished prose.

### Step 3: Translation

Produce an English translation while retaining the original Hindi transcript.

Translation should preserve meaning, tone and culturally specific expressions.

### Step 4: Story extraction

Use an LLM to identify:

- Significant memories.
- People mentioned.
- Events.
- Dates and time periods.
- Locations.
- Family relationships.
- Cultural references.
- Personal reflections.

Produce structured JSON or equivalent records.

### Step 5: Review and verification

All extracted information should be reviewable.

Distinguish:

- Explicitly stated information.
- Approximate recollections.
- Inferred information.
- Independently verified information.
- Conflicting recollections.

Do not silently resolve discrepancies between family members.

### Step 6: Archive publication

Approved information becomes available to the timeline, biographies, relationship graph and story explorer.

### Step 7: Creative production

Selected stories can be used to produce:

- Documentary scripts.
- Audio episodes.
- Short videos.
- Illustrated historical scenes.
- Printed family memoirs.

All creative outputs should reference their source material.

---

# 6. Technical Architecture

The project should initially favour simplicity and avoid unnecessary infrastructure.

Potential technology choices:

| Component | Proposed technology |
|---|---|
| Frontend | Angular |
| Backend | ASP.NET Core Web API |
| Database | PostgreSQL or Azure SQL |
| File storage | Local storage initially, Azure Blob Storage later |
| AI processing | LLM with structured output |
| Transcription | Google Recorder initially |
| Translation | LLM-assisted |
| Search | Database search initially, Azure AI Search later |
| Timeline | Angular visualisation component |
| Relationship graph | Cytoscape.js or similar |
| Maps | MapLibre or equivalent |
| Video production | DaVinci Resolve |
| AI video generation | Veo, Runway or equivalent |

### Architectural principle

Keep the original archive separate from the application.

The database should contain metadata and relationships, while original media files should be stored independently.

This ensures that the archive remains portable even if the application is replaced.

Avoid introducing microservices, event-driven architecture or a graph database at the initial stage.

A modular monolithic application is sufficient.

---

# 7. MVP Scope

The first milestone should demonstrate the complete journey from a recording to an accessible family-history experience.

It should not attempt to implement the entire vision.

## MVP objectives

1. Import the three existing recordings of Dad.
2. Store original audio files.
3. Store original Hindi transcripts.
4. Support corrected Hindi transcripts and English translations.
5. Extract people, stories, events and approximate dates.
6. Allow manual correction and approval of extracted information.
7. Create an initial family timeline.
8. Provide a basic individual profile for Dad.
9. Link timeline events to their original recordings and transcript passages.
10. Support adding Mum and Grandma as additional people, even before their interviews are complete.

## MVP user experience

The initial interface should contain:

**Home**
- Project overview.
- Three family member profiles.
- Latest recordings.
- Timeline preview.

**People**
- Individual family profiles.
- Biographical information.
- Associated stories and recordings.

**Timeline**
- Chronological family events.
- Filters by person.
- Clickable events.

**Recordings**
- List of interviews.
- Audio playback.
- Transcript display.
- Linked stories.

**Story details**
- Story summary.
- Original Hindi passage.
- English translation.
- Recording reference and timestamp.
- Associated people, events and photographs.

## MVP acceptance criteria

The MVP is successful when:

- The three existing recordings can be imported and played.
- Their original transcripts are preserved.
- A corrected transcript and English translation can be associated with each recording.
- AI can suggest structured memories and events.
- A human can review and approve the suggestions.
- Approved events appear on a family timeline.
- Selecting an event provides access to its source story and recording.
- Additional family members and recordings can be added without redesigning the application.

---

# 8. Future Opportunities

These are potential directions, not commitments for the initial implementation.

## 8.1 Cinematic documentary production

Create a documentary using original voices, photographs, historical footage and AI-generated visualisations.

## 8.2 Family history chatbot

Allow family members to ask questions about their history.

Answers should be grounded in the archive and reference the original recordings.

Example:

"What did Grandmother say about her childhood home?"

The application should retrieve relevant memories and allow the user to listen to the original passage.

If the information is unavailable, the assistant should say so.

## 8.3 Audio storytelling

Produce short audio episodes using original recordings, introductions and supporting historical context.

## 8.4 Historical context

Add independently researched information about India during the periods described in the interviews.

This could include:

- Major historical events.
- Social and economic changes.
- Education.
- Technology.
- Cultural traditions.
- Historical photographs and maps.

Clearly distinguish historical research from personal recollections.

## 8.5 Printed family memoir

Produce a professionally designed book combining:

- Personal stories.
- Original quotations.
- Family photographs.
- Family trees.
- Maps.
- Historical context.

## 8.6 Extended family

Allow additional relatives and generations to contribute their memories and photographs.

---

# 9. Non-Functional Requirements and Preservation

The archive contains personal and potentially sensitive family information.

The following requirements are important.

### Preservation

- Never overwrite original recordings.
- Retain original transcripts.
- Store derived content separately.
- Maintain source references for extracted information.
- Support regular backups.
- Avoid proprietary formats wherever practical.

### Accuracy

- Distinguish known dates from estimated dates.
- Retain contradictory recollections.
- Do not invent biographical details.
- Preserve the original language.
- Provide traceability from every published story to its source.

### Privacy

- Default to private access.
- Obtain permission before publishing recordings or photographs.
- Control access to personal information.
- Do not use family recordings to train or publish voice replicas without explicit permission.

### Usability

- Mobile-friendly interface.
- Simple navigation.
- Clear visual timeline.
- Easy playback of recordings.
- Readable Hindi and English text.
- Accessible to non-technical family members.

---

# 10. Proposed Roadmap

| Phase | Focus | Outcome |
|---|---|---|
| 0 | Capture | Recordings and transcripts organised |
| 1 | Foundation | File archive and basic data model |
| 2 | Processing | Transcript correction, translation and AI extraction |
| 3 | Visualisation | Profiles, stories and family timeline |
| 4 | Creative | First documentary prototype |
| 5 | Expansion | Mum and Grandma integrated |
| 6 | Exploration | Search, chatbot, map and family memoir |

Phases do not need to be completed strictly in sequence. Capturing family interviews should continue throughout.

---

# 11. Initial Project Backlog

The first practical tasks are:

- [ ] Create a repository for the application.
- [ ] Establish a structured folder for original recordings and transcripts.
- [ ] Import the three existing recordings of Dad.
- [ ] Record metadata for each recording.
- [ ] Review the existing Hindi transcripts.
- [ ] Create English translations.
- [ ] Define the initial database schema.
- [ ] Define structured JSON schemas for people, events and stories.
- [ ] Build an initial ingestion workflow.
- [ ] Build the family member profile page.
- [ ] Build the first chronological timeline.
- [ ] Link stories to their original audio and timestamps.
- [ ] Add Mum and Grandma as family members.
- [ ] Record additional interviews.
- [ ] Produce a first 60–90 second documentary prototype.

---

# 12. Open Decisions

The following decisions remain deliberately unresolved:

1. Whether the final documentary will be one combined film or three individual biographies.
2. Whether the archive will be a private website, a locally hosted application or a cloud-hosted application.
3. Whether Hindi will remain the primary presentation language, with English translations.
4. How much historical research and external archival material to incorporate.
5. Whether the documentary will use AI-generated scenes or primarily genuine photographs and footage.
6. Whether the archive will eventually support extended family contributions.
7. Whether to build a conversational family-history assistant.

These decisions should be informed by the material collected and the experience of building the initial MVP.

---

# 13. Definition of Success

The project should ultimately allow a future family member to:

- Understand who their grandparents and great-grandparents were.
- Explore their lives chronologically.
- Understand how the family evolved across generations.
- Discover personal stories in the original voices of family members.
- See photographs and places associated with those memories.
- Watch a documentary that brings the family's history together.
- Ask questions and discover information without needing to know which recording contains the answer.

**The fundamental objective is not to create a sophisticated AI application. It is to preserve a family's memories in a form that future generations can understand, explore and experience.**

The application and creative outputs are simply different ways of achieving that objective.