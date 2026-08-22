---
name: auto-clip-studio
description: Build and maintain the AutoClip Studio video clipping project with its required module-by-module testing and review gates.
metadata:
  short-description: AutoClip Studio development workflow
---

# AutoClip Studio Development

Use this skill for any work inside `auto-clip-studio/`. Do not use it for unrelated video tools.

## Required workflow

1. Read `docs/architecture.md`, `docs/api-contract.md`, and `docs/progress.md`.
2. Read `references/workflow.md` before choosing the next module.
3. Read `references/review-checklist.md` after completing each API or module.
4. Read `references/api-contract.md` from the skill only when the contract needs interpretation or change.
5. Follow `docs/ai-project-process.md` for general engineering standards.

## Hard constraints

- Never skip the test + review + document-sync gate after completing an API or module.
- Keep uploads, renders, transcripts, model caches, and SQLite data under `.local/`.
- Never commit API keys, user videos, rendered media, or model response caches.
- Do not add a major dependency unless `docs/architecture.md` records the reason.
- Validate all AI provider output with Pydantic before persistence.
- Keep state transitions inside the state-machine module; API handlers must not assign states directly.
- Keep frontend and backend API changes synchronized with `docs/api-contract.md`.
