# Weekly Planner CLI Acceptance

- command: `creativeos campaign week plan <campaign-id> --week-start YYYY-MM-DD`
- deterministic seven-day ordered output
- existing weeks load without mutation
- replacement requires `--replace`
- corrupt or unsupported snapshots fail closed
- no provider execution or publishing side effects
- all items remain `planned`
