---
name: design-doc
description: Produce a design, planning, analysis, or architecture-decision document through a structured interview. Dispatches researcher subagents for codebase facts first, then interviews the user on every open fork with pros/cons and a recommendation, then writes a decision document to {docs-dir}/todo/ and stops. Use for "design doc", "planning doc", "analysis doc", "design proposal", "architecture decision", or when asked to think a change through before building it.
---

# Design Doc

Produce a decision document: the problem, the forks that were settled, why each
went the way it did, and what remains open. The output is readable months later
and is directly ingestible by `/forge <path>` (doc-first mode), which re-verifies
paths and restructures it into an implementation plan.

**This skill never implements.** It ends when the document is written.

The output is a *decision record*, not a coder spec. No Reachability table, no
ordered implementation steps — the forge planner derives those. Your job is to
make sure nothing load-bearing is left ambiguous.

---

## Step 1 — Investigate before asking

Facts come from the codebase, not from the user. Only surface a question once
you have confirmed the codebase does not already answer it.

Count the **independently investigable unknowns** — ones answerable by searching
different parts of the codebase without depending on each other.

- **2 or more:** name the axes explicitly ("axis 1: how X is written; axis 2: how
  X is read"), then dispatch one `researcher` subagent per axis in a single
  parallel Task batch.
- **1:** dispatch a single researcher.

Dispatch shape — one specific, answerable question plus file hints:

> "Find where [X] is handled. Summarize the flow, relevant file paths, and any
> invariants."

**Wait for every researcher to return before drafting.** Synthesize their output
into the document's own prose — never paste raw researcher output. Never infer a
reader or call site from a filename or module name; if it is not in a researcher
response, it does not go in the document.

## Step 2 — Interview

Invoke `skill: interview-me` and follow it: map question dependencies, ask
branching decisions first, batch independent questions in parallel, and give a
recommended answer with one line of *why* for each.

Two rules carry over from the planner and override any urge to move faster:

- **Investigation resolves facts, not choices.** Never decide a branch on the
  user's behalf because the code contains a reasonable default.
- **Never leave a real fork unmade.** Present the options and get a choice.
  Silently picking a default is as much a failure as not noticing the fork.

When a fork has real trade-offs — complexity, performance, a new dependency,
scope — put it to the user in this shape:

```
### Option A: {short name}
**approach:** <1 sentence>
**pros:** <bullets>
**cons:** <bullets>

### Option B: {short name}
<same shape>

**Recommendation:** Option [A|B] — <one sentence why>.
```

Scale the interview to the scope: a narrow topic may settle in two questions, a
broad one may take several batches. Depth is set by ambiguity, not by a quota.

## Step 3 — Write the document

Write to `{docs-dir}/todo/{slug}-design.md`. Date goes in the frontmatter, not the
filename. (Use `{slug}-analysis.md` when the document diagnoses an existing
system rather than proposing a change.)

### Frontmatter and core sections — always present

```markdown
---
status: design | needs-decision | accepted
date: YYYY-MM-DD
tags: [design, <area>]
---
```

Write one of the three statuses above. `final` is the fourth value in the enum, but it is not
yours to set — the forge `docs-writer` sets it once a run has delivered every item the
document asks for, and may then move the document to `{docs-dir}/archive`.

```markdown
# <Topic> — Design

## 1. Context
<The problem. What prompted it now. What breaks or stays awkward if nothing
changes.>

## 2. Decisions
<One subsection per settled fork. Each carries three things:
**approach** — what was chosen, concretely;
**rationale** — why, in terms of the trade-off that decided it;
**rejected** — the alternatives and the specific reason each lost.
A decision without a rejected alternative was not a fork; fold it into Context.>

## 3. Affected files
<Path + what changes there. Every path traceable to a researcher response.
Write `none — analysis only` if the document proposes no change.>

## 4. Open questions
<[BLOCKING] = cannot proceed without an answer (unmade decision, unconfirmed
value). [VERIFY] = confirm during implementation and flag what you find.
Write `none` if there are none — never omit the section.>
```

### Optional sections — add only when warranted

Add a section only when the topic earns it. An empty "Non-goals: none" is
filler and makes the document less likely to be read.

| Section | Add when |
|---|---|
| `## Goals` / `## Non-goals` | scope is contested or the boundary is the point |
| `## Options` | a fork is still **open** — use the pros/cons block from Step 2 |
| `## Failure modes` | runtime behavior changes and can fail in new ways |
| `## Risks` | doing this could cause a *new* problem while solving the old one |
| `## Consequences` | this reaches into work outside its own scope, for better or worse |
| `## Evaluation plan` | a metric, benchmark, or eval decides whether this worked |
| `## Related docs` | cross-references exist — link them as `{docs-dir}/...` paths |

Order them as listed above when several apply.

`Failure modes`, `Risks` and `Consequences` are three different questions and
collapse into mush if you let them:

- **Failure modes** — how the built thing breaks *at runtime*. Present tense,
  about the system.
- **Risks** — what this change could make worse, and what you do about it.
  Each row needs a mitigation, or an explicit note that the risk is accepted
  and why. A risk with neither is an anxiety, not a design artifact.
- **Consequences** — what this change *implies* elsewhere, positive or
  negative. Not things to fix now; things a later plan needs to know. Mark the
  direction so the section stays honest about the wins too.

```markdown
## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| <what could go wrong> | low/med/high | <what you do, or `accepted — <why>`> |

## Consequences

- **(+)** <what this unlocks, simplifies, or makes cheaper later>
- **(−)** <what this constrains, couples, or makes harder later>
- **(?)** <a connection worth tracking whose sign is not yet clear>
```

### Banned outside `## Open questions`

- "need to check", "should verify", "confirm whether", "TBD"
- future-tense references to research ("researcher to confirm", "we should
  investigate") — by the time you write, research is done
- conditionals over unknown facts: "if X exists", "assuming Y is", "depending
  on whether"

A conditional is legal only for a *runtime* branch in the system being
described, never for your own uncertainty about the codebase. Dispatch a
researcher and write the answer instead. If the researcher cannot answer it, it
is `[BLOCKING]` in Open questions.

### Self-check before you finish

Re-read the document against this list and fix any failure:

- every decision in §2 has approach, rationale, **and** rejected alternatives
- every file path is traceable to a researcher response, not inferred
- §3 is non-empty, or explicitly reads `none — analysis only`
- §4 is present, even if it reads `none`
- every optional section included is warranted; none is filler
- if `## Risks` is present, every row has a mitigation or an explicit `accepted — <why>`
- no banned string appears outside §4
- every fork raised in the interview is either settled in §2 or listed in §4

Coverage is the target, not length.

## Step 4 — Stop

**Do not begin implementation.** Do not write or edit source files, configs, or
tests. Await explicit approval.

Print the document path and the chaining command, as a suggestion only — do not
run it:

```
Written: {docs-dir}/todo/<slug>-design.md
Next (when ready): /forge {docs-dir}/todo/<slug>-design.md
```
