# NoteTube AI — Redesign & Notes Sprint (July 4-5, 2026)

## Landing Page / Dashboard
- Near-black theme (#07080c / #0b0d14) with indigo-violet accent, radial hero glow
- Product-as-hero: glowing animated gradient border on URL input, example video chips, social proof line ("679+ videos · ~60 seconds")
- Animated output preview (video → notes/chapters/flashcards generating) for guests & empty accounts
- Bento feature grid: large "Take Me There" tile with mock search UI, flip-on-hover flashcard tile
- VideoCard restyled to match (rounded-2xl, hover lift)
- Fixed: Sign Out dropdown unclickable (header z-index below main content)

## Video Workspace Page
- Tabs redesigned: pill style with icons — 📝 Summary | 📜 Transcript | 💬 Chat | 🎓 Study
- **Summary is now the default tab** (was hidden behind a "View Summary" modal — removed)
- Summary tab: TL;DR gradient card → Overview → Key Points (emoji + clickable timestamp chips) → Action Items (card sections)
- **Study tab**: segmented Breakdown/Flashcards switcher + Download Notes dropdown (Notes section planned here later)
- **Notes tab removed** (barely used; PDF export replaces it)
- Selection popup: single prominent "✨ Explain in Chat" action (Take Notes removed, passive bottom banner removed)
- Header removed → floating back button + processing badge; player enlarged (56vh)
- Duplicate video title removed
- Transcript fills full panel height (removed 600px cap)
- ProcessingPanel: step checklist with live check/spinner states, gradient progress bar
- Auth callback page: gradient spinner ring, feature teaser chips

## Backend — AI Pipeline
- **Groq removed entirely** — OpenAI only (`ai_provider.py` rewritten)
- Structured notes prompt (Eightify-style): new `tldr` field, bullets as `{emoji, text, time, seconds}` objects, inline `suggested_prompts` (saves one AI call)
- New DB columns: `notes.tldr`, `notes.short_notes` (migrations `9574feba1aed`, `50ac98cc3f79`)
  - ⚠️ **Run `alembic upgrade head` on production deploy**
- Schema: `bullets: List[Union[str, BulletSchema]]` (legacy string bullets still supported)

## Worker — Two-Phase Parallel Pipeline
- Phase A (parallel): chapters + structured notes + embeddings (embeddings moved out of the sequential path)
- Phase B (parallel): detailed + short downloadable notes, both **chapter-anchored map-reduce** — each chapter's transcript slice gets its own parallel AI call, stitched in order
  - Guarantees full-video coverage; length scales naturally (~1 page/chapter detailed, ~⅓ short)
  - Verified: 40-min video, 22 chapters → 22/22 sections, ~53K chars detailed notes
- Both notes styles non-fatal; on-demand endpoint regenerates if missing

## Download Notes (PDF)
- "Download Notes" dropdown in Study tab: 📚 Detailed Notes / ⚡ Short Notes
- Client-side PDF via @react-pdf/renderer (lazy-loaded), markdown → PDF renderer, Twemoji for emoji
- Endpoint: `POST /api/videos/{id}/study-notes?style=detailed|short` — cached per style (`markdown_notes` / `short_notes`)
- New videos: both styles pre-generated during processing → instant download
- Old videos: generated on first download (~15-20s), then cached
- Mixpanel: `notes_pdf_downloaded` with style + cached

## Known TODOs
- Download UX: tell user "stay on this page" while notes generate (first-time old videos)
- Notes section inside Study tab (user notes return later)
- Chat → teacher persona + voice mode (researching)
- Local cached notes were cleared for regeneration; production old videos self-heal lazily

## Analytics Context (Mixpanel, June 2026)
- 108 videos submitted, 62% success; 86% guest usage; Reddit = 70% of traffic
- Notes = most-clicked feature; chat clicks high but only 5 messages ever → pre-warmed chat + Explain-in-Chat shipped to fix
