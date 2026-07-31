---
name: interview-me
description: Interview the user relentlessly about a plan or design until shared understanding is reached. Investigates files/code/docs/issues/logs to resolve facts before asking, maps question dependencies, batches independent questions in parallel while asking branching decisions first, and gives a recommended answer for each. Use when user wants to stress-test, refine or deepen a plan, get grilled/interviewed on their design, or mentions "interview".
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions until nothing load-bearing is left ambiguous.

## Investigate before asking

If an answer can be found by reading files, code, docs, issues, or logs, inspect those **first** instead of asking. Only surface a question once you've confirmed the codebase doesn't already answer it.

The **decisions** are mine, though. Never decide a branch on my behalf because you found "a reasonable default" in the code — investigation resolves *facts*, not *choices*. Put every open decision to me and wait for my answer before proceeding down its branch.

## Map the questions before firing them

Once questions arise, don't just dump them in arrival order. First work out how they relate:

- **Dependency** — does answering B require knowing the answer to A? (A branches the tree; B only exists on one branch.)
- **Similarity** — do several questions circle the same concern? Group them so I reason about the concern once.

## Batch intelligently

Use that map to control the order and grouping:

1. **Deciding/branching questions go first, alone or in a tight group.** If a question's answer determines whether other questions even apply — or changes what they'd be — ask it before the questions that hang off it. Don't waste my time on questions that a branching answer might delete.
2. **Independent questions go in parallel.** Any set of questions that don't depend on each other can be asked together in one batch. Group the ones sharing a concern.
3. **Then descend.** After I answer a branching question, ask the next batch that its answer unlocked. Repeat until the tree is resolved.

Keep batches focused — a batch is a set of genuinely independent decisions, not an everything-dump.

## Every question gets a recommended answer

For each question, state **your recommended answer** and one line of why. Make it a real recommendation I can accept or override, not a menu of equal options. When there's a meaningful trade-off, name it.
