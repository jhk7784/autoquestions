"""
Full IB-2 taxonomy imported from the production question generation system.

This is the canonical source of truth for skills, archetypes, mechanisms,
command terms, and style types used by evaluate.py and mutate.py.
"""

# ─── T2 Functions Skills (12) ─────────────────────────────────────────────────
# From IB-2: frontend/lib/topic-tree.ts + frontend/lib/skills.ts

FUNCTIONS_SKILLS = {
    "FUNC_DOMAIN": "Domain and range",
    "FUNC_COMPOSITE": "Composite functions",
    "FUNC_INVERSE": "Inverse functions",
    "FUNC_TRANSFORM": "Transformations",
    "FUNC_QUADRATIC": "Quadratic functions",
    "FUNC_RATIONAL": "Rational functions",
    "FUNC_EXP": "Exponential functions",
    "FUNC_LOG": "Logarithmic functions",
    "FUNC_MODULUS": "Absolute value functions",
    "FUNC_POLYNOMIAL": "Polynomial functions",
    "FUNC_SUM_PRODUCT_ROOTS": "Sum & product of roots",
    "FUNC_GRAPH_SKETCH": "Graph sketching",
}

ALL_SKILLS = list(FUNCTIONS_SKILLS.keys())

# ─── Question Archetypes (6) ──────────────────────────────────────────────────
# From IB-2: backend/archetypes.py

QUESTION_ARCHETYPES = {
    "proof_by_contradiction_via_construction": {
        "name": "Build then Contradict",
        "description": "Student constructs something first, then uses it to derive a contradiction",
        "required_mechanisms": ["proof_unfamiliar_context", "indirect_approach"],
        "example": "Find roots of a polynomial, then show those roots cannot satisfy a given condition",
    },
    "representation_bridge": {
        "name": "Representation Bridge",
        "description": "Same mathematical object viewed through two representations, then connected",
        "required_mechanisms": ["multi_representation", "transfer_generalization"],
        "example": "Complex numbers in polar form → vectors → geometric property derivation",
    },
    "constraint_optimization_chain": {
        "name": "Constraint Chain",
        "description": "Constraints added step-by-step, each narrowing the optimization problem",
        "required_mechanisms": ["constraint_reasoning", "hence_chains"],
        "example": "Find the maximum area given fixed perimeter, then given one side must be integer",
    },
    "reverse_engineering": {
        "name": "Reverse Engineering",
        "description": "Given the result, work backwards to deduce conditions",
        "required_mechanisms": ["hidden_structure", "strategic_path"],
        "example": "Given that the integral equals 12, determine the function f(x)",
    },
    "generalization_from_special_case": {
        "name": "Special Case to General",
        "description": "Solve a specific case, then generalize — the generalization requires new skills",
        "required_mechanisms": ["transfer_generalization", "proof_unfamiliar_context"],
        "example": "Prove for n=3, then prove for general n using a different technique",
    },
    "spatial_coordinate_bridge": {
        "name": "Spatial Coordinate Bridge",
        "description": "Transition between visual/geometric and coordinate/algebraic representations",
        "required_mechanisms": ["multi_representation", "transfer_generalization"],
        "example": "Express a circle geometrically, derive its equation, find tangent lines, interpret geometrically",
    },
}

ALL_ARCHETYPES = list(QUESTION_ARCHETYPES.keys())

# ─── Difficulty Mechanisms (18) ───────────────────────────────────────────────
# From IB-2: backend/config.py DIFFICULTY_MECHANISMS

