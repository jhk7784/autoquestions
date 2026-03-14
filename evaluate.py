from __future__ import annotations

"""
Diversity metric evaluation for the exemplar question set.

Computes a composite score across 6 dimensions imported from the IB-2 taxonomy:
  1. Skill coverage (12 T2 Functions sub-skills)
  2. Embedding spread (semantic distinctness)
  3. Archetype diversity (6 structural archetypes)
  4. Mechanism coverage (18 difficulty mechanisms, D7 requires 2+)
  5. Command term variety (26 IB command terms)
  6. Style balance (pure abstract / applied / modelling)
"""

import json
import numpy as np
from collections import Counter
from typing import Optional

from taxonomy import (
    ALL_SKILLS, ALL_ARCHETYPES, ALL_MECHANISMS, ALL_STYLES,
    D7_MECHANISMS, COMMAND_TERMS,
)

# ─── Sub-score Functions ──────────────────────────────────────────────────────

def skill_coverage_score(questions: list[dict]) -> float:
    """
    Evenness of distribution across the 12 Functions sub-skills.
    Returns 0-1 where 1 = perfectly even.
    """
    n = len(questions)
    if n == 0:
        return 0.0

    counts = {s: 0 for s in ALL_SKILLS}
    for q in questions:
        skill = q.get("skill", "FUNC_POLYNOMIAL")
        if skill in counts:
            counts[skill] += 1
        # Count secondary skills at half weight
        for ss in q.get("secondary_skills", []):
            if ss in counts:
                counts[ss] += 0.5

    values = list(counts.values())
    ideal = sum(values) / len(ALL_SKILLS)
    max_std = np.sqrt(ideal**2 * (len(ALL_SKILLS) - 1) / len(ALL_SKILLS) + (sum(values) - ideal)**2 / len(ALL_SKILLS))

    if max_std == 0:
        return 1.0

    actual_std = np.std(values)
    return float(1.0 - (actual_std / max_std))


