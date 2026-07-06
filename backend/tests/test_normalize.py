"""
Spec-mandated tests (docs/superpowers/specs/normalize_knowledge_base_spec.md
§ "TDD contract") reformulated as pure unit tests over synthetic input strings.

Data-independence rule: no test in this file may query a real ChromaDB
collection or assert that any specific raw string exists in the ingested data.
Every input is a literal string defined right here.
"""
import pytest

from pipeline.normalize import (
    ATOMIC_EQUIPMENT,
    ATOMIC_MUSCLES,
    build_exercise_metadata,
    equipment_booleans,
    muscle_booleans,
    parse_equipment,
    parse_muscles,
)


# ---------------------------------------------------------------------------
# Parser edge cases (supporting tests, not spec-mandated)
# ---------------------------------------------------------------------------

class TestParseEquipment:
    def test_single_atom(self):
        assert parse_equipment("dumbbell") == {"dumbbell"}

    def test_comma_joined_multi(self):
        assert parse_equipment("dumbbell, bench") == {"dumbbell", "bench"}

    def test_order_independent(self):
        assert parse_equipment("bench, barbell") == parse_equipment("barbell, bench")

    def test_case_insensitive(self):
        assert parse_equipment("Dumbbell, BENCH") == {"dumbbell", "bench"}

    def test_extra_whitespace(self):
        assert parse_equipment("  dumbbell ,  bench  ") == {"dumbbell", "bench"}

    def test_pull_up_bar_atomic(self):
        assert parse_equipment("pull-up bar") == {"pull-up bar"}

    def test_resistance_band_atomic(self):
        assert parse_equipment("resistance band, bodyweight") == {"resistance band", "bodyweight"}

    def test_empty_string(self):
        assert parse_equipment("") == set()

    def test_unknown_token_ignored(self):
        assert parse_equipment("dumbbell, moonrock") == {"dumbbell"}


class TestParseMuscles:
    def test_lowercase_single(self):
        assert parse_muscles("biceps") == {"biceps"}

    def test_uppercase_normalized(self):
        assert parse_muscles("Biceps") == {"biceps"}

    def test_multi_word_lower_back(self):
        assert parse_muscles("lower back") == {"lower back"}

    def test_empty_string(self):
        assert parse_muscles("") == set()

    def test_general_passthrough(self):
        assert parse_muscles("general") == {"general"}

    def test_unknown_token_ignored(self):
        assert parse_muscles("biceps, ectoplasm") == {"biceps"}


class TestEquipmentBooleansShape:
    def test_all_nine_keys_present(self):
        result = equipment_booleans(set())
        assert set(result.keys()) == {
            "equipment_barbell", "equipment_bench", "equipment_dumbbell",
            "equipment_pull_up_bar", "equipment_bodyweight", "equipment_cable",
            "equipment_kettlebell", "equipment_machine", "equipment_resistance_band",
        }
        assert all(v is False for v in result.values())


class TestMuscleBooleansShape:
    def test_all_eighteen_keys_present_primary_prefix(self):
        result = muscle_booleans(set(), prefix="muscle_")
        assert len(result) == 18
        assert all(k.startswith("muscle_") for k in result)
        assert all(v is False for v in result.values())

    def test_secondary_prefix(self):
        result = muscle_booleans({"biceps"}, prefix="muscle_secondary_")
        assert result["muscle_secondary_biceps"] is True
        assert result["muscle_secondary_triceps"] is False

    def test_slugification_lower_back(self):
        result = muscle_booleans({"lower back"}, prefix="muscle_")
        assert result["muscle_lower_back"] is True


# ---------------------------------------------------------------------------
# The 6 spec-mandated tests (T1–T6) — pure over synthetic input.
# ---------------------------------------------------------------------------

class TestT1_EquipmentMembership:
    """Spec T1: raw 'dumbbell, bench' must set BOTH equipment_dumbbell AND equipment_bench True."""

    def test_dumbbell_bench_sets_both_booleans(self):
        atoms = parse_equipment("dumbbell, bench")
        assert atoms == {"dumbbell", "bench"}
        booleans = equipment_booleans(atoms)
        assert booleans["equipment_dumbbell"] is True
        assert booleans["equipment_bench"] is True
        # And every OTHER equipment stays False — expansion is exact, not wide open.
        assert booleans["equipment_barbell"] is False
        assert booleans["equipment_cable"] is False


class TestT2_EquipmentCountSanity:
    """Spec T2: any raw string that names an atom as one of its comma-separated
    tokens must set that atom's boolean True. Naive exact-string matching against
    the joined string would miss the multi-equipment case — that's the recall bug.
    """

    @pytest.mark.parametrize("raw", [
        "dumbbell",
        "dumbbell, bench",
        "barbell, dumbbell",
        "dumbbell, bench, barbell",
        "kettlebell, dumbbell",
        "bench, dumbbell, kettlebell, bodyweight",
    ])
    def test_every_raw_naming_dumbbell_sets_boolean(self, raw):
        booleans = equipment_booleans(parse_equipment(raw))
        assert booleans["equipment_dumbbell"] is True, (
            f"raw {raw!r} names dumbbell but expansion failed to set the boolean"
        )

    def test_raw_without_dumbbell_does_not_set_boolean(self):
        assert equipment_booleans(parse_equipment("barbell, bench"))["equipment_dumbbell"] is False


