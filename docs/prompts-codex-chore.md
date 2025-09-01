---
title: 'Codex Chore Prompt'
slug: 'prompts-codex-chore'
---

# Codex Chore Prompt

Use this prompt for dependency bumps, CI tweaks, or other housekeeping in aquiloop.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Perform maintenance tasks that keep the project healthy.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Identify a small chore such as updating dependencies or configs.
2. Make the change with minimal code adjustments.
3. Update docs if the chore impacts usage.
4. Run the commands above to ensure the project stays green.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the maintenance work.
```

Copy this block whenever performing chores in aquiloop.
