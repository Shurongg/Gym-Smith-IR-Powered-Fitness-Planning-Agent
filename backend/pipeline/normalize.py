"""
Pure normalization for exercise KB metadata.

Contract per spec docs/superpowers/specs/normalize_knowledge_base_spec.md:
- equipment: 9 atomic tokens (spec §D1)
- muscles:   18 atomic tokens after vocab unification (spec §D2)
- category:  lowercased (spec §D3)

No I/O, no Chroma dependency — just data transformations.
`build_exercise_metadata` is the single seam that ingest calls.
"""

ATOMIC_EQUIPMENT: list[str] = [
    "barbell", "bench", "dumbbell", "pull-up bar", "bodyweight",
    "cable", "kettlebell", "machine", "resistance band",
]

ATOMIC_MUSCLES: list[str] = [
    "abdominals", "abductors", "adductors", "biceps", "calves", "chest",
    "forearms", "general", "glutes", "hamstrings", "lats", "lower back",
    "middle back", "neck", "quadriceps", "shoulders", "traps", "triceps",
]

MUSCLE_ALIASES: dict[str, str] = {
    "abs": "abdominals",
    "quads": "quadriceps",
}

_EQUIPMENT_SET = set(ATOMIC_EQUIPMENT)
_MUSCLES_SET = set(ATOMIC_MUSCLES)


def _slugify(token: str) -> str:
    return token.replace("-", "_").replace(" ", "_")


def parse_equipment(raw: str) -> set[str]:
    if not raw:
        return set()
    out: set[str] = set()
    for part in raw.split(","):
        tok = part.strip().lower()
        if tok in _EQUIPMENT_SET:
            out.add(tok)
    return out


def parse_muscles(raw: str) -> set[str]:
    if not raw:
        return set()
    out: set[str] = set()
    for part in raw.split(","):
        tok = part.strip().lower()
        tok = MUSCLE_ALIASES.get(tok, tok)
        if tok in _MUSCLES_SET:
            out.add(tok)
    return out


def equipment_booleans(atoms: set[str]) -> dict[str, bool]:
    return {f"equipment_{_slugify(a)}": (a in atoms) for a in ATOMIC_EQUIPMENT}


def muscle_booleans(atoms: set[str], prefix: str) -> dict[str, bool]:
    return {f"{prefix}{_slugify(a)}": (a in atoms) for a in ATOMIC_MUSCLES}


def build_exercise_metadata(
    name: str,
    category: str,
    muscles_str: str,
    muscles_secondary_str: str,
    equipment_str: str,
    description: str,
) -> dict:
    """Assemble the full normalized metadata dict for one exercise.

    Additive: keeps legacy joined-string fields (`equipment` / `muscles` /
    `muscles_secondary`) so read-only consumers keep working, adds `_raw`
    aliases per spec §"Non-destructive rule", lowercases `category` per §D3,
    expands equipment and muscles into boolean fields per §D1/§D2.
    """
    eq_atoms = parse_equipment(equipment_str)
    prim_atoms = parse_muscles(muscles_str)
    sec_atoms = parse_muscles(muscles_secondary_str)

    meta: dict = {
        "name": name,
        "category": category.lower(),
        # legacy joined-string fields — read-only consumers still use these
        "muscles": muscles_str,
        "muscles_secondary": muscles_secondary_str,
        "equipment": equipment_str,
        "description": description[:400],
        # explicit raw aliases per spec
        "equipment_raw": equipment_str,
        "muscles_raw": muscles_str,
        "muscles_secondary_raw": muscles_secondary_str,
    }
    meta.update(equipment_booleans(eq_atoms))
    meta.update(muscle_booleans(prim_atoms, prefix="muscle_"))
    meta.update(muscle_booleans(sec_atoms, prefix="muscle_secondary_"))
    return meta
