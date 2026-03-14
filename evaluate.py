from __future__ import annotations

"""
Diversity metric evaluation for the exemplar question set.
Computes a composite score from skill coverage, embedding spread, and archetype diversity.
"""

import json
import numpy as np
from typing import Optional

# ─── Skill Coverage ───────────────────────────────────────────────────────────

ALL_SKILLS = [
    "FUNC_DOMAIN", "FUNC_COMPOSITE", "FUNC_INVERSE", "FUNC_TRANSFORM",
    "FUNC_QUADRATIC", "FUNC_RATIONAL", "FUNC_EXP", "FUNC_LOG",
    "FUNC_MODULUS", "FUNC_POLYNOMIAL", "FUNC_SUM_PRODUCT_ROOTS", "FUNC_GRAPH_SKETCH",
]

ALL_ARCHETYPES = [
    "prove", "find/solve", "sketch/graph", "interpret/explain",
    "model/apply", "show that", "multi-step synthesis",
]


def skill_coverage_score(questions: list[dict]) -> float:
    """
    Measures how evenly questions are distributed across the 12 Functions sub-skills.
    Returns 0-1 where 1 = perfectly even distribution.
    """
    n = len(questions)
    if n == 0:
        return 0.0

    counts = {s: 0 for s in ALL_SKILLS}
    for q in questions:
        skill = q.get("skill", "FUNC_POLYNOMIAL")
        if skill in counts:
            counts[skill] += 1

    values = list(counts.values())
    # Perfect distribution would have each skill at n/len(ALL_SKILLS)
    ideal = n / len(ALL_SKILLS)
    # Max possible std dev: all questions on one skill
    max_std = np.sqrt(ideal**2 * (len(ALL_SKILLS) - 1) / len(ALL_SKILLS) + (n - ideal)**2 / len(ALL_SKILLS))

    if max_std == 0:
        return 1.0

    actual_std = np.std(values)
    return float(1.0 - (actual_std / max_std))


# ─── Embedding Spread ─────────────────────────────────────────────────────────

def embedding_spread_score(embeddings: list[list[float]]) -> float:
    """
    Mean pairwise cosine distance between all question embeddings.
    Returns 0-1 where 1 = maximally spread out.
    """
    n = len(embeddings)
    if n < 2:
        return 0.0

    vecs = np.array(embeddings, dtype=np.float64)
    # Normalize
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    vecs = vecs / norms

    # Pairwise cosine similarity matrix
    sim_matrix = vecs @ vecs.T

    # Extract upper triangle (excluding diagonal)
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    similarities = sim_matrix[mask]

    # Convert to distances (1 - similarity), then take mean
    distances = 1.0 - similarities
    mean_dist = float(np.mean(distances))

    # Normalize: cosine distance is in [0, 2], but for unit vectors typically [0, 1]
    # Clip to [0, 1] for safety
    return min(max(mean_dist, 0.0), 1.0)


# ─── Archetype Diversity ──────────────────────────────────────────────────────

def archetype_diversity_score(questions: list[dict]) -> float:
    """
    Fraction of distinct archetypes present in the question set.
    Returns 0-1 where 1 = all archetypes represented.
    """
    if not questions:
        return 0.0

    present = set(q.get("archetype", "find/solve") for q in questions)
    return len(present & set(ALL_ARCHETYPES)) / len(ALL_ARCHETYPES)


# ─── Composite Score ──────────────────────────────────────────────────────────

def diversity_score(
    questions: list[dict],
    embeddings: Optional[list[list[float]]] = None,
) -> dict:
    """
    Compute the composite diversity score.

    Returns a dict with individual sub-scores and the composite.
    If embeddings are not provided, embedding_spread defaults to 0
    and its weight is redistributed.
    """
    skill = skill_coverage_score(questions)
    archetype = archetype_diversity_score(questions)

    if embeddings is not None and len(embeddings) >= 2:
        spread = embedding_spread_score(embeddings)
        composite = 0.40 * skill + 0.35 * spread + 0.25 * archetype
    else:
        # No embeddings — redistribute weight
        spread = None
        composite = 0.60 * skill + 0.40 * archetype

    return {
        "composite": round(composite, 6),
        "skill_coverage": round(skill, 6),
        "embedding_spread": round(spread, 6) if spread is not None else None,
        "archetype_diversity": round(archetype, 6),
    }


# ─── Skill Gap Analysis (used by mutate.py) ──────────────────────────────────

def find_diversity_gaps(questions: list[dict]) -> dict:
    """
    Analyze the question set and return actionable gap information.
    Used by mutate.py to tell Gemini what to target.
    """
    from collections import Counter

    skill_counts = Counter(q.get("skill", "FUNC_POLYNOMIAL") for q in questions)
    arch_counts = Counter(q.get("archetype", "find/solve") for q in questions)

    # Skills with zero or lowest representation
    missing_skills = [s for s in ALL_SKILLS if skill_counts.get(s, 0) == 0]
    if not missing_skills:
        min_count = min(skill_counts.values())
        missing_skills = [s for s, c in skill_counts.items() if c == min_count]

    # Most over-represented skill
    overrep_skill = skill_counts.most_common(1)[0][0] if skill_counts else None

    # Missing archetypes
    missing_archs = [a for a in ALL_ARCHETYPES if arch_counts.get(a, 0) == 0]
    if not missing_archs:
        min_count = min(arch_counts.values())
        missing_archs = [a for a, c in arch_counts.items() if c == min_count]

    # Most over-represented archetype
    overrep_arch = arch_counts.most_common(1)[0][0] if arch_counts else None

    return {
        "skill_counts": dict(skill_counts),
        "archetype_counts": dict(arch_counts),
        "underrepresented_skills": missing_skills,
        "overrepresented_skill": overrep_skill,
        "underrepresented_archetypes": missing_archs,
        "overrepresented_archetype": overrep_arch,
    }


if __name__ == "__main__":
    with open("questions.json") as f:
        qs = json.load(f)

    result = diversity_score(qs)
    print(f"Diversity score: {result['composite']}")
    print(f"  Skill coverage:     {result['skill_coverage']}")
    print(f"  Embedding spread:   {result['embedding_spread']}")
    print(f"  Archetype diversity: {result['archetype_diversity']}")

    gaps = find_diversity_gaps(qs)
    print(f"\nUnderrepresented skills: {gaps['underrepresented_skills']}")
    print(f"Overrepresented skill:   {gaps['overrepresented_skill']}")
    print(f"Underrepresented archetypes: {gaps['underrepresented_archetypes']}")
    print(f"Overrepresented archetype:   {gaps['overrepresented_archetype']}")
