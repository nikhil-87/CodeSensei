# Behavioral (STAR) Stories from this Project

Reusable STAR answers grounded in real work on CodeSensei. Adapt the framing to the exact
question.

## "Tell me about a hard technical problem you solved."
- **Situation:** The dependency graph occasionally rendered blank or as a faint "translucent"
  smear.
- **Task:** Find and fix the root cause without hacks.
- **Action:** I inspected the live Cytoscape instance (since the canvas can't be
  screenshotted) and found the zoom clamped at max (2.5×) with nodes panned off-screen. The
  cose-bilkent layout's `animate:"end"` fit had latched onto the collapsed pre-animation
  positions. I switched to a deterministic layout and re-fit after the layout settled. A
  *separate* "wide thing covering the graph" turned out to be a global `.cytoscape-host > div`
  CSS rule stretching my new controls overlay — fixed by excluding overlays with
  `:not([data-graph-overlay])`.
- **Result:** Graph reliably auto-fits and renders; documented both bugs in the
  troubleshooting guide so they can't recur.

## "Tell me about a time you prevented a production-style failure."
- **Situation:** Workers can crash mid-analysis (OOM on large repos), leaving repos stuck
  "analyzing" forever, and double "Analyze" clicks could run duplicate work.
- **Task:** Make the job system self-healing and duplicate-safe.
- **Action:** Added a **partial unique index** so the database forbids two active jobs per
  repo (duplicate → `409`), and a **heartbeat column + background reaper** that fails stale
  jobs and resets their repos. Added an immediate startup sweep to clear orphans from a crash.
- **Result:** Crashes self-recover, the user can retry, and concurrent submits can't
  double-process. Verified by seeding a stuck job and watching the reaper resolve it.

## "Tell me about a time you fixed something the 'right' way instead of the quick way."
- **Situation:** Repository cards looked "cut off on the right" on mobile. My first instinct
  (and first patch) was `overflow-x-hidden`.
- **Task:** The user pushed back — clipping hides content, it's not a fix.
- **Action:** I reproduced it by forcing a classic scrollbar (headless uses zero-width overlay
  scrollbars), found the scrollbar was painting over the card's padding, and fixed it properly
  with `scrollbar-gutter: stable` plus `min-w-0`/truncation so content reflows instead of
  being clipped.
- **Result:** Cards stay fully visible across all viewports; I learned to reproduce
  environment-specific rendering before "fixing" it.

## "Tell me about designing for change / portability."
- **Situation:** The app had to run locally (Ollama, containers) and on free tiers (Groq,
  HuggingFace, Neon, Upstash) and migrate between them.
- **Task:** Avoid code changes per environment.
- **Action:** Put every external provider behind a small interface selected by env vars, with
  centralized defaults in `shared/`. Migration became a `.env` change + a `pg_dump`.
- **Result:** "Codespaces → Oracle Cloud" is configuration, not code. I can demo the same
  binary against four different provider stacks.

## "Tell me about handling honest feedback / iterating with a stakeholder."
- **Situation:** Across the responsive-design and graph work, the reviewer repeatedly flagged
  band-aid fixes (clipping overflow, hiding scrollbars).
- **Task:** Diagnose root causes instead of masking symptoms.
- **Action:** For each, I measured the actual DOM/instance state, identified the true cause
  (flex-height chain, scrollbar gutter, layout fit timing, CSS overlay rule), fixed it, and
  recorded the lesson in the docs.
- **Result:** A genuinely polished, responsive product and a troubleshooting guide that
  encodes the lessons.

## "What are you most proud of / what would you change?"
Proud of the **completeness**: a real distributed system (queue, worker, vector store,
migrations, observability, security) that runs on $0 and is documented well enough to hand
off. I'd change the dependency graph to symbol/call level and move rate limiting to Redis next
— I can articulate exactly why those are the highest-leverage upgrades.
