---
name: cross-skill-ref
description: "Fixture: mentions a sibling skill's scripts/ path, a URL with a scripts/ segment and a ../ path; only the ./-prefixed and plain local paths are this skill's references."
---

# cross-skill-ref

Validate the card with `skills/other-skill/scripts/validate_card.py` (it lives in
a sibling skill, not in this one). The upstream copy is
https://example.com/org/repo/blob/main/scripts/tool.py and the parent tree keeps
../scripts/parent.sh; neither is a file of this skill.

Then run ./scripts/own.sh and read `references/guide.md`.
