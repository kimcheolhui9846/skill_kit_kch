---
name: web-design-guidelines
description: "Use when asked to review UI code for accessibility, focus, forms, animation, typography, performance or dark mode ('UI 리뷰', 'review my UI', 'audit design') - checks the given files against a pinned copy of Vercel's Web Interface Guidelines and reports file:line findings. Do NOT use for backend code, visual design direction (use frontend-design) or when no UI files are given."
---

# Web Design Guidelines

Review UI files against the rules in [references/command.md](references/command.md), a pinned
copy of Vercel's Web Interface Guidelines (MIT, [references/LICENSE](references/LICENSE)).
Do not fetch a newer version from the web; the kit updates the copy (`kit source update`).

## Steps

1. Take the files or glob the user gave. If none, ask which files to review.
2. Read `references/command.md` once. Its "Rules" section is the checklist; its
   "Output Format" section is the report format.
3. Read each file and check it against every rule that applies to its kind of code.
4. Report findings grouped by file, one line each: `path:line - rule - fix`.
   Say "no findings" for a file that passes.

## Rules

- Report only what the code shows. Mark guesses (e.g. behaviour that depends on CSS you did not
  read) as "check manually".
- Do not edit files unless the user asks for fixes.
