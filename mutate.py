from __future__ import annotations

"""
Two-stage Gemini mutation with full IB-2 taxonomy awareness.

Stage 1: Gemini 2.5 Pro — analyzes current set across all 6 diversity dimensions
Stage 2: Gemini 3 Flash Preview — converts reasoning output to structured JSON
"""

import json
import os
import numpy as np
from collections import Counter
from google import genai

from evaluate import find_diversity_gaps
from taxonomy import (
    ALL_SKILLS, ALL_ARCHETYPES, ALL_MECHANISMS, ALL_COMMAND_TERMS, ALL_STYLES,
    QUESTION_ARCHETYPES, DIFFICULTY_MECHANISMS,
    D7_MECHANISMS, D7_SYNERGIES, D7_PROFILE,
)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
REASONER_MODEL = "gemini-2.5-pro"
FORMATTER_MODEL = "gemini-3-flash-preview"

client = genai.Client(api_key=GEMINI_API_KEY)


def select_target(
    questions: list[dict],
    embeddings: list[list[float]] | None = None,
) -> int:
    """
    Pick the index of the question to mutate.

    Multi-dimensional targeting:
    1. Score each question by how much it contributes to over-representation
    2. Among top scorers, find the most embedding-redundant
    """
    # Score each question: higher = more redundant / less valuable
    scores = []
    skill_counts = Counter(q.get("skill") for q in questions)
    arch_counts = Counter(q.get("archetype") for q in questions)
    style_counts = Counter(q.get("style") for q in questions)

    for i, q in enumerate(questions):
        score = 0
        # Penalize over-represented dimensions
        score += skill_counts.get(q.get("skill"), 0) * 3  # Skill has highest weight
        score += arch_counts.get(q.get("archetype"), 0) * 2
        score += style_counts.get(q.get("style"), 0) * 1
        # Penalize questions with few mechanisms (less interesting)
        score += max(0, 2 - len(q.get("mechanisms", [])))
        scores.append(score)

    # Get top 5 candidates by redundancy score
    ranked = sorted(range(len(questions)), key=lambda i: scores[i], reverse=True)
    candidates = ranked[:min(5, len(ranked))]

    # If we have embeddings, find the most similar pair among candidates
    if embeddings and len(candidates) >= 2:
        vecs = np.array([embeddings[i] for i in candidates], dtype=np.float64)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms
        sim = vecs @ vecs.T
        np.fill_diagonal(sim, -1)
        flat_idx = np.argmax(sim)
        i, _ = divmod(flat_idx, len(candidates))
        return candidates[i]

    return candidates[0]


