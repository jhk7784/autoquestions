# AutoQuestions — Project Context

## What This Is
Autonomous exemplar question diversity optimizer for IB AA HL D7 Functions questions.
Inspired by [karpathy/autoresearch](https://github.com/karpathy/autoresearch).

**Repo:** https://github.com/jhk7784/autoquestions
**Local:** `/Users/junghwankim/projects/autoquestions`

## How It Works
GitHub Actions runs every 10 minutes. Each cycle:
1. Loads `questions.json` (50 D7 Functions exemplars)
2. Computes composite diversity score across 6 dimensions
3. Gemini 2.5 Pro reasons about which question to rewrite and how
4. Gemini 3 Flash Preview formats the output as JSON
5. If diversity improved → commits. If not → discards.

## Current State (2026-03-14)
- **Baseline diversity:** 0.627 → 0.775 after taxonomy upgrade + cycles
- **GitHub Actions:** Active, running every 10 minutes
- **Secrets configured:** `GEMINI_API_KEY`, `GH_PAT` (fine-grained PAT)
- **IMPORTANT:** Both secrets were exposed in chat — rotate them

## File Map
| File | Purpose | Editable? |
|------|---------|-----------|
| `questions.json` | Working set of 50 D7 exemplars | Automated loop |
| `taxonomy.py` | Full IB-2 taxonomy (skills, archetypes, mechanisms, commands, styles) | Fixed — copied from IB-2 |
| `evaluate.py` | 6-dimension diversity scoring | Fixed |
| `mutate.py` | Two-stage Gemini mutation (reason + format) | Fixed |
| `run.py` | One cycle of the loop | Fixed |
| `seed.py` | One-time DB export from IB-2 `exemplar_vectors` | Run once |
| `reclassify.py` | One-time Gemini reclassification with full taxonomy | Run once |
| `results.tsv` | Experiment log (timestamp, scores, keep/discard) | Append-only |
| `program.md` | Human-readable system description | Human |
| `.github/workflows/autoquestions.yml` | Cron trigger every 10 min | Human |

## Diversity Metric (6 dimensions, composite 0-1, higher = better)
```
composite = 0.25 * skill_coverage
          + 0.20 * embedding_spread
          + 0.20 * archetype_diversity
          + 0.15 * mechanism_coverage
          + 0.10 * command_term_variety
          + 0.10 * style_balance
```

## Taxonomy Source
All taxonomy data in `taxonomy.py` was imported FROM `/Users/junghwankim/Documents/IB-2`:
- 12 T2 Functions skills — from `frontend/lib/topic-tree.ts`
- 6 archetypes — from `backend/archetypes.py`
- 18 difficulty mechanisms — from `backend/config.py`
- 26 IB command terms — from `backend/prompts.py` + `backend/generation.py`
- 3 style types — from `backend/style_context.py`
- D7 cognitive profile + mechanism synergies — from `backend/config.py`

**The taxonomy was NOT upgraded beyond IB-2.** It was brought up to parity.

## Known Gaps (from reclassification analysis)
- 49/50 questions are `pure_abstract` — almost no applied/modelling
- FUNC_SUM_PRODUCT_ROOTS has zero coverage
- `proof_by_contradiction_via_construction` and `constraint_optimization_chain` barely represented
- `investigation_conjecture`, `multi_representation`, `dual_skill_composition` mechanisms underused

## What Has NOT Been Done Yet

### 1. No feedback loop to IB-2
The optimized questions sit in `questions.json` only. They are NOT imported back
into IB-2's `exemplar_vectors` pgvector database. Options:
- Manual import: review + upsert best mutations into IB-2 DB
- Automated sync: script to push improved questions daily
- Pipeline tuning: use gap data to adjust IB-2's planner prompts/MMR weights

### 2. No taxonomy evolution (outer loop)
The findings doc (`docs/findings-taxonomy-improvement.md`) proposed a two-level loop:
- **Inner loop** (current): mutate questions, keep if diversity improves
- **Outer loop** (NOT built): evolve the taxonomy itself — discover new skill
  subdivisions, new archetypes, new diversity dimensions via embedding clustering

This is the most impactful next step. It would make autoquestions discover
taxonomy improvements that could flow BACK to IB-2's generation pipeline.

### 3. No analysis notebook
Unlike autoresearch's `analysis.ipynb`, there's no visualization of progress
over time. Would be useful: plot diversity score over cycles, show which
dimensions are improving vs plateauing.

## LLM Models Used
- **Reasoning:** `gemini-2.5-pro`
- **JSON formatting:** `gemini-3-flash-preview`
- **Embeddings:** `gemini-embedding-001`
- **Reclassification:** `gemini-2.5-flash` + `gemini-3-flash-preview`

## Database Connection (for seed.py / future import scripts)
IB-2 PostgreSQL: `postgresql://ib2admin:***@ib2-postgres.cfice0q2wena.ap-northeast-2.rds.amazonaws.com:5432/ib2`
Table: `exemplar_vectors` — columns: id, question, solution, marks, topic, type, curriculum, paper_type, exam_type, source, difficulty

## GitHub Actions Notes
- Cron: `*/10 * * * *` — can be delayed 15-20 min under GitHub load
- The bot commits as `autoquestions-bot <bot@autoquestions.dev>`
- If you're pushing changes locally, disable the workflow first:
  `gh workflow disable autoquestions.yml --repo jhk7784/autoquestions`
  Then re-enable after push:
  `gh workflow enable autoquestions.yml --repo jhk7784/autoquestions`

## Quick Commands
```bash
# Check latest results
tail -5 results.tsv

# Run one cycle locally
GEMINI_API_KEY="..." python3 run.py

# Evaluate current diversity
python3 evaluate.py

# Disable/enable the cron
gh workflow disable autoquestions.yml --repo jhk7784/autoquestions
gh workflow enable autoquestions.yml --repo jhk7784/autoquestions

# Watch a run
gh run watch --repo jhk7784/autoquestions
```
