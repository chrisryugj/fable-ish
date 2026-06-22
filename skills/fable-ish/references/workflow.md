# fable-ish Workflow

## Mode Selection

- `quick`: simple explanation, direction check, low-risk review, or user asks for speed.
- `normal`: bounded code/docs/config changes, focused debugging, or ordinary implementation.
- `deep`: production, auth, database, migrations, deployment, broad refactor, generated artifacts, or high reliability work.
- `blocked`: destructive scope, secret exposure, irreversible remote action, missing credentials, or user decision required.

## Domain Steering

Use the user's domain expertise as the main steering signal. Preserve domain meaning instead of replacing it with generic coding assumptions.

When the user gives rules, edge cases, constraints, or correction criteria, use them to choose the work unit, likely failure scenarios, and exit proof.

## Work Kind Selection

First classify depth: quick, normal, deep, or blocked. Then classify work kind:

- `build`: create or extend behavior.
- `fix`: reproduce, diagnose, patch, and prove the failure no longer reproduces.
- `test`: choose the smallest proof that covers the risk.
- `operate`: verify process, endpoint, job, deployment, or runtime state.
- `understand`: inspect and explain the existing system without inventing behavior.
- `plan`: produce risk-ordered phases and proof boundaries.
- `analyze`: preserve data provenance, calculations, and reproducibility.
- `document`: verify facts, commands, links, and user-facing procedure.

Use depth to choose rigor. Use work kind to choose proof.

## Work Loop

For normal and deep tasks:

1. Inspect the relevant local context before editing.
2. Name the work unit as behavior, invariant, or artifact contract.
3. Choose an observable exit proof.
4. Implement the smallest coherent slice.
5. Run the narrowest relevant verification first.
6. Review likely failure scenarios.
7. Fix confirmed issues.
8. Stop only when proof passes or a concrete blocker remains.

## Review Lenses

Use these only when risk warrants:

- Changed invariant and caller/callee contract.
- Removed guards, defaults, or fallbacks.
- Empty, missing, zero, false, malformed, and legacy state.
- Concurrency, ordering, persistence, platform, and deployment differences.
- Security boundaries around auth, secrets, money, DB, and remote writes.

## Optional Subagents

Subagents are optional. Use them only for broad search, independent review, or separate modules where recall matters. Do not spawn them for small local edits.
