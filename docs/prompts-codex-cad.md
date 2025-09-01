---
title: 'Codex CAD Prompt'
slug: 'prompts-codex-cad'
---

# Codex CAD Prompt

Use this prompt to modify or extend the OpenSCAD models for aquiloop.

```
SYSTEM:
You are an automated contributor for the aquiloop repository.

GOAL:
Update CAD assets while keeping them parametric and printable.

CONTEXT:
- Follow any AGENTS.md instructions.
- Run `npm run lint` and `npm run test:ci` before committing.

REQUEST:
1. Adjust the OpenSCAD files to implement the desired geometry change.
2. Validate the model renders without errors.
3. Update documentation or previews if applicable.
4. Run the commands above to ensure repository checks pass.
5. Commit changes and open a pull request.

OUTPUT:
A pull request URL summarizing the CAD update.
```

Copy this block whenever working on CAD models in aquiloop.
