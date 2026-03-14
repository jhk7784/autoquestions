# Findings: Improving AutoQuestions with Autoresearch Patterns

## Date: 2026-03-14

## Context

AutoQuestions is a clone of [karpathy/autoresearch](https://github.com/karpathy/autoresearch) that optimizes diversity of IB Math AA HL D7 Functions exemplar questions. This document captures findings from investigating how to improve question generation using autoresearch patterns.

## Current System Status

- **Diversity score**: 0.6265 → 0.6750 after 2 successful mutation cycles
- **Question set**: 50 questions in `questions.json`
- **Loop**: GitHub Actions runs every 10 minutes, mutates one question per cycle

## Problem: The Taxonomy Is Too Coarse

### Current Skills (12, hardcoded in evaluate.py)
FUNC_DOMAIN, FUNC_COMPOSITE, FUNC_INVERSE, FUNC_TRANSFORM, FUNC_QUADRATIC, FUNC_RATIONAL, FUNC_EXP, FUNC_LOG, FUNC_MODULUS, FUNC_POLYNOMIAL, FUNC_SUM_PRODUCT_ROOTS, FUNC_GRAPH_SKETCH

### Current Archetypes (7, hardcoded in evaluate.py)
prove, find/solve, sketch/graph, interpret/explain, model/apply, show that, multi-step synthesis

### Why This Is Limiting

1. **Too coarse**: 12 skills map to IB syllabus section headings, but real exam questions blend multiple concepts. A question about "finding the inverse of a rational function and sketching its graph" touches FUNC_INVERSE + FUNC_RATIONAL + FUNC_GRAPH_SKETCH but gets classified as only one.

2. **Keyword classification is brittle**: In `seed.py`, classification uses simple keyword matching (e.g., `\frac{` → FUNC_RATIONAL). A question with fractions in the solution but fundamentally about composites gets misclassified.

3. **Archetypes too narrow**: 26 of 50 questions are tagged "prove" and 18 are "find/solve" — that's 88% in just 2 categories. The taxonomy doesn't capture real variety.

4. **Diversity metric plateaus**: Once all 12 skills and 7 archetypes are represented, the score has limited room to grow. The system can't discover *new* dimensions of diversity.

5. **Taxonomy was invented locally**: The 12 skills and 7 archetypes were created in `seed.py` using keyword heuristics — they are NOT pulled from a canonical taxonomy in the ib-2 project database. The ib-2 project may have a richer, more accurate taxonomy.

## Key Insight from Autoresearch

Autoresearch's power comes from **letting the agent freely edit the "program" (train.py) while keeping the evaluation fixed**. AutoQuestions currently does the opposite — the evaluation categories (skills/archetypes) are hardcoded, and only the questions change. This limits what the system can discover.

### Autoresearch Architecture Comparison

| autoresearch | autoquestions (current) | autoquestions (proposed) |
|---|---|---|
| `train.py` (agent edits freely) | questions.json (agent edits) | `taxonomy.md` + question mutations |
| `prepare.py` (fixed evaluation) | `evaluate.py` (fixed scoring) | `evaluate.py` (fixed scoring) |
| `program.md` (human goals) | `program.md` (IB constraints) | `program.md` (IB constraints) |
| val_bpb metric | composite diversity score | composite diversity score |

### Autoresearch Known Issue: Low Creativity (Issue #22)
Agents tend toward small incremental tweaks rather than bold changes. AutoQuestions likely has the same issue since it can only swap one question's skill/archetype per cycle within fixed categories.

## Proposed Improvements

### 1. Make the Taxonomy Evolvable (like `program.md`)

Create a `taxonomy.md` file (analogous to autoresearch's `program.md`) that the mutation agent can propose changes to:

- **Discover finer-grained skills** — e.g., split FUNC_RATIONAL into FUNC_RATIONAL_ASYMPTOTE, FUNC_RATIONAL_PARTIAL_FRACTION, FUNC_RATIONAL_INEQUALITY
- **Discover cross-cutting dimensions** — e.g., "requires graphical reasoning", "involves proof by contradiction", "multi-function interaction"
- **Expand archetypes** beyond 7 to match what the data actually shows

### 2. Use Embedding-Driven Skill Discovery

Instead of hardcoded keyword lists, use Gemini embeddings to cluster questions and discover natural groupings:

```
1. Embed all 50 questions
2. Cluster (e.g., k-means with varying k)
3. Ask Gemini to label each cluster with a descriptive skill name
4. Use these emergent skills as the new taxonomy
```

This would surface dimensions of variation the IB syllabus headings miss — like "algebraic manipulation intensity", "multi-step reasoning depth", or "graphical vs symbolic approach".

### 3. Two-Level Optimization Loop

- **Inner loop** (current, every 10 min): mutate one question, accept if diversity improves
- **Outer loop** (new, every N inner cycles): evaluate whether the taxonomy itself should evolve — add/split/merge skill categories based on clustering analysis, then re-score everything

### 4. Richer Diversity Metric

Add beyond current composite score:
- **Novelty score**: How different is each new question from its nearest neighbor in embedding space?
- **Difficulty spread**: Variance across cognitive complexity, not just IB difficulty rating
- **Solution-method diversity**: Do questions require different mathematical techniques?

## Next Step: Connect to ib-2 Taxonomy

The ib-2 project (PostgreSQL database at `ib2-postgres.cfice0q2wena.ap-northeast-2.rds.amazonaws.com`, table `exemplar_vectors`) may contain a richer taxonomy than what was exported. Investigate:
- What columns/tags exist in the database beyond what `seed.py` pulled?
- Does ib-2 have its own skill tree or categorization system?
- Can we pull the full taxonomy and use it as the foundation instead of keyword-heuristic skills?

## References

- [karpathy/autoresearch](https://github.com/karpathy/autoresearch)
- [autoresearch Issue #22: Low creativity](https://github.com/karpathy/autoresearch/issues/22)
- [autoresearch Discussion #43: Session report](https://github.com/karpathy/autoresearch/discussions/43)
