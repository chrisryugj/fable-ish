# fable-ish Verification

## Verification Ladder

Pick the lowest proof that actually covers the risk:

1. Static file/schema/manifest validation.
2. Focused unit or integration test.
3. Typecheck, lint, or build.
4. Runtime smoke check, curl, browser, or health endpoint.
5. Artifact rendering or consumer check.
6. CI, deployment, or production/internal URL check when that is the real boundary.

## Baseline Failures

If the baseline was already red, do not hide it.

- Record the failing command.
- Identify whether the new work changed the failure.
- Use `delta-zero` only when the failure is unrelated and unchanged.
- If you cannot distinguish baseline from new failure, report it as uncertain.

## Missing Harness

If no test exists:

- Create a tiny targeted verifier when safe and in scope.
- Otherwise run the closest observable proof.
- State the verification gap in the final response.

## Stop Criteria

Stop when:

- The selected proof passed.
- A failure is fixed and the original proof no longer reproduces.
- Remaining progress needs credentials, user choice, future data, or external state.
- Verification would be disproportionate and that gap is explicitly reported.
