from __future__ import annotations

"""
Two-stage Gemini mutation: Reason about diversity gaps, then format to JSON.

Stage 1: Gemini 2.5 Pro — analyzes current set, reasons about what to change
Stage 2: Gemini 3 Flash Preview — converts reasoning output to structured JSON
"""

import json
import os
import numpy as np
from google import genai

from evaluate import find_diversity_gaps, ALL_SKILLS, ALL_ARCHETYPES

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
REASONER_MODEL = "gemini-2.5-pro"
FORMATTER_MODEL = "gemini-3-flash-preview"

client = genai.Client(api_key=GEMINI_API_KEY)

QUESTION_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "question": {"type": "string"},
        "solution": {"type": "string"},
        "marks": {"type": "integer"},
        "topic": {"type": "string"},
        "skill": {"type": "string", "enum": ALL_SKILLS},
        "archetype": {"type": "string", "enum": ALL_ARCHETYPES},
        "difficulty": {"type": "integer"},
        "source": {"type": "string"},
        "paper_type": {"type": "string"},
    },
    "required": ["id", "question", "solution", "marks", "topic", "skill",
                  "archetype", "difficulty", "source", "paper_type"],
}


def select_target(
    questions: list[dict],
    embeddings: list[list[float]] | None = None,
) -> int:
    """
    Pick the index of the question to mutate.

    Strategy:
    1. Find the most over-represented skill
    2. Among those questions, find the most redundant pair (highest embedding similarity)
    3. Among those, pick the one with the most common archetype
    """
    gaps = find_diversity_gaps(questions)
    overrep_skill = gaps["overrepresented_skill"]

    # Candidates: questions in the over-represented skill
    candidates = [i for i, q in enumerate(questions) if q.get("skill") == overrep_skill]
    if not candidates:
        candidates = list(range(len(questions)))

    # If we have embeddings, find the most similar pair among candidates
    if embeddings and len(candidates) >= 2:
        vecs = np.array([embeddings[i] for i in candidates])
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        vecs = vecs / norms
        sim = vecs @ vecs.T
        np.fill_diagonal(sim, -1)
        flat_idx = np.argmax(sim)
        i, j = divmod(flat_idx, len(candidates))
        # Between the two most similar, pick the one with more common archetype
        from collections import Counter
        arch_counts = Counter(q.get("archetype") for q in questions)
        a_count = arch_counts.get(questions[candidates[i]].get("archetype"), 0)
        b_count = arch_counts.get(questions[candidates[j]].get("archetype"), 0)
        return candidates[i] if a_count >= b_count else candidates[j]
    else:
        # No embeddings — pick first candidate with most common archetype
        from collections import Counter
        arch_counts = Counter(q.get("archetype") for q in questions)
        candidates.sort(key=lambda i: arch_counts.get(questions[i].get("archetype"), 0), reverse=True)
        return candidates[0]


def build_reasoner_prompt(
    questions: list[dict],
    target_idx: int,
    gaps: dict,
) -> str:
    """Build the prompt for Gemini 2.5 Pro reasoner stage."""

    target_q = questions[target_idx]

    # Summarize the current set
    q_summaries = []
    for i, q in enumerate(questions):
        marker = " ← TARGET (rewrite this)" if i == target_idx else ""
        q_summaries.append(
            f"[{i}] skill={q['skill']}, archetype={q['archetype']}, "
            f"marks={q['marks']}{marker}\n"
            f"    {q['question'][:200]}..."
        )

    return f"""You are an IB Mathematics AA HL exam question writer specializing in Functions (Topic 2).

## Current Question Set
{chr(10).join(q_summaries)}

## Diversity Analysis
Skill distribution: {json.dumps(gaps['skill_counts'], indent=2)}
Archetype distribution: {json.dumps(gaps['archetype_counts'], indent=2)}

Underrepresented skills: {gaps['underrepresented_skills']}
Overrepresented skill: {gaps['overrepresented_skill']}
Underrepresented archetypes: {gaps['underrepresented_archetypes']}
Overrepresented archetype: {gaps['overrepresented_archetype']}

## Task
Rewrite question [{target_idx}] to fill the biggest diversity gap.

The current question is:
- Skill: {target_q['skill']}
- Archetype: {target_q['archetype']}
- Marks: {target_q['marks']}

Target the question toward one of these underrepresented skills: {gaps['underrepresented_skills']}
And use one of these underrepresented archetypes: {gaps['underrepresented_archetypes']}

## Rules
- Must remain D7 difficulty (exam-worthy, 6-10 marks)
- Must be mathematically correct with a complete solution
- Must stay within IB AA HL Functions syllabus
- Change the SKILL and/or ARCHETYPE to target the identified gap
- Include a proper mark scheme in the solution
- Use LaTeX notation for mathematical expressions

## Output
Write the complete rewritten question with:
1. The question text (with LaTeX)
2. The full solution with mark scheme
3. The new skill classification
4. The new archetype classification
5. Total marks"""


def build_formatter_prompt(reasoner_output: str, target_q: dict) -> str:
    """Build the prompt for Gemini 3 Flash Preview formatter stage."""
    return f"""Convert the following rewritten exam question into JSON format.

Original question ID: {target_q['id']}
Original source: {target_q['source']}
Paper type: {target_q['paper_type']}

The skill must be one of: {ALL_SKILLS}
The archetype must be one of: {ALL_ARCHETYPES}
Difficulty must be 7.
Topic must be "Functions".

--- REASONER OUTPUT ---
{reasoner_output}
--- END ---

Output ONLY valid JSON matching this schema, nothing else:
{{
  "id": "{target_q['id']}",
  "question": "...",
  "solution": "...",
  "marks": <int>,
  "topic": "Functions",
  "skill": "<one of the valid skills>",
  "archetype": "<one of the valid archetypes>",
  "difficulty": 7,
  "source": "{target_q['source']}",
  "paper_type": "{target_q['paper_type']}"
}}"""


def mutate(
    questions: list[dict],
    embeddings: list[list[float]] | None = None,
) -> tuple[list[dict], int, str]:
    """
    Run one mutation cycle.

    Returns:
        (new_questions, target_idx, description)

    Raises on failure (invalid JSON, API error, etc.)
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
        config={
            "response_mime_type": "application/json",
        },
    )
    formatter_text = formatter_response.text

    # Parse JSON
    new_q = json.loads(formatter_text)

    # Validate required fields
    for field in ["question", "solution", "marks", "skill", "archetype"]:
        if field not in new_q:
            raise ValueError(f"Missing required field: {field}")

    # Validate skill and archetype are valid
    if new_q["skill"] not in ALL_SKILLS:
        raise ValueError(f"Invalid skill: {new_q['skill']}")
    if new_q["archetype"] not in ALL_ARCHETYPES:
        raise ValueError(f"Invalid archetype: {new_q['archetype']}")

    # Build description
    desc = (
        f"mutate [{target_idx}] {target_q['skill']}→{new_q['skill']}, "
        f"{target_q['archetype']}→{new_q['archetype']}"
    )

    # Replace in set
    new_questions = questions.copy()
    new_questions[target_idx] = new_q

    return new_questions, target_idx, desc
