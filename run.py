from __future__ import annotations

"""
Main loop: run one cycle of the autoquestions diversity optimizer.

1. Load questions.json
2. Compute current diversity score
3. Mutate one question via Gemini
4. Compute new diversity score
5. If improved → overwrite questions.json (caller commits)
6. If not → revert questions.json to original
7. Append result to results.tsv
"""

import json
import os
import sys
import traceback
from datetime import datetime, timezone

from evaluate import diversity_score
from mutate import mutate

QUESTIONS_FILE = "questions.json"
RESULTS_FILE = "results.tsv"


def get_embeddings(questions: list[dict]) -> list[list[float]] | None:
    """
    Compute embeddings for all questions using Gemini text-embedding-004.
    Returns None if embedding fails (score will be computed without embedding spread).
    """
    try:
        from google import genai
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        texts = [q["question"][:2048] for q in questions]
        response = client.models.embed_content(
            model="gemini-embedding-001",
            contents=texts,
        )
        return [e.values for e in response.embeddings]
    except Exception as e:
        print(f"WARNING: Embedding failed, proceeding without embedding spread: {e}")
        return None


def init_results_file():
    """Create results.tsv with header if it doesn't exist."""
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w") as f:
            f.write("timestamp\told_score\tnew_score\tdelta\tstatus\tdescription\n")


def append_result(old_score: float, new_score: float, status: str, description: str):
    """Append one row to results.tsv."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    delta = new_score - old_score
    with open(RESULTS_FILE, "a") as f:
        f.write(f"{ts}\t{old_score:.6f}\t{new_score:.6f}\t{delta:+.6f}\t{status}\t{description}\n")


def run_cycle():
    """Run one mutation cycle. Returns True if diversity improved."""

    # Load current questions
    with open(QUESTIONS_FILE) as f:
        questions = json.load(f)

    print(f"Loaded {len(questions)} questions")

    # Compute current diversity
    embeddings = get_embeddings(questions)
    old_result = diversity_score(questions, embeddings)
    old_score = old_result["composite"]
    print(f"Current diversity: {old_score:.6f}")
    print(f"  Skill coverage:     {old_result['skill_coverage']}")
    print(f"  Embedding spread:   {old_result['embedding_spread']}")
    print(f"  Archetype diversity: {old_result['archetype_diversity']}")

    # Mutate
    print("\nMutating...")
    new_questions, target_idx, description = mutate(questions, embeddings)
    print(f"  {description}")

    # Compute new diversity
    new_embeddings = get_embeddings(new_questions)
    new_result = diversity_score(new_questions, new_embeddings)
    new_score = new_result["composite"]
    delta = new_score - old_score
    print(f"\nNew diversity: {new_score:.6f} (delta: {delta:+.6f})")

    if new_score > old_score:
        # Improvement — write new questions
        with open(QUESTIONS_FILE, "w") as f:
            json.dump(new_questions, f, indent=2, ensure_ascii=False)
        append_result(old_score, new_score, "keep", description)
        print(f"KEEP — diversity improved by {delta:+.6f}")
        return True
    else:
        # No improvement — discard (don't modify questions.json)
        append_result(old_score, new_score, "discard", description)
        print(f"DISCARD — diversity did not improve ({delta:+.6f})")
        return False


def main():
    init_results_file()

    try:
        improved = run_cycle()
        sys.exit(0 if improved else 0)  # Always exit 0 — discards are normal
    except json.JSONDecodeError as e:
        print(f"CRASH — invalid JSON from formatter: {e}")
        init_results_file()
        append_result(0.0, 0.0, "crash", f"JSON parse error: {e}")
        sys.exit(0)  # Don't fail the GH Action
    except Exception as e:
        print(f"CRASH — {e}")
        traceback.print_exc()
        init_results_file()
        append_result(0.0, 0.0, "crash", f"error: {str(e)[:100]}")
        sys.exit(0)


if __name__ == "__main__":
    main()
