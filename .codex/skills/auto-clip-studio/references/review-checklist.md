# Review Checklist

Complete this checklist after every API or module:

- The implementation satisfies the current module's acceptance criteria.
- Input validation covers types, sizes, ranges, file types, and state.
- Missing resources return stable 404/409 behavior.
- Invalid or external-failure paths leave recoverable state and useful errors.
- State changes go through the state machine and do not expose partial writes.
- Focused tests cover success and at least one failure scenario.
- AI output is schema-validated and bounded before persistence.
- No secret, user media, cache, or runtime artifact is committed or logged.
- No unrelated refactor or undeclared major dependency was introduced.
- `docs/api-contract.md`, architecture notes, and progress log match behavior.