DIFFICULTY_MECHANISMS = {
    "direct_application": "Single concept, direct formula or method application.",
    "method_selection": "Student must decide WHICH method to use (not given explicitly).",
    "multi_concept_same_topic": "Requires 2+ concepts from the SAME syllabus topic.",
    "cross_concept": "Requires connecting concepts from different parts of the same topic.",
    "strategic_path": "Multiple valid approaches exist; student must choose an efficient path.",
    "non_routine": "Problem does not match any standard textbook template.",
    "proof_adapt": "'Show that' where the standard technique must be adapted.",
    "cross_topic_synthesis": "Combine concepts from 2 DIFFERENT IB syllabus topics.",
    "hidden_structure": "The mathematical structure needed is NOT obvious from the problem statement.",
    "hence_chains": "Later parts depend on earlier results in NON-OBVIOUS ways.",
    "proof_unfamiliar_context": "'Show that' or 'Prove' where technique needs significant adaptation.",
    "constraint_reasoning": "Constraints eliminate standard approaches, forcing alternative methods.",
    "dual_skill_composition": "Nontrivial combination of 2 DISTINCT skills from different domains.",
    "transfer_generalization": "Apply a known technique to a completely novel context.",
    "investigation_conjecture": "Pattern discovery followed by formal proof.",
    "indirect_approach": "Direct method fails; requires insight (symmetry, substitution, contradiction).",
    "multi_representation": "Translate between algebraic, geometric, and analytic representations.",
    "sting_in_tail_synthesis": "Final part combines ALL previous results in a non-trivial way.",
}

ALL_MECHANISMS = list(DIFFICULTY_MECHANISMS.keys())

# D7-available mechanisms (from IB-2 config.py DIFFICULTY_CONFIG)
D7_MECHANISMS = [
    "cross_topic_synthesis", "hidden_structure", "hence_chains",
    "proof_unfamiliar_context", "constraint_reasoning",
]

# ─── D7 Mechanism Synergies ──────────────────────────────────────────────────
# From IB-2: backend/config.py MECHANISM_SYNERGIES

D7_SYNERGIES = {
    ("hidden_structure", "multi_representation"): {"effect": "Discover hidden structure through representation change", "boost": 0.3},
    ("cross_topic_synthesis", "hence_chains"): {"effect": "Multi-topic result feeds forward through dependent parts", "boost": 0.35},
    ("hidden_structure", "proof_unfamiliar_context"): {"effect": "Hidden structure revealed through unfamiliar proof technique", "boost": 0.35},
    ("cross_topic_synthesis", "hidden_structure"): {"effect": "Cross-topic connection reveals the hidden structure", "boost": 0.35},
    ("cross_topic_synthesis", "constraint_reasoning"): {"effect": "Cross-topic synthesis under constraints", "boost": 0.25},
    ("hence_chains", "hidden_structure"): {"effect": "Each 'hence' step reveals more of the hidden structure", "boost": 0.2},
    ("hence_chains", "constraint_reasoning"): {"effect": "Hence chain where constraints force non-obvious next step", "boost": 0.2},
    ("proof_unfamiliar_context", "constraint_reasoning"): {"effect": "Proof in unfamiliar context where standard approaches are blocked", "boost": 0.25},
}

# ─── IB Command Terms (26) ───────────────────────────────────────────────────
# From IB-2: backend/prompts.py IB_COMMAND_TERMS + backend/generation.py COMMAND_TERM_SCORES

