---
title: 'Codex Spellcheck Prompt'
slug: 'prompts-codex-spellcheck'
---

# Codex Spellcheck Prompt

Use this prompt to improve spelling in aquiloop.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Fix spelling mistakes or add missing dictionary entries.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Scan files for spelling errors or inconsistent terminology.
2. Update text or dictionaries accordingly.
3. Run the commands above to ensure checks pass.
4. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the spelling improvements.
```

Copy this block whenever running spellcheck tasks in aquiloop.
