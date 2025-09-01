---
title: 'Codex Test Prompt'
slug: 'prompts-codex-tests'
---

# Codex Test Prompt

Use this prompt to add or improve tests in aquiloop.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Increase test coverage and reliability.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Identify untested behavior or missing edge cases.
2. Write tests that fail before code changes.
3. Update code as needed to make tests pass.
4. Run the commands above to confirm success.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the test improvements.
```

Copy this block whenever working on tests for aquiloop.