def embedding_spread_score(embeddings: list[list[float]]) -> float:
    """Mean pairwise cosine distance. Returns 0-1 where 1 = maximally spread."""
    n = len(embeddings)
    if n < 2:
        return 0.0

    vecs = np.array(embeddings, dtype=np.float64)
    norms = np.linalg.norm(vecs, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    vecs = vecs / norms

    sim_matrix = vecs @ vecs.T
    mask = np.triu(np.ones((n, n), dtype=bool), k=1)
    similarities = sim_matrix[mask]
    distances = 1.0 - similarities
    mean_dist = float(np.mean(distances))

    return min(max(mean_dist, 0.0), 1.0)


def archetype_diversity_score(questions: list[dict]) -> float:
    """Fraction of the 6 structural archetypes represented. 0-1."""
    if not questions:
        return 0.0

    present = set()
    for q in questions:
        arch = q.get("archetype", "none")
        if arch in ALL_ARCHETYPES:
            present.add(arch)

    return len(present) / len(ALL_ARCHETYPES)


def mechanism_coverage_score(questions: list[dict]) -> float:
    """
    Measures how many distinct difficulty mechanisms are used across the set,
    with bonus for D7-specific mechanisms.
    Returns 0-1.
    """
    if not questions:
        return 0.0

    all_mechs = set()
    d7_mechs = set()
    for q in questions:
        for m in q.get("mechanisms", []):
            if m in ALL_MECHANISMS:
                all_mechs.add(m)
            if m in D7_MECHANISMS:
                d7_mechs.add(m)

    # Base: fraction of all 18 mechanisms used
    base = len(all_mechs) / len(ALL_MECHANISMS)

    # D7 bonus: fraction of 5 D7-specific mechanisms used (weighted 50%)
    d7_coverage = len(d7_mechs) / len(D7_MECHANISMS)

    return 0.5 * base + 0.5 * d7_coverage


def command_term_variety_score(questions: list[dict]) -> float:
    """
    Measures variety of command terms used, weighted by cognitive level.
    Returns 0-1.
    """
    if not questions:
        return 0.0

    # Count unique command terms
    present = set()
    cognitive_levels = set()
    for q in questions:
        for ct in q.get("command_terms", []):
            if ct in COMMAND_TERMS:
                present.add(ct)
                cognitive_levels.add(COMMAND_TERMS[ct]["cognitive"])

    # Base: fraction of command terms used (cap at reasonable target — not all 26 needed)
    # A good D7 set should use ~8-12 distinct command terms
    target_terms = 12
    term_score = min(len(present) / target_terms, 1.0)

    # Cognitive spread: should cover multiple cognitive levels
    all_cognitive = set(v["cognitive"] for v in COMMAND_TERMS.values())
    cog_score = len(cognitive_levels) / len(all_cognitive)

    return 0.6 * term_score + 0.4 * cog_score


def style_balance_score(questions: list[dict]) -> float:
    """
    Measures balance across pure_abstract, applied_real_world, and modelling.
    Returns 0-1 where 1 = all 3 styles present with reasonable balance.
    """
    if not questions:
        return 0.0

    counts = Counter(q.get("style", "pure_abstract") for q in questions)
    present = sum(1 for s in ALL_STYLES if counts.get(s, 0) > 0)

    # Presence: are all 3 styles represented?
    presence = present / len(ALL_STYLES)

    # Balance: how even is the distribution?
    if present <= 1:
        return presence * 0.5  # Having just one style = low score

    values = [counts.get(s, 0) for s in ALL_STYLES]
    total = sum(values)
    if total == 0:
        return 0.0
    ideal = total / len(ALL_STYLES)
    max_std = np.sqrt(ideal**2 * (len(ALL_STYLES) - 1) / len(ALL_STYLES) + (total - ideal)**2 / len(ALL_STYLES))
    if max_std == 0:
        return 1.0
    actual_std = np.std(values)
    evenness = 1.0 - (actual_std / max_std)

    return 0.5 * presence + 0.5 * evenness


# ─── Composite Score ──────────────────────────────────────────────────────────

def diversity_score(
    questions: list[dict],
    embeddings: Optional[list[list[float]]] = None,
) -> dict:
    """
    Compute the composite diversity score across all 6 dimensions.

    Weights:
      skill_coverage:      0.25  (primary content dimension)
      embedding_spread:    0.20  (semantic distinctness)
      archetype_diversity: 0.20  (structural variety)
      mechanism_coverage:  0.15  (cognitive complexity variety)
      command_term_variety: 0.10 (assessment language variety)
      style_balance:       0.10  (context variety)
    """
    skill = skill_coverage_score(questions)
    archetype = archetype_diversity_score(questions)
    mechanism = mechanism_coverage_score(questions)
    command = command_term_variety_score(questions)
    style = style_balance_score(questions)

    if embeddings is not None and len(embeddings) >= 2:
        spread = embedding_spread_score(embeddings)
        composite = (
            0.25 * skill
            + 0.20 * spread
            + 0.20 * archetype
            + 0.15 * mechanism
            + 0.10 * command
            + 0.10 * style
        )
    else:
        spread = None
        # Redistribute embedding weight proportionally
        composite = (
            0.30 * skill
            + 0.25 * archetype
            + 0.20 * mechanism
            + 0.13 * command
            + 0.12 * style
        )

    return {
        "composite": round(composite, 6),
        "skill_coverage": round(skill, 6),
        "embedding_spread": round(spread, 6) if spread is not None else None,
        "archetype_diversity": round(archetype, 6),
        "mechanism_coverage": round(mechanism, 6),
        "command_term_variety": round(command, 6),
        "style_balance": round(style, 6),
    }


# ─── Gap Analysis (used by mutate.py) ────────────────────────────────────────

def find_diversity_gaps(questions: list[dict]) -> dict:
    """
    Comprehensive gap analysis across all taxonomy dimensions.
    Used by mutate.py to build the mutation prompt.
    """
    skill_counts = Counter(q.get("skill", "FUNC_POLYNOMIAL") for q in questions)
    arch_counts = Counter(q.get("archetype", "none") for q in questions)
    mech_counts = Counter(m for q in questions for m in q.get("mechanisms", []))
    term_counts = Counter(t for q in questions for t in q.get("command_terms", []))
    style_counts = Counter(q.get("style", "pure_abstract") for q in questions)

    def find_under_over(counts, all_items):
        missing = [s for s in all_items if counts.get(s, 0) == 0]
        if not missing and counts:
            min_count = min(counts.get(s, 0) for s in all_items)
            missing = [s for s in all_items if counts.get(s, 0) == min_count]
        overrep = counts.most_common(1)[0][0] if counts else None
        return missing, overrep

    under_skills, over_skill = find_under_over(skill_counts, ALL_SKILLS)
    under_archs, over_arch = find_under_over(arch_counts, ALL_ARCHETYPES)
    under_mechs, over_mech = find_under_over(mech_counts, D7_MECHANISMS)
    under_styles, over_style = find_under_over(style_counts, ALL_STYLES)

    return {
        "skill_counts": dict(skill_counts),
        "archetype_counts": dict(arch_counts),
        "mechanism_counts": dict(mech_counts),
        "command_term_counts": dict(term_counts),
        "style_counts": dict(style_counts),
        "underrepresented_skills": under_skills,
        "overrepresented_skill": over_skill,
        "underrepresented_archetypes": under_archs,
        "overrepresented_archetype": over_arch,
        "underrepresented_mechanisms": under_mechs,
        "overrepresented_mechanism": over_mech,
        "underrepresented_styles": under_styles,
        "overrepresented_style": over_style,
    }


if __name__ == "__main__":
    with open("questions.json") as f:
        qs = json.load(f)

    result = diversity_score(qs)
    print(f"Diversity score: {result['composite']}")
    print(f"  Skill coverage:      {result['skill_coverage']}")
    print(f"  Embedding spread:    {result['embedding_spread']}")
    print(f"  Archetype diversity: {result['archetype_diversity']}")
    print(f"  Mechanism coverage:  {result['mechanism_coverage']}")
    print(f"  Command term variety:{result['command_term_variety']}")
    print(f"  Style balance:       {result['style_balance']}")

    gaps = find_diversity_gaps(qs)
    print(f"\nUnderrepresented skills:     {gaps['underrepresented_skills']}")
    print(f"Overrepresented skill:       {gaps['overrepresented_skill']}")
    print(f"Underrepresented archetypes: {gaps['underrepresented_archetypes']}")
    print(f"Overrepresented archetype:   {gaps['overrepresented_archetype']}")
    print(f"Underrepresented mechanisms: {gaps['underrepresented_mechanisms']}")
    print(f"Underrepresented styles:     {gaps['underrepresented_styles']}")
