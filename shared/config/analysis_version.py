"""Single source of truth for analysis versioning + freshness evaluation.

Why this exists
---------------
Repository analysis is expensive and persisted (Postgres + ChromaDB). Once
stored, it can outlive the code that produced it: the dependency-graph logic
changes, the persisted schema grows a column, or the embedding model is
swapped. Without version stamps we would *silently* serve results that were
produced by an older pipeline — exactly the failure mode we want to avoid.

Every completed analysis is stamped with three monotonically-increasing
integers plus the embedding signature it was indexed with. On read we compare
the stored stamps against the constants below to decide whether the analysis is
``fresh``, ``stale`` (older pipeline / schema), or ``unknown`` (analyzed before
versioning existed). The UI surfaces this and offers a one-click refresh.

When to bump
------------
* ``ANALYSIS_VERSION``  — analysis *output* or graph/metric logic changed in a
  way that makes old results misleading (e.g. new edge kinds, fixed cycle
  detection, new dead-code heuristic).
* ``PIPELINE_VERSION``  — the orchestration/cloning pipeline changed (e.g. clone
  depth, file-selection rules) without necessarily changing the data shape.
* ``SCHEMA_VERSION``    — the *persisted* shape changed (new column/table a
  feature reads). Old rows lack the data, so dependent features must gate.

Keep bumps deliberate and paired with a feature's ``min_*`` requirement below.
"""
from __future__ import annotations

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Current versions. Bump deliberately (see module docstring).
# ---------------------------------------------------------------------------
ANALYSIS_VERSION = 1
PIPELINE_VERSION = 1
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FeatureRequirement:
    """Minimum stamps a stored analysis needs to fully back a feature."""

    key: str
    label: str
    min_analysis_version: int = 1
    min_schema_version: int = 1
    requires_embeddings: bool = False


# Product features that consume persisted analysis. ``affected_features`` on a
# freshness verdict is derived from these so the UI can tell the user *exactly*
# what is impacted by an out-of-date analysis.
FEATURES: tuple[FeatureRequirement, ...] = (
    FeatureRequirement("code_metrics", "Code metrics"),
    FeatureRequirement("dependency_graph", "Dependency graph"),
    FeatureRequirement("architecture", "Architecture map"),
    FeatureRequirement("dead_code", "Dead-code detection"),
    FeatureRequirement("ai_assistant", "AI assistant", requires_embeddings=True),
)


def embedding_signature(provider: str, model: str) -> str:
    """Stable identifier for the embedding strategy an index was built with.

    Two analyses are only AI-compatible if their embedding signatures match —
    vectors produced by different models are not comparable.
    """
    return f"{provider}:{model}"


# Freshness verdict states.
FRESH = "fresh"          # stamps match the current pipeline
STALE = "stale"          # produced by an older but known pipeline
UNKNOWN = "unknown"      # analyzed before versioning (no stamps recorded)
UNAVAILABLE = "unavailable"  # no completed analysis to evaluate


@dataclass(frozen=True)
class FreshnessVerdict:
    """Outcome of comparing a stored analysis against current versions."""

    state: str
    reasons: tuple[str, ...]
    affected_features: tuple[str, ...]
    can_refresh: bool

    @property
    def is_current(self) -> bool:
        return self.state == FRESH


def evaluate_freshness(
    *,
    is_ready: bool,
    analysis_version: int | None,
    pipeline_version: int | None,
    schema_version: int | None,
    embedding_model: str | None,
    current_embedding_model: str | None,
) -> FreshnessVerdict:
    """Compare a stored analysis's stamps against the current pipeline.

    ``current_embedding_model`` is the signature the *backend* is configured
    for right now; pass ``None`` to skip the AI-index comparison (e.g. when it
    cannot be determined). All comparisons are conservative: anything we cannot
    positively confirm as current is treated as needing a refresh.
    """
    if not is_ready:
        return FreshnessVerdict(UNAVAILABLE, (), (), can_refresh=False)

    # Legacy rows analyzed before versioning carry no stamps at all.
    if analysis_version is None or schema_version is None or pipeline_version is None:
        return FreshnessVerdict(
            UNKNOWN,
            ("This repository was analyzed before version tracking was introduced.",),
            tuple(f.label for f in FEATURES),
            can_refresh=True,
        )

    reasons: list[str] = []
    affected: set[str] = set()

    if analysis_version < ANALYSIS_VERSION:
        reasons.append(
            f"Analyzed with an older analysis version (v{analysis_version}; "
            f"current v{ANALYSIS_VERSION})."
        )
    if pipeline_version < PIPELINE_VERSION:
        reasons.append(
            f"The analysis pipeline has been upgraded (v{pipeline_version} → "
            f"v{PIPELINE_VERSION})."
        )
    if schema_version < SCHEMA_VERSION:
        reasons.append(
            f"A newer data schema is available (v{schema_version} → "
            f"v{SCHEMA_VERSION})."
        )

    # Features whose minimum requirements outrun the stored stamps.
    for feature in FEATURES:
        if (
            analysis_version < feature.min_analysis_version
            or schema_version < feature.min_schema_version
        ):
            affected.add(feature.label)

    # AI index built with a different embedding model is not comparable.
    if (
        current_embedding_model is not None
        and embedding_model is not None
        and embedding_model != current_embedding_model
    ):
        reasons.append(
            "The AI assistant was indexed with a different embedding model "
            f"({embedding_model} → {current_embedding_model})."
        )
        for feature in FEATURES:
            if feature.requires_embeddings:
                affected.add(feature.label)

    if not reasons:
        return FreshnessVerdict(FRESH, (), (), can_refresh=False)

    # If the analysis is behind, every feature is at least worth re-checking;
    # but only report the ones we can concretely tie to a gap, falling back to
    # "all" when a global version moved.
    if not affected:
        affected = {f.label for f in FEATURES}

    return FreshnessVerdict(
        STALE,
        tuple(reasons),
        tuple(sorted(affected)),
        can_refresh=True,
    )
