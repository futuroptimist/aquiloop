---
title: 'Codex Docs Update Prompt'
slug: 'prompts-codex-docs'
---

# Codex Docs Update Prompt

Use this prompt to enhance or fix aquiloop documentation.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Improve documentation accuracy, links, or readability.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Identify outdated, unclear, or missing docs.
2. Apply minimal edits while keeping style consistent.
3. Update cross references or links as needed.
4. Run the commands above to confirm tests and lint pass.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing documentation improvements.
```

Copy this block whenever updating docs in aquiloop.
