from __future__ import annotations

"""
One-time script: Re-classify all questions in questions.json using Gemini
with the full IB-2 taxonomy (skills, archetypes, mechanisms, command terms, style).

Replaces the naive keyword heuristics from seed.py with proper LLM classification.
"""

import json
import os
import time

from google import genai

from taxonomy import (
    FUNCTIONS_SKILLS, QUESTION_ARCHETYPES, DIFFICULTY_MECHANISMS,
    COMMAND_TERMS, STYLE_TYPES,
    ALL_SKILLS, ALL_ARCHETYPES, ALL_MECHANISMS, ALL_COMMAND_TERMS, ALL_STYLES,
    D7_MECHANISMS,
)

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)

CLASSIFIER_MODEL = "gemini-2.5-flash"  # Fast + cheap for classification
FORMATTER_MODEL = "gemini-3-flash-preview"


def build_classification_prompt(question: dict) -> str:
    """Build a prompt that asks Gemini to classify one question across all taxonomy dimensions."""

    skills_desc = "\n".join(f"  - {k}: {v}" for k, v in FUNCTIONS_SKILLS.items())
    archetypes_desc = "\n".join(
        f"  - {k}: {v['name']} — {v['description']}" for k, v in QUESTION_ARCHETYPES.items()
    )
    mechanisms_desc = "\n".join(f"  - {k}: {v}" for k, v in DIFFICULTY_MECHANISMS.items())
    commands_desc = "\n".join(
        f"  - {k} (AO: {v['ao']}, severity: {v['severity']})" for k, v in COMMAND_TERMS.items()
    )
    styles_desc = "\n".join(f"  - {k}: {v}" for k, v in STYLE_TYPES.items())

    return f"""You are an IB Mathematics AA HL expert classifier. Analyze this exam question and classify it across multiple taxonomy dimensions.

## Question
{question['question'][:3000]}

## Solution
{question.get('solution', 'N/A')[:2000]}

## Marks: {question.get('marks', 'unknown')}

---

## Classification Dimensions

### 1. Primary Skill (pick the BEST match)
{skills_desc}

### 2. Secondary Skills (0-2 additional skills involved)
Same list as above. Only include if the question genuinely requires knowledge from multiple sub-skills.

### 3. Archetype (pick the BEST match, or "none" if no archetype fits well)
{archetypes_desc}

### 4. Difficulty Mechanisms (pick 1-3 that apply — for D7, at least 2 should be from: {D7_MECHANISMS})
{mechanisms_desc}

### 5. Command Terms (list ALL command terms used in the question text)
{commands_desc}

### 6. Style Type (pick one)
{styles_desc}

---

## Output
Provide your reasoning, then state your classifications clearly at the end."""


def build_formatter_prompt(reasoning: str, question_id: str) -> str:
    return f"""Extract the classifications from the reasoning below into JSON.

--- REASONING ---
{reasoning}
--- END ---

Output ONLY valid JSON:
{{
  "id": "{question_id}",
  "skill": "<primary skill from: {ALL_SKILLS}>",
  "secondary_skills": ["<optional additional skills>"],
  "archetype": "<one of {ALL_ARCHETYPES} or 'none'>",
  "mechanisms": ["<1-3 mechanisms from: {ALL_MECHANISMS}>"],
  "command_terms": ["<command terms found in question>"],
  "style": "<one of {ALL_STYLES}>"
}}"""


def classify_one(question: dict) -> dict:
    """Classify a single question using two-stage Gemini pipeline."""

    # Stage 1: Reasoning
    prompt = build_classification_prompt(question)
    response = client.models.generate_content(
        model=CLASSIFIER_MODEL,
        contents=prompt,
    )
    reasoning = response.text

    # Stage 2: Format to JSON
    fmt_prompt = build_formatter_prompt(reasoning, question["id"])
    fmt_response = client.models.generate_content(
        model=FORMATTER_MODEL,
        contents=fmt_prompt,
        config={"response_mime_type": "application/json"},
    )

    result = json.loads(fmt_response.text)

    # Validate
    if result.get("skill") not in ALL_SKILLS:
        result["skill"] = question.get("skill", "FUNC_POLYNOMIAL")
    result["secondary_skills"] = [s for s in result.get("secondary_skills", []) if s in ALL_SKILLS]
    if result.get("archetype") not in ALL_ARCHETYPES + ["none"]:
        result["archetype"] = "none"
    result["mechanisms"] = [m for m in result.get("mechanisms", []) if m in ALL_MECHANISMS]
    result["command_terms"] = [c for c in result.get("command_terms", []) if c in ALL_COMMAND_TERMS]
    if result.get("style") not in ALL_STYLES:
        result["style"] = "pure_abstract"

    return result


def main():
    with open("questions.json") as f:
        questions = json.load(f)

    print(f"Reclassifying {len(questions)} questions with full IB-2 taxonomy...")
    print()

    for i, q in enumerate(questions):
        try:
            classification = classify_one(q)

            # Merge classification into question
            q["skill"] = classification["skill"]
            q["secondary_skills"] = classification["secondary_skills"]
            q["archetype"] = classification["archetype"]
            q["mechanisms"] = classification["mechanisms"]
            q["command_terms"] = classification["command_terms"]
            q["style"] = classification["style"]

            # Remove old-style archetype field if it was a simple string
            # (now replaced by proper archetype ID)

            print(
                f"[{i+1}/{len(questions)}] {q['id'][:20]}... "
                f"skill={classification['skill']}, "
                f"arch={classification['archetype']}, "
                f"mechs={classification['mechanisms']}, "
                f"style={classification['style']}"
            )

            # Rate limiting: Gemini free tier = 15 RPM for 2.5 Pro
            time.sleep(2)

        except Exception as e:
            print(f"[{i+1}/{len(questions)}] FAILED: {e}")
            # Keep existing classification on failure
            if "secondary_skills" not in q:
                q["secondary_skills"] = []
            if "mechanisms" not in q:
                q["mechanisms"] = []
            if "command_terms" not in q:
                q["command_terms"] = []
            if "style" not in q:
                q["style"] = "pure_abstract"

    # Save
    with open("questions.json", "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Updated {len(questions)} questions in questions.json")

    # Print distribution summary
    from collections import Counter
    print("\n--- Skill Distribution ---")
    for skill, count in Counter(q["skill"] for q in questions).most_common():
        print(f"  {skill}: {count}")
    print("\n--- Archetype Distribution ---")
    for arch, count in Counter(q["archetype"] for q in questions).most_common():
        print(f"  {arch}: {count}")
    print("\n--- Mechanism Distribution ---")
    all_mechs = [m for q in questions for m in q.get("mechanisms", [])]
    for mech, count in Counter(all_mechs).most_common():
        print(f"  {mech}: {count}")
    print("\n--- Style Distribution ---")
    for style, count in Counter(q.get("style", "pure_abstract") for q in questions).most_common():
        print(f"  {style}: {count}")
    print("\n--- Command Term Distribution ---")
    all_terms = [t for q in questions for t in q.get("command_terms", [])]
    for term, count in Counter(all_terms).most_common(10):
        print(f"  {term}: {count}")


if __name__ == "__main__":
    main()
