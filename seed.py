"""
One-time script: Export D7 Functions exemplar questions from the IB-2 pgvector database.
Writes to questions.json.
"""

import asyncio
import json
import asyncpg

DATABASE_URL = "postgresql://ib2admin:pDhZJoNI7I74cIXatAOj2LnJ@ib2-postgres.cfice0q2wena.ap-northeast-2.rds.amazonaws.com:5432/ib2"

# T2 Functions sub-skills for classification
FUNCTIONS_KEYWORDS = {
    "FUNC_DOMAIN": ["domain", "range"],
    "FUNC_COMPOSITE": ["composite", "fog", "gof", "f(g(", "g(f("],
    "FUNC_INVERSE": ["inverse", "f^{-1}", "f^(-1)", "f⁻¹"],
    "FUNC_TRANSFORM": ["transform", "translat", "reflect", "stretch", "dilat"],
    "FUNC_QUADRATIC": ["quadratic", "parabola", "ax^2", "vertex", "discriminant"],
    "FUNC_RATIONAL": ["rational", "asymptote", "\\frac{", "denominator"],
    "FUNC_EXP": ["exponential", "e^", "growth", "decay", "\\exp"],
    "FUNC_LOG": ["logarithm", "\\ln", "\\log", "log_"],
    "FUNC_MODULUS": ["absolute", "modulus", "|x|", "\\lvert"],
    "FUNC_POLYNOMIAL": ["polynomial", "cubic", "degree", "factor theorem", "remainder"],
    "FUNC_SUM_PRODUCT_ROOTS": ["sum of roots", "product of roots", "vieta", "roots of"],
    "FUNC_GRAPH_SKETCH": ["sketch", "graph", "plot", "curve", "intercept"],
}

ARCHETYPES = {
    "prove": ["prove", "show that", "hence show"],
    "find/solve": ["find", "solve", "determine", "calculate", "evaluate"],
    "sketch/graph": ["sketch", "graph", "draw", "plot"],
    "interpret/explain": ["interpret", "explain", "describe", "state the meaning"],
    "model/apply": ["model", "application", "context", "real-world", "represents"],
    "show that": ["show that", "verify", "demonstrate", "confirm"],
    "multi-step synthesis": ["hence", "and hence", "use your result", "using part"],
}


def classify_skill(question_text: str, solution_text: str) -> str:
    """Classify a question into a T2 Functions sub-skill by keyword matching."""
    combined = (question_text + " " + solution_text).lower()
    best_skill = "FUNC_POLYNOMIAL"  # default fallback
    best_count = 0
    for skill, keywords in FUNCTIONS_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw.lower() in combined)
        if count > best_count:
            best_count = count
            best_skill = skill
    return best_skill


def classify_archetype(question_text: str) -> str:
    """Classify a question into an archetype by keyword matching."""
    text = question_text.lower()
    best_arch = "find/solve"  # default
    best_count = 0
    for arch, keywords in ARCHETYPES.items():
        count = sum(1 for kw in keywords if kw in text)
        if count > best_count:
            best_count = count
            best_arch = arch
    return best_arch


async def main():
    conn = await asyncpg.connect(DATABASE_URL)

    # Query D7 Functions questions from exemplar_vectors
    # topic ILIKE '%function%' captures Functions-related exemplars
    rows = await conn.fetch("""
        SELECT id, question, solution, marks, topic, type, curriculum,
               paper_type, exam_type, source, difficulty
        FROM exemplar_vectors
        WHERE difficulty >= 6 AND difficulty <= 8
          AND (
            topic ILIKE '%function%'
            OR topic ILIKE '%composite%'
            OR topic ILIKE '%inverse%'
            OR topic ILIKE '%quadratic%'
            OR topic ILIKE '%rational%'
            OR topic ILIKE '%exponential%'
            OR topic ILIKE '%logarithm%'
            OR topic ILIKE '%polynomial%'
            OR topic ILIKE '%domain%'
            OR topic ILIKE '%transform%'
          )
        ORDER BY difficulty DESC, marks DESC
        LIMIT 50
    """)

    questions = []
    for row in rows:
        q_text = row["question"] or ""
        s_text = row["solution"] or ""
        questions.append({
            "id": row["id"],
            "question": q_text,
            "solution": s_text,
            "marks": row["marks"] or 0,
            "topic": "Functions",
            "skill": classify_skill(q_text, s_text),
            "archetype": classify_archetype(q_text),
            "difficulty": row["difficulty"] or 7,
            "source": row["source"] or "",
            "paper_type": row["paper_type"] or "Paper 1",
        })

    await conn.close()

    with open("questions.json", "w") as f:
        json.dump(questions, f, indent=2, ensure_ascii=False)

    print(f"Exported {len(questions)} questions to questions.json")

    # Print skill distribution
    from collections import Counter
    skill_counts = Counter(q["skill"] for q in questions)
    print("\nSkill distribution:")
    for skill, count in skill_counts.most_common():
        print(f"  {skill}: {count}")

    arch_counts = Counter(q["archetype"] for q in questions)
    print("\nArchetype distribution:")
    for arch, count in arch_counts.most_common():
        print(f"  {arch}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