class TestT3_MuscleVocabUnified:
    """Spec T3: after parsing, only the 18 atomic muscles ever appear. Aliases
    (abs, quads) get mapped. Uppercase variants get lowercased. No leakage."""

    ATOMIC = set(ATOMIC_MUSCLES)

    def test_atoms_pass_through(self):
        for atom in ATOMIC_MUSCLES:
            assert parse_muscles(atom) == {atom}

    def test_alias_abs_to_abdominals(self):
        assert parse_muscles("abs") == {"abdominals"}
        assert parse_muscles("Abs") == {"abdominals"}

    def test_alias_quads_to_quadriceps(self):
        assert parse_muscles("quads") == {"quadriceps"}
        assert parse_muscles("Quads") == {"quadriceps"}

    @pytest.mark.parametrize("raw", [
        "Abs", "Quads", "Biceps", "Chest", "TRICEPS",
        "Abs, Quads",
        "Biceps, Hamstrings, Chest, Triceps",
        "Shoulders, Biceps, Hamstrings, Glutes, Lats, Quads, Abs",
    ])
    def test_output_only_contains_atomic_names(self, raw):
        result = parse_muscles(raw)
        assert result <= self.ATOMIC
        assert "abs" not in result and "quads" not in result

    def test_boolean_keyset_is_exactly_the_18_atoms(self):
        result = muscle_booleans(parse_muscles("Abs, Quads, Biceps"), prefix="muscle_")
        assert set(result.keys()) == {f"muscle_{a.replace(' ', '_').replace('-', '_')}"
                                       for a in ATOMIC_MUSCLES}


class TestT4_MuscleMembership:
    """Spec T4: raw 'Biceps, Hamstrings' → muscle_biceps AND muscle_hamstrings True."""

    def test_biceps_hamstrings_sets_both_booleans(self):
        atoms = parse_muscles("Biceps, Hamstrings")
        assert atoms == {"biceps", "hamstrings"}
        booleans = muscle_booleans(atoms, prefix="muscle_")
        assert booleans["muscle_biceps"] is True
        assert booleans["muscle_hamstrings"] is True
        # every other muscle stays False
        assert booleans["muscle_chest"] is False
        assert booleans["muscle_abdominals"] is False

    def test_secondary_prefix_variant(self):
        atoms = parse_muscles("Biceps, Hamstrings")
        booleans = muscle_booleans(atoms, prefix="muscle_secondary_")
        assert booleans["muscle_secondary_biceps"] is True
        assert booleans["muscle_secondary_hamstrings"] is True


class TestT5_RawFieldsPreserved:
    """Spec T5: build_exercise_metadata keeps the raw joined strings verbatim
    under _raw aliases so a bad mapping is traceable/revertible."""

    def test_all_three_raw_fields_present(self):
        meta = build_exercise_metadata(
            name="Test Ex",
            category="Chest",
            muscles_str="Biceps, Hamstrings",
            muscles_secondary_str="abdominals, glutes",
            equipment_str="dumbbell, bench",
            description="do a thing",
        )
        assert meta["equipment_raw"] == "dumbbell, bench"
        assert meta["muscles_raw"] == "Biceps, Hamstrings"
        assert meta["muscles_secondary_raw"] == "abdominals, glutes"

    def test_raw_fields_survive_empty_strings(self):
        meta = build_exercise_metadata(
            name="Test", category="Cardio", muscles_str="",
            muscles_secondary_str="", equipment_str="bodyweight", description="",
        )
        assert meta["muscles_raw"] == ""
        assert meta["muscles_secondary_raw"] == ""
        assert meta["equipment_raw"] == "bodyweight"

    def test_legacy_fields_also_preserved(self):
        # Additive rule: legacy field names carry the same string. This is what
        # keeps read-only consumers (main.py, exercise_retriever) working.
        meta = build_exercise_metadata(
            name="X", category="Chest", muscles_str="biceps",
            muscles_secondary_str="glutes", equipment_str="dumbbell", description="",
        )
        assert meta["equipment"] == "dumbbell"
        assert meta["muscles"] == "biceps"
        assert meta["muscles_secondary"] == "glutes"

    def test_description_truncated_to_400_chars(self):
        # Ingest convention: description field on metadata is capped so the
        # per-row payload stays small; full text still lives in the document body.
        long_desc = "x" * 500
        meta = build_exercise_metadata(
            name="Test", category="Chest", muscles_str="",
            muscles_secondary_str="", equipment_str="bodyweight",
            description=long_desc,
        )
        assert len(meta["description"]) == 400
        assert meta["description"] == "x" * 400

    def test_description_shorter_than_cap_preserved(self):
        meta = build_exercise_metadata(
            name="Test", category="Chest", muscles_str="",
            muscles_secondary_str="", equipment_str="bodyweight",
            description="short",
        )
        assert meta["description"] == "short"


class TestT6_CategoryLowercased:
    """Spec T6: category is lowercased at build time; Cardio/cardio dedup is gone."""

    @pytest.mark.parametrize("raw,expected", [
        ("Cardio", "cardio"),
        ("cardio", "cardio"),
        ("Chest", "chest"),
        ("Legs", "legs"),
        ("olympic weightlifting", "olympic weightlifting"),
        ("Abs", "abs"),  # spec §D3 does NOT dedup the category-side "Abs" tag; that's a taxonomy split, deferred.
    ])
    def test_category_lowercased(self, raw, expected):
        meta = build_exercise_metadata(
            name="X", category=raw, muscles_str="", muscles_secondary_str="",
            equipment_str="bodyweight", description="",
        )
        assert meta["category"] == expected
