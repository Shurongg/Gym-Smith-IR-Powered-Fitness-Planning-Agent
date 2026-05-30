from pipeline.context_assembler import assemble_prompt, SYSTEM_PROMPT

SAMPLE_INTENT = {
    "target_muscles": ["biceps"],
    "equipment": ["dumbbell"],
    "frequency": 3,
    "intensity": "medium",
    "goal": "hypertrophy",
    "flags": [],
}
SAMPLE_EXERCISES = [
    {"name": "Bicep Curl", "muscles": "Biceps brachii", "equipment": "Dumbbell",
     "description": "Stand with dumbbells, curl up.", "category": "Arms"},
]
SAMPLE_RULES = [
    {"title": "Progressive Overload", "content": "Increase weight over time.", "type": "training_principle"},
]
SAMPLE_MEMORY = {"equipment": ["dumbbell"], "intensity_preference": "medium", "last_goal": "hypertrophy"}

def test_assemble_includes_exercises():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "Bicep Curl" in prompt

def test_assemble_includes_rules():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "Progressive Overload" in prompt

def test_assemble_includes_user_memory():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, SAMPLE_MEMORY)
    assert "dumbbell" in prompt.lower()

def test_assemble_no_memory():
    prompt = assemble_prompt("I want arm gains", SAMPLE_INTENT, SAMPLE_EXERCISES, SAMPLE_RULES, None)
    assert isinstance(prompt, str)
    assert len(prompt) > 100

def test_system_prompt_contains_restrictions():
    assert "medical" in SYSTEM_PROMPT.lower()
    assert "supplement" in SYSTEM_PROMPT.lower()
