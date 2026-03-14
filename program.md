# AutoQuestions — Autonomous Exemplar Question Diversity Optimizer

## What This Does

This system autonomously improves the diversity of a curated set of IB Mathematics AA HL
D7 Functions exemplar questions. It runs on GitHub Actions every 10 minutes.

Each cycle:
1. Loads the current question set from `questions.json`
2. Computes a composite diversity score (skill coverage + embedding spread + archetype diversity)
3. Identifies the biggest diversity gap
4. Uses Gemini 2.5 Pro to reason about how to rewrite the weakest question
5. Uses Gemini 3 Flash Preview to format the rewritten question as JSON
6. If the rewrite improves diversity → keeps the change
7. If not → discards

## Metric: Composite Diversity Score (0-1, higher = better)

```
diversity = 0.40 * skill_coverage + 0.35 * embedding_spread + 0.25 * archetype_diversity
```

- **Skill coverage**: How evenly questions span the 12 Functions sub-skills
- **Embedding spread**: Mean pairwise cosine distance (semantic distinctness)
- **Archetype diversity**: Fraction of question types represented (prove, find, sketch, etc.)

## Files

| File | Purpose | Who Edits |
|------|---------|-----------|
| `questions.json` | The question set being optimized | Automated loop |
| `evaluate.py` | Computes diversity score | Fixed |
| `mutate.py` | Two-stage Gemini mutation | Fixed |
| `run.py` | Runs one cycle | Fixed |
| `results.tsv` | Experiment log | Automated loop |
| `seed.py` | One-time DB export | Run once |

## Inspired By

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) — same loop pattern,
but optimizing question diversity instead of validation loss.