def build_reasoner_prompt(
    questions: list[dict],
    target_idx: int,
    gaps: dict,
) -> str:
    """Build the comprehensive prompt for Gemini 2.5 Pro reasoner."""

    target_q = questions[target_idx]

    # Summarize current set with full taxonomy info
    q_summaries = []
    for i, q in enumerate(questions):
        marker = " ← TARGET (rewrite this)" if i == target_idx else ""
        mechs = ", ".join(q.get("mechanisms", []))
        terms = ", ".join(q.get("command_terms", []))
        q_summaries.append(
            f"[{i}] skill={q.get('skill')}, archetype={q.get('archetype')}, "
            f"mechanisms=[{mechs}], style={q.get('style')}, "
            f"terms=[{terms}], marks={q.get('marks')}{marker}\n"
            f"    {q['question'][:150]}..."
        )

    # Build archetype descriptions for the prompt
    arch_desc = "\n".join(
        f"  - {aid}: {a['name']} — {a['description']} (requires: {a['required_mechanisms']})"
        for aid, a in QUESTION_ARCHETYPES.items()
    )

    # Build mechanism descriptions
    mech_desc = "\n".join(
        f"  - {mid}: {desc}" for mid, desc in DIFFICULTY_MECHANISMS.items()
        if mid in D7_MECHANISMS or mid in [m for q in questions for m in q.get("mechanisms", [])]
    )

    # D7 synergies
    syn_desc = "\n".join(
        f"  - {a} + {b}: {v['effect']} (boost: {v['boost']})"
        for (a, b), v in D7_SYNERGIES.items()
    )

    return f"""You are an IB Mathematics AA HL exam question writer specializing in Functions (Topic 2).
You are optimizing a set of D7 exemplar questions for MAXIMUM DIVERSITY across 6 dimensions.

## D7 Cognitive Profile
- DOK: {D7_PROFILE['dok']}, Bloom: {D7_PROFILE['bloom']}, SOLO: {D7_PROFILE['solo']}
- Assessment Objectives: {D7_PROFILE['ao']}
- Must use at least {D7_PROFILE['min_mechanisms']} difficulty mechanisms
- Parts must escalate in cognitive demand
- Marks: {D7_PROFILE['marks_range'][0]}-{D7_PROFILE['marks_range'][1]}

## Current Question Set ({len(questions)} questions)
{chr(10).join(q_summaries)}

## Diversity Gap Analysis

### Skills (target: even coverage across 12 Functions sub-skills)
Distribution: {json.dumps(gaps['skill_counts'], indent=2)}
GAPS — underrepresented: {gaps['underrepresented_skills']}
EXCESS — overrepresented: {gaps['overrepresented_skill']}

### Archetypes (target: all 6 structural archetypes)
Distribution: {json.dumps(gaps['archetype_counts'], indent=2)}
GAPS: {gaps['underrepresented_archetypes']}
Available archetypes:
{arch_desc}

### Mechanisms (target: variety of cognitive challenge types)
Distribution: {json.dumps(gaps['mechanism_counts'], indent=2)}
GAPS — underused D7 mechanisms: {gaps['underrepresented_mechanisms']}
D7-available mechanisms:
{mech_desc}

### High-impact mechanism synergies (use these for stronger questions):
{syn_desc}

### Styles (target: mix of pure_abstract, applied_real_world, modelling)
Distribution: {json.dumps(gaps['style_counts'], indent=2)}
GAPS: {gaps['underrepresented_styles']}

### Command Terms
Distribution: {json.dumps(dict(Counter(t for q in questions for t in q.get('command_terms', [])).most_common(10)), indent=2)}

## Task
Rewrite question [{target_idx}] to fill the BIGGEST diversity gaps.

Current question [{target_idx}]:
- Skill: {target_q.get('skill')}
- Archetype: {target_q.get('archetype')}
- Mechanisms: {target_q.get('mechanisms')}
- Style: {target_q.get('style')}
- Command terms: {target_q.get('command_terms')}
- Marks: {target_q.get('marks')}

## Mutation Targets (prioritized)
1. Shift skill → one of: {gaps['underrepresented_skills']}
2. Use archetype → one of: {gaps['underrepresented_archetypes']}
3. Include mechanisms → {gaps['underrepresented_mechanisms']}
4. Shift style → one of: {gaps['underrepresented_styles']}
5. Use different command terms than the most common ones

## Rules
- Must be D7 difficulty: exam-worthy, {D7_PROFILE['marks_range'][0]}-{D7_PROFILE['marks_range'][1]} marks
- Must be mathematically correct with a complete solution and mark scheme
- Must stay within IB AA HL Functions syllabus
- Must use at least 2 difficulty mechanisms (preferably a synergistic pair)
- Parts must escalate in cognitive demand
- Use LaTeX notation for mathematical expressions

## Output
Write the complete rewritten question with:
1. The question text (with LaTeX, multiple parts with escalating difficulty)
2. The full solution with mark scheme (M1, A1, R1 notation)
3. Skill classification (primary + any secondary skills)
4. Archetype used
5. Mechanisms used (name them explicitly)
6. Command terms used
7. Style type
8. Total marks"""


def build_formatter_prompt(reasoner_output: str, target_q: dict) -> str:
    """Build the prompt for Gemini 3 Flash Preview formatter stage."""
    return f"""Extract the rewritten exam question from the reasoning below into JSON.

--- REASONER OUTPUT ---
{reasoner_output}
--- END ---

IMPORTANT: In JSON strings, all backslashes must be double-escaped (e.g., \\\\frac not \\frac).
Output ONLY valid JSON matching this exact schema:
{{
  "id": "{target_q['id']}",
  "question": "<full question text with LaTeX>",
  "solution": "<full solution with mark scheme>",
  "marks": <integer>,
  "topic": "Functions",
  "skill": "<primary skill, one of: {ALL_SKILLS}>",
  "secondary_skills": [<optional additional skills from same list>],
  "archetype": "<one of: {ALL_ARCHETYPES}>",
  "mechanisms": [<1-3 mechanisms from: {ALL_MECHANISMS}>],
  "command_terms": [<command terms used, from: {ALL_COMMAND_TERMS[:15]}...>],
  "style": "<one of: {ALL_STYLES}>",
  "difficulty": 7,
  "source": "{target_q.get('source', 'autoquestions')}",
  "paper_type": "{target_q.get('paper_type', 'Paper 1')}"
}}"""


