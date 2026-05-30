# Equipment Rules

## Equipment priority
When user provides available equipment, only recommend exercises that match available equipment.

## If equipment is unknown
Ask one short clarification question:
"What equipment do you have access to: gym machines, dumbbells, cables, bands, or bodyweight only?"

If no clarification is possible, generate a bodyweight + dumbbell fallback plan.

## Dumbbell rules
If user has dumbbells:
- chest: dumbbell press, dumbbell floor press, dumbbell fly
- arms: dumbbell curl, hammer curl, overhead triceps extension
- shoulders: dumbbell shoulder press, lateral raise
- legs: goblet squat, dumbbell Romanian deadlift, split squat

## Cable rules
If user has cables:
- chest: cable fly, cable chest press
- biceps: cable curl
- triceps: rope pushdown, overhead cable extension
- shoulders: face pull, cable lateral raise

## Bodyweight rules
If user has no equipment:
- chest: push-up variations
- triceps: close-grip push-up, bench/chair dip only if safe setup
- core: plank, dead bug, hollow hold, mountain climber
- legs: squat, lunge, glute bridge

## Machine rules
If user has gym machines:
- chest: chest press machine, pec deck
- back: lat pulldown, seated row
- legs: leg press, leg curl, leg extension
- arms: preacher curl machine, assisted dip machine

## Substitution rule
If an exercise requires unavailable equipment:
1. Identify movement pattern.
2. Keep target muscle similar.
3. Replace equipment.
4. Keep difficulty similar or slightly easier.

Example:
- barbell bench press unavailable
- alternatives:
  - dumbbell bench press
  - dumbbell floor press
  - machine chest press
  - push-up
  - cable chest press
