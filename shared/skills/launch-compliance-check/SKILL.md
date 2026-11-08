---
name: launch-compliance-check
description: "Use before launching a web service or app ('출시 전 점검', 'launch checklist') - walks 20 items (privacy, terms, refunds, cookies, consent, SDKs, dark patterns, fees, reviews, claims, accessibility, business info, children, unsubscribe, licenses, deletion) and reports method, evidence and verdict for each. Do NOT use as legal advice or for code review."
---

# Launch compliance check

**This is not legal advice.** It is a checklist that collects evidence and points at the rules
a person must confirm. Never write that the service "complies with" or "violates" a law; write
what the evidence shows and mark the legal judgment NEEDS_HUMAN.

## Steps

1. **Scope.** Write down what is being launched (site, app, API), where the users are (Korea by
   default; EU or US users add rules this list does not cover: mark those NEEDS_HUMAN), and
   what it does: accounts, payments, email, ads, children, uploads.
2. **Collect, change nothing.** Read the pages, forms, code and config the user points at. For
   each of the 20 items in [references/checklist.md](references/checklist.md) follow its
   "how to check" and keep the evidence: file:line, URL and quoted text, a screenshot path, or
   a command and its output.
3. **Verdict per item**, one of four:
   - `PASS`: the evidence shows the item is met. No evidence, no PASS.
   - `FAIL`: the evidence shows it is not met (say what is missing).
   - `N/A`: the feature does not exist (say which: "no email is sent", "no payments").
   - `NEEDS_HUMAN`: code and screens cannot settle it (contracts, licenses bought, legal
     judgment, a page you could not open). Say what the person must check.
4. **Rules.** When an item names a law or standard, copy the citation and its level from
   [references/sources.md](references/sources.md): `VERIFIED-DOC` only for text read at an
   official source on the date given; everything else stays `UNVERIFIED`. Never upgrade a
   level from memory.
5. **Report** with the table below, then list the FAILs first with the smallest fix for each,
   then the NEEDS_HUMAN questions. Fix nothing unless the user asks.

## Report

```markdown
## Launch compliance check: <service> (<date>)

This is not legal advice. Scope: <what, users where, features>.

| # | Item | How checked | Evidence | Verdict | Rule (level) |
|---|---|---|---|---|---|
| 1 | Privacy policy | ... | `site/privacy.html:12` "..." | PASS | PIPA art. 30 (UNVERIFIED) |

Totals: PASS n / FAIL n / N/A n / NEEDS_HUMAN n

### FAIL: smallest fix
### NEEDS_HUMAN: questions for a person
```

All 20 rows appear, in the checklist's order, even when the verdict is N/A.