def mutate(
    questions: list[dict],
    embeddings: list[list[float]] | None = None,
) -> tuple[list[dict], int, str]:
    """
    Run one mutation cycle with full taxonomy awareness.

    Returns:
        (new_questions, target_idx, description)
    """
    gaps = find_diversity_gaps(questions)
    target_idx = select_target(questions, embeddings)
    target_q = questions[target_idx]

    # Stage 1: Reasoning
    reasoner_prompt = build_reasoner_prompt(questions, target_idx, gaps)
    reasoner_response = client.models.generate_content(
        model=REASONER_MODEL,
        contents=reasoner_prompt,
    )
    reasoner_text = reasoner_response.text

    # Stage 2: Formatting
    formatter_prompt = build_formatter_prompt(reasoner_text, target_q)
    formatter_response = client.models.generate_content(
        model=FORMATTER_MODEL,
        contents=formatter_prompt,
        config={"response_mime_type": "application/json"},
    )
    formatter_text = formatter_response.text

    # Parse JSON — repair common LaTeX escape issues
    # Gemini sometimes outputs invalid \escapes in LaTeX (e.g., \f, \t inside strings)
    import re
    repaired = re.sub(
        r'(?<!\\)\\(?!["\\/bfnrtu])',  # unescaped backslash not followed by valid JSON escape
        r'\\\\',
        formatter_text,
    )
    try:
        new_q = json.loads(repaired)
    except json.JSONDecodeError:
        # Last resort: try original text
        new_q = json.loads(formatter_text)

    # Validate and sanitize
    for field in ["question", "solution", "marks", "skill"]:
        if field not in new_q:
            raise ValueError(f"Missing required field: {field}")

    if new_q["skill"] not in ALL_SKILLS:
        raise ValueError(f"Invalid skill: {new_q['skill']}")

    # Sanitize optional fields
    new_q.setdefault("secondary_skills", [])
    new_q["secondary_skills"] = [s for s in new_q["secondary_skills"] if s in ALL_SKILLS]

    if new_q.get("archetype") not in ALL_ARCHETYPES:
        new_q["archetype"] = "none"

    new_q.setdefault("mechanisms", [])
    new_q["mechanisms"] = [m for m in new_q["mechanisms"] if m in ALL_MECHANISMS]

    new_q.setdefault("command_terms", [])
    new_q["command_terms"] = [c for c in new_q["command_terms"] if c in ALL_COMMAND_TERMS]

    if new_q.get("style") not in ALL_STYLES:
        new_q["style"] = "pure_abstract"

    new_q.setdefault("difficulty", 7)
    new_q.setdefault("topic", "Functions")
    new_q.setdefault("id", target_q["id"])
    new_q.setdefault("source", target_q.get("source", "autoquestions"))
    new_q.setdefault("paper_type", target_q.get("paper_type", "Paper 1"))

    # Build description
    changes = []
    if new_q["skill"] != target_q.get("skill"):
        changes.append(f"skill:{target_q.get('skill')}→{new_q['skill']}")
    if new_q["archetype"] != target_q.get("archetype"):
        changes.append(f"arch:{target_q.get('archetype')}→{new_q['archetype']}")
    if new_q.get("style") != target_q.get("style"):
        changes.append(f"style:{target_q.get('style')}→{new_q['style']}")
    mechs = ",".join(new_q.get("mechanisms", []))
    changes.append(f"mechs:[{mechs}]")

    desc = f"mutate [{target_idx}] {'; '.join(changes)}"

    # Replace in set
    new_questions = questions.copy()
    new_questions[target_idx] = new_q

    return new_questions, target_idx, desc