COMMAND_TERMS = {
    # AO1 — Knowledge & Understanding
    "write down": {"ao": "AO1", "severity": 1.0, "cognitive": "recall", "typical_d": "D1-D3"},
    "state": {"ao": "AO1", "severity": 1.0, "cognitive": "recall", "typical_d": "D1-D3"},
    "calculate": {"ao": "AO1", "severity": 1.0, "cognitive": "application", "typical_d": "D1-D4"},
    "estimate": {"ao": "AO1", "severity": 1.0, "cognitive": "application", "typical_d": "D2-D4"},
    "list": {"ao": "AO1", "severity": 1.0, "cognitive": "recall", "typical_d": "D1-D2"},
    "label": {"ao": "AO3", "severity": 1.0, "cognitive": "communication", "typical_d": "D1-D2"},
    "plot": {"ao": "AO3", "severity": 1.0, "cognitive": "communication", "typical_d": "D2-D3"},
    # AO1-AO2 — Application
    "find": {"ao": "AO1-AO2", "severity": 1.5, "cognitive": "application", "typical_d": "D1-D6"},
    "determine": {"ao": "AO1-AO2", "severity": 1.5, "cognitive": "reasoning", "typical_d": "D3-D6"},
    "sketch": {"ao": "AO3", "severity": 1.5, "cognitive": "communication", "typical_d": "D3-D6"},
    "differentiate": {"ao": "AO1", "severity": 1.5, "cognitive": "application", "typical_d": "D2-D5"},
    "integrate": {"ao": "AO1", "severity": 1.5, "cognitive": "application", "typical_d": "D2-D5"},
    "construct": {"ao": "AO3", "severity": 1.5, "cognitive": "communication", "typical_d": "D3-D5"},
    "describe": {"ao": "AO3", "severity": 1.5, "cognitive": "communication", "typical_d": "D3-D5"},
    # AO2-AO3 — Reasoning
    "show that": {"ao": "AO2", "severity": 2.0, "cognitive": "reasoning", "typical_d": "D4-D8"},
    "show": {"ao": "AO2", "severity": 2.0, "cognitive": "reasoning", "typical_d": "D3-D7"},
    "solve": {"ao": "AO2", "severity": 2.0, "cognitive": "application", "typical_d": "D3-D7"},
    "explain": {"ao": "AO3-AO5", "severity": 2.0, "cognitive": "reasoning", "typical_d": "D5-D7"},
    "predict": {"ao": "AO2", "severity": 2.0, "cognitive": "application", "typical_d": "D4-D6"},
    "comment": {"ao": "AO3", "severity": 2.0, "cognitive": "communication", "typical_d": "D4-D6"},
    "compare": {"ao": "AO3", "severity": 2.0, "cognitive": "communication", "typical_d": "D4-D7"},
    # AO2-AO5 — Strategic Reasoning
    "hence": {"ao": "AO2", "severity": 2.5, "cognitive": "strategic", "typical_d": "D4-D8"},
    "hence or otherwise": {"ao": "AO2-AO3", "severity": 2.5, "cognitive": "strategic", "typical_d": "D5-D8"},
    "deduce": {"ao": "AO5", "severity": 2.5, "cognitive": "reasoning", "typical_d": "D5-D8"},
    "verify": {"ao": "AO2", "severity": 2.5, "cognitive": "reasoning", "typical_d": "D4-D7"},
    # AO5-AO6 — Higher-order
    "prove": {"ao": "AO5", "severity": 3.0, "cognitive": "reasoning", "typical_d": "D6-D8"},
    "justify": {"ao": "AO5", "severity": 3.0, "cognitive": "reasoning", "typical_d": "D6-D8"},
    "investigate": {"ao": "AO6", "severity": 3.0, "cognitive": "inquiry", "typical_d": "D7-D8"},
    "suggest": {"ao": "AO6", "severity": 3.0, "cognitive": "inquiry", "typical_d": "D5-D7"},
}

ALL_COMMAND_TERMS = list(COMMAND_TERMS.keys())

# ─── Style Types (3) ─────────────────────────────────────────────────────────
# From IB-2: backend/style_context.py

STYLE_TYPES = {
    "pure_abstract": "Pure mathematical context, no real-world scenario",
    "applied_real_world": "Framed in a real-world scenario (physics, economics, biology, etc.)",
    "modelling": "Mathematical modelling problem from realistic context",
}

ALL_STYLES = list(STYLE_TYPES.keys())

# ─── D7 Cognitive Framework ──────────────────────────────────────────────────
# From IB-2: backend/config.py DIFFICULTY_CONFIG

D7_PROFILE = {
    "dok": "3-4",
    "bloom": "Evaluate/Create",
    "solo": "Relational → Extended Abstract",
    "ao": "AO5-AO6",
    "min_mechanisms": 2,
    "part_escalation": True,
    "marks_range": (6, 10),
}
