# Hypertrophy and Muscle Definition Rules

## Goal mapping
If the user says:
- muscle definition
- toned arms
- visible lines
- build muscle
- bigger chest
- stronger-looking arms

Map the goal to:
- hypertrophy-oriented resistance training
- progressive overload
- basic nutrition support
- recovery consistency

## No guarantee rule
Do not promise visible muscle definition within a fixed time.
Use cautious wording:
- "This can support your goal."
- "Visible changes depend on training history, body composition, diet, sleep, and consistency."

## Weekly set target
For a target muscle group:
- Beginner default: 6–8 hard sets per target muscle per week.
- General hypertrophy default: about 8–12 hard sets per target muscle per week.
- Do not exceed 15 sets per target muscle per week in the MVP unless the user is clearly experienced.

## Exercise count
For each target muscle:
- Use 2–4 exercises per week.
- Mix compound and isolation exercises when appropriate.

## Repetition range
Default hypertrophy range:
- 8–12 reps for main accessory movements.
- 10–15 reps for smaller isolation movements.
- 12–20 reps may be used for low-load bodyweight or band movements.

## Effort rule
Use moderate-to-hard effort.
Default:
- Stop with about 1–3 reps in reserve.
- Do not require failure on every set.

## Rest rule
Default rest:
- 1–2 minutes for isolation/accessory exercises.
- 2–3 minutes for heavier compound exercises.

## Example output constraint
For each exercise, include:
- target muscle
- equipment
- sets
- reps
- rest
- short reason

## YAML rule cards

```yaml
id: hypertrophy_default_volume
topic: hypertrophy
applies_when:
  - user_goal includes "muscle growth"
  - user_goal includes "definition"
  - user_goal includes "tone"
rule:
  beginner_default_sets_per_target_muscle_per_week: "6-8"
  general_default_sets_per_target_muscle_per_week: "8-12"
  max_mvp_sets_per_target_muscle_per_week: "15"
output_instruction:
  - "Do not promise visible results."
  - "Use progressive overload."
  - "Include rest days."
source_basis:
  - "ACSM resistance training guidelines"
  - "hypertrophy volume literature"
---
id: user_asks_two_month_definition
topic: expectation_management
applies_when:
  - user_goal includes "2 months"
  - user_goal includes "visible definition"
rule:
  response:
    - "Explain that 8 weeks can support progress but cannot guarantee visible definition."
    - "Generate an 8-week structure."
    - "Include training consistency, nutrition basics, and recovery."
    - "Avoid body-fat promises."
```
