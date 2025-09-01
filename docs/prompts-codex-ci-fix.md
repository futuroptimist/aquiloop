---
title: 'Codex CI-Failure Fix Prompt'
slug: 'prompts-codex-ci-fix'
---

# Codex CI-Failure Fix Prompt

Use this prompt when CI fails and you want an automated agent to fix the issue.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Diagnose and resolve the failing check.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Reproduce the failure locally.
2. Apply a minimal fix.
3. Add a regression test when practical.
4. Run the commands above to confirm the fix.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the CI fix.
```

Copy this block whenever addressing CI failures in aquiloop.
