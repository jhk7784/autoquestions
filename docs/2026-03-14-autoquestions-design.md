# AutoQuestions — Design Spec

**Date:** 2026-03-14
**Goal:** Autonomous loop that iterates on D7 IB AA HL Functions exemplar questions to maximize diversity.

## Overview

Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch), this system runs an autonomous loop on GitHub Actions every 10 minutes. Each cycle:

1. Reads the current set of D7 Functions exemplar questions (`questions.json`)
2. Computes a composite diversity score
3. Uses Gemini 2.5 Pro to reason about and rewrite the lowest-diversity question
4. Uses Gemini 3 Flash Preview to format the output as JSON
5. Re-computes diversity score
6. If improved → commits the change. If not → discards.

## Architecture

### Files

| File | Role | Mutated By |
|------|------|------------|
| `program.md` | Human-readable description of the system | Human |
| `questions.json` | Working set of ~20-50 D7 Functions exemplars | Loop |
| `evaluate.py` | Computes composite diversity score | Nobody (fixed) |
| `mutate.py` | Two-stage Gemini mutation (reason + format) | Nobody (fixed) |
| `run.py` | One cycle of the loop | Nobody (fixed) |
| `seed.py` | One-time DB export of initial questions | Nobody (run once) |
| `results.tsv` | Experiment log | Loop (append-only) |
| `.github/workflows/autoquestions.yml` | Cron trigger | Human |

### Diversity Metric (composite, 0-1, higher = better)

```
diversity_score = 0.40 * skill_coverage + 0.35 * embedding_spread + 0.25 * archetype_diversity
```

**Skill Coverage (0-1):** Evenness of distribution across T2 Functions' 12 sub-skills (FUNC_DOMAIN through FUNC_GRAPH_SKETCH). Uses normalized standard deviation.

**Embedding Spread (0-1):** Mean pairwise cosine distance between all question embeddings (Gemini text-embedding-004, 768-dim). Normalized to [0,1].

**Archetype Diversity (0-1):** Fraction of distinct question types represented. Archetypes: prove, find/solve, sketch/graph, interpret/explain, model/apply, show that, multi-step synthesis. Classified by keyword matching.

### Mutation Strategy

**Target selection:**
1. Find most over-represented skill → pick questions in that cluster
2. Among those, find the pair with highest embedding similarity (most redundant)
3. Pick the one using the most common archetype
4. That question gets rewritten to target the least-covered skill + rarest archetype

**Two-stage LLM call:**
1. **Reasoner (Gemini 2.5 Pro):** Receives full context (questions, diversity analysis, gap identification). Outputs free-form reasoning + rewritten question.
2. **Formatter (Gemini 3 Flash Preview):** Converts reasoner output into exact JSON schema.

**Guardrails:**
- Invalid JSON from formatter → discard, log as `crash`
- Rewritten question has same skill/archetype → discard (no-op mutation)
- 3 consecutive discards on same question → skip, try different target

### GitHub Actions

- Cron: `*/10 * * * *` (every 10 minutes)
- Manual trigger: `workflow_dispatch`
- Runner: `ubuntu-latest`, Python 3.12
- Secrets: `GEMINI_API_KEY`, `GH_PAT` (fine-grained, Contents + Workflows R/W)
- Commit strategy: bot commits `questions.json` + `results.tsv` only if diversity improved

### Question Schema

Each question in `questions.json`:
```json
{
  "id": "string",
  "question": "string (LaTeX)",
  "solution": "string (LaTeX)",
  "marks": 8,
  "topic": "Functions",
  "skill": "FUNC_COMPOSITE",
  "archetype": "find/solve",
  "difficulty": 7,
  "source": "2022_May_AA_HL_P1_TZ1",
  "paper_type": "Paper 1"
}
```

### Dependencies

- `google-genai` — Gemini API
- `numpy` — cosine distance calculations
- `asyncpg` — DB access (seed.py only)
