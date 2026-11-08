
## When to use which skill
Each skill holds its own steps; this policy only says when.
- Any S or C task: start with task-router. Tasks that wait for approval: task-approval.
- Session start or resumed work in a folder with .kit/work/: session-recovery.
- Unfamiliar code: codebase-explorer. Design choices: design-review. Algorithms with stated limits: algorithm-options.
- Writing code: test-driven-development (principle 4). Bugs or failing tests: systematic-debugging.
- Before calling it done: counterexample-hunter (principle 7), verification-before-completion (principle 5), implementation-review.
- Speed: benchmark to measure, algorithm-optimizer to improve.
- Datasets (before training, evaluating or reporting on them): data-quality-validator.
- Reviews: requesting-code-review before asking, receiving-code-review when feedback arrives.
- Keep changes small and simple: karpathy-guidelines.
