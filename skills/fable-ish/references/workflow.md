# fable-ish Workflow

## Mode Selection

- `quick`: simple explanation, direction check, low-risk review, or user asks for speed.
- `normal`: bounded code/docs/config changes, focused debugging, or ordinary implementation.
- `deep`: production, auth, database, migrations, deployment, broad refactor, generated artifacts, or high reliability work.
- `blocked`: destructive scope, secret exposure, irreversible remote action, missing credentials, or user decision required.

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
