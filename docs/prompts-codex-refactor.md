---
title: 'Codex Refactor Prompt'
slug: 'prompts-codex-refactor'
---

# Codex Refactor Prompt

Use this prompt to restructure code in aquiloop without altering behavior.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Improve code clarity while keeping functionality intact.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Identify code that can be simplified or clarified.
2. Refactor while preserving existing behavior and tests.
3. Adjust or add tests if necessary.
4. Run the commands above to ensure no regressions.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the refactor.
```

Copy this block whenever refactoring aquiloop.
