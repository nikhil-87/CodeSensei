# Feature: Insights (Complexity, Dead Code, Impact)

Three read-only analyses share the same shape: a backend service builds a read-model from
persisted analysis rows; a frontend page renders it behind the analysis gate.

## Complexity
**What:** ranks files by cyclomatic complexity; shows a chart + a detail table (LOC,
cognitive, functions, classes).
**Why:** surfaces the riskiest, hardest-to-change files.
- **API:** `GET /repositories/{id}/complexity?top_n=` → `ComplexityRanking`.
- **Service:** `MetricService.complexity_ranking` (reads `metrics`, index `ix_metrics_cyclomatic`).
- **Frontend:** `ComplexityPage` + `ComplexityChart` (vertical bars desktop, **horizontal
  bars on mobile** via `useMediaQuery` so file labels stay readable) + a table wrapped in
  `overflow-x-auto`.

## Dead Code
**What:** lists symbols that appear unused, with kind, location, confidence, and reason.
**Why:** find removable code and reduce maintenance surface.
- **API:** `GET /repositories/{id}/dead-code` → `DeadCodeReport`.
- **Service:** `DeadCodeService.report` (reads `symbols.is_used` / `usage_count`, index
  `symbols(is_used)`).
- **Frontend:** `DeadCodePage` + `DeadCodeTable` (sortable, horizontally scrollable).
- **Caveat:** dead-code detection is heuristic; dynamic/reflective usage can produce false
  positives — hence a **confidence** score, not a verdict.

## Impact Analysis
**What:** pick a file → see transitive dependents and dependencies, chain depths, and a
0–100 **criticality** score with a label (Low/Moderate/High/Critical).
**Why:** answer "what breaks if I change this?" before changing it.
- **API:** `POST /repositories/{id}/impact` → `ImpactAnalysisResponse`.
- **Service:** `ImpactService.analyze` (traverses `dependencies`).
- **Frontend:** `ImpactAnalysisPage`; the same math (`computeImpact`) also powers the graph
  inspector's criticality meter.

## Common edge cases
- Not-yet-analyzed repos are blocked by `AnalysisGate`.
- Empty results render friendly empty states.
- Insight queries are cached (5-min staleness client-side; Redis server-side).

## Security
- All three are gated by `verify_repository_access` (owner or public).

## Future improvements
- Trend lines across analyses (needs analysis history retention).
- Function-level impact once symbol/call edges exist.
