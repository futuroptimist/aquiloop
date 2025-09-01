---
title: 'Codex Feature Prompt'
slug: 'prompts-codex-feature'
---

# Codex Feature Prompt

Use this prompt when adding a small feature to aquiloop.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Implement a minimal feature in aquiloop.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Write a failing test that captures the new behavior.
2. Implement the feature with minimal changes.
3. Update relevant docs or prompts.
4. Run the commands above to ensure success.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the feature addition.
```

Copy this block whenever implementing a feature in aquiloop.
