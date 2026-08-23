# Production Quality Gate

This checklist is mandatory before coding, during review, and before release. Apply every relevant item to AutoClip Studio backend, frontend, providers, database, media pipeline, and deployment configuration.

## 1. Business Logic

1. Cover every branch. Do not leave an unhandled `else`, omitted condition, or silent no-op path that can create dirty data.
2. Validate all input: required fields, length, range, format, file type, and size. Never trust external input directly.
3. Enforce state transitions through the project state machine. Validate current state before mutation.
4. Extract business constants and rules instead of hard-coding values in handlers.
5. Reuse common functions instead of duplicating the same business logic.
6. Return stable contract objects. Do not arbitrarily return `null`, `undefined`, or mixed shapes.
7. Make repeat requests idempotent. Repeated analysis, render, callback, or payment-like operations must not create duplicate persisted data.
8. Preserve atomicity where a business operation must complete as one unit; never persist a partial result silently.

## 2. Exception Handling

1. Wrap database, cache, HTTP, RPC, OSS, ASR, LLM, and filesystem operations with explicit error handling.
2. Never swallow exceptions. At minimum, log a bounded, useful message.
3. Separate business validation failures from system/provider failures.
4. Do not expose raw stacks, SQL errors, provider payloads, or internal paths to API callers.
5. Set explicit connection and read timeouts for every external request. No request may wait forever.
6. Add bounded retries with exponential backoff and jitter where safe. Avoid retry storms.
7. Do not collapse empty string, `null`, `0`, `false`, missing field, and empty collection into one meaning.
8. Do not use exceptions as ordinary control flow.

## 3. Security

1. Use parameterized database statements. Never concatenate SQL.
2. Escape or safely render user-generated text in the frontend. Never inject model or user text into executable contexts.
3. Authorize every API on the backend. Frontend hiding is not authorization.
4. Never log or persist secrets, tokens, keys, phone numbers, or identity documents in plaintext.
5. Prevent command injection and path traversal. Validate uploads and never derive a storage path directly from a client filename.
6. Protect important operations against replay with token/signature or equivalent validation.
7. Keep all credentials in environment variables or a dedicated secret manager. Never hard-code them.

## 4. Database

1. Evaluate indexes for every query on growing tables. Avoid full scans of large tables.
2. Keep transactions short. Do not hold a transaction across HTTP, LLM, ASR, OSS, or FFmpeg work.
3. Avoid long transactions that can lock tables or produce large rollback work.
4. Every `UPDATE` and `DELETE` must have an intentional `WHERE` clause.
5. Process large datasets in bounded batches or cursor pages, never one unbounded load.
6. Make `NULL` semantics explicit; prefer explicit values where business meaning matters.
7. Keep update ordering consistent to reduce deadlocks.
8. Assign business values explicitly rather than relying on accidental database defaults.
9. Avoid huge-offset pagination. Use a stable cursor, such as an indexed id/time pair.
10. For read replicas, account for replication lag and force the primary for read-after-write when required.

## 5. Cache

1. Set an expiry for every cache entry.
2. Handle cache penetration, breakdown, and stampede patterns.
3. Define update order and invalidation rules that prevent stale or inconsistent values.
4. Catch cache failures and degrade gracefully; cache unavailability must not break the core flow.
5. Avoid large keys and unbounded values.

## 6. HTTP and RPC Interfaces

1. Every outbound call must set connection and read timeouts.
2. Validate and shape-check response payloads before indexing or attribute access.
3. Preserve API compatibility. Field removal or type changes require a contract update and migration plan.
4. Add failure/degradation behavior for each external dependency.
5. Do not call HTTP/RPC services repeatedly inside loops when a batch API can be used.

## 7. Concurrency and Async Tasks

1. Protect shared mutable state with locks, queues, or immutable design.
2. Async and background task errors must be recorded and surfaced in project state.
3. Bound all worker/thread/coroutine pools. Never spawn unbounded concurrency.
4. Do not rely on a parent request transaction inside an async task.
5. Make queue/message consumption idempotent and route persistent failures to a dead-letter or failed state.
6. Do not create threads/coroutines in hot loops without a bounded pool.

## 8. Resource Cleanup

1. Close files, clients, sockets, and database sessions with `with`, `finally`, or equivalent lifecycle management.
2. Do not let static/global collections grow without eviction.
3. Release large media objects promptly.
4. Stop timers and background workers during shutdown.
5. Clean temporary local and OSS files even when provider processing fails.

## 9. Logging and Alerts

1. Log key lifecycle events, state changes, external-call outcomes, and exceptions with project/segment ids.
2. Never log credentials, signed URLs, tokens, captions containing private data, or complete raw provider payloads.
3. Use levels correctly: normal flow as info, genuine failures as error.
4. Preserve enough exception context to diagnose production issues without exposing internals to callers.
5. Trigger alerts for persistent provider failure, render failure, storage failure, and stuck jobs.
6. Bound logged payload size; do not log full transcripts or media objects.

## 10. Configuration and Environments

1. Separate development, test, and production configuration. Do not hard-code environment-specific addresses.
2. Disable debug modes, test routes, and temporary switches before release.
3. Remove test accounts and test-only behavior before production.
4. Validate required environment variables at startup or provider initialization; fail clearly and early.

## 11. Coding Standards

1. Use meaningful names.
2. Replace magic numbers and strings with named constants.
3. Never compare floating-point values for exact equality.
4. Check collection length before indexed access.
5. Do not mutate a collection while iterating it.
6. Explain complex logic with concise comments; delete obsolete code instead of commenting it out.
7. Extract repeated logic into shared functions.
8. Avoid deep nesting; early-return or split helper functions.
9. Be explicit about types and avoid implicit string/number coercion.

## 12. Boundary Tests

Every module must consider:

- Empty string, missing field, `null`, zero, negative, maximum, and oversized values.
- Empty collection, one item, many items.
- Time boundaries: midnight, month/year rollover, timezone, and duration rounding.
- Concurrent operations on the same project/segment.
- Provider timeout, empty response, malformed response, and HTTP error.
- Network interruption and partial upload/render failure.

## 13. Release Verification

1. Remove debug prints, sleeps, temporary scripts, and test-only logic.
2. Cover core paths and exception paths with tests.
3. Review exceptions, transactions, loops, authorization, and input validation explicitly.
4. Confirm a fast rollback path.
5. Prefer staged/gray release over immediate full rollout.
6. Verify database migrations are reversible or otherwise protected, and estimate execution time.

## Gate Definition

A change cannot be committed if it introduces an unresolved P0/P1 violation of this document. If a rule cannot be applied yet, record the limitation and mitigation in `docs/progress.md` and the relevant design document.
