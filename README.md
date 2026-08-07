# Forge 

**Structured, multi-agent development pipeline**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

A drop-in set of Claude Code / CoPilot agent definitions and a slash command that turn a task description
into reviewed, tested code — with human approval gates at each major stage.
Language and framework agnostic. Configurable for any project via four placeholders.
(Applicable for any other agentic tool with the correct placing of agents skill and command.)

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/pipeline-dark.svg">
    <img src="assets/pipeline-light.svg" width="100%"
         alt="Forge pipeline: an optional design-doc feeds /forge, then planner, an approval gate, coder, qa-reviewer, a second approval gate, test-writer and docs-writer, ending at done. Each stage lights up in turn and darkens once it has passed.">
  </picture>
</p>

<details>
<summary>Text version</summary>

```
  [design-doc]  ←── optional, interview-driven
       │
       ▼
idea, or design/plan doc in {docs-dir}/todo/
       │
   [planner]  ←── interview-me Skill
       │
  approval gate ──► you
       │
    [coder]
       │
  [qa-reviewer]
       │
  approval gate ──► you
       │
  [test-writer]
       │
  [docs writer]
       │
     done
```

</details>

Escalation paths run in both directions — the coder can send ambiguous requirements back to
the planner; the qa-reviewer can send bugs back to the coder; the test-writer can surface
source bugs before they reach you; the docs-writer asks rather than guessing at a living
document it is not sure about.

---

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)  / CoPilot (any recent version)
- A project with a `CLAUDE.md` at its root

---

## Installation

### Claude
1. Copy the `agents/`, `commands/`, and `bootstrap.md` into your project's `.claude/` directory:

   ```
   .claude/
     agents/
       coder.md
       dispatcher.md
       docs-writer.md
       planner.md
       qa-reviewer.md
       researcher.md
       test-writer.md
     commands/
      forge.md
     skills/
      interview-me/
       SKILL.md
      design-doc/
       SKILL.md
      curate-learnings/
       SKILL.md
       references/
       scripts/
     bootstrap.md          ← fill this in first
   ```

### CoPilot
1. Copy the `agents/`, copy `commands/forge.md` -> `agents/`, copy `skills/interview-me` -> `skills/`, copy `prompts/`, and `bootstrap.md` into your project's `.github/` directory:

   ```
   .github/
     agents/
       coder.md
       dispatcher.md
       docs-writer.md
       forge.md
	     planner.md
       qa-reviewer.md
       researcher.md
       test-writer.md
     prompts/
       forge.prompt.md
	 skills/
	   interview-me/
	     SKILL.md
     design-doc/
       SKILL.md
     bootstrap.md          ← fill this in first
   ```

   `skills/curate-learnings` is Claude-only: it measures usage from Claude Code session
   transcripts (`~/.claude/projects/<slug>/*.jsonl`). Under CoPilot it finds no transcripts,
   reports "no evidence available", and proposes no evictions.

2. Open `bootstrap.md` with your LLM and fill in the four project-level placeholders.
   The guide walks through each one and tells you what to remove if a concept doesn't apply.
   
+ align models to use in agents frontmatter to fit your provider options. Follow the grades of models:
	planner	-> deep thinking model
	coder, qa-reviewer, test-writer, docs-writer	-> smart model
	dispatcher, researcher -> fast/cheap model

3. Run `/forge` inside your coding agent.

---

## Usage

```
/design-doc "rework how jobs report progress"      ← optional, writes a design doc
/forge "add email notifications when a job finishes"
/forge {docs-dir}/todo/my-feature.md
/forge {workflow-dir}/run-20260516-125849
```

`/design-doc` is the optional pre-design step described below — it settles the design and stops.

The first `/forge` form interviews you to clarify scope, then plans and builds.
The second form reads an existing plan document and picks up from there.
The third form resumes an aborted run — the pipeline re-enters at the most advanced completed stage.

---

## Pre-design Phase

`design-doc` is an optional Stage 0. Invoke it as `/design-doc "…"`, or by asking for a design,
planning, analysis, or architecture-decision document. It interviews you the same way the
planner does, then writes the document and stops — it never implements.

**What it produces.** A decision document at `{docs-dir}/todo/{slug}-design.md` (or
`{slug}-analysis.md` when it diagnoses an existing system rather than proposing a change), with
four sections that are always present — Context, Decisions, Affected files, Open questions —
plus optional sections such as Risks, Failure modes, or an Evaluation plan, added only when the
topic warrants them. Frontmatter carries `status: design | needs-decision | accepted`. See
[`skills/design-doc/SKILL.md`](skills/design-doc/SKILL.md) for the full contract.

**What it deliberately does not produce.** No Reachability table, no ordered implementation
steps, no line-level scope. The design doc owns *what and why*; the planner owns *where and
how*. That split is the point of the two-step flow — you settle the design at a high level
first, and the planner's job narrows to breaking those decisions down into a spec the coder can
execute without re-deciding anything.

**Chaining.** The document is directly ingestible by forge's doc-first mode:

```
/design-doc "rework how jobs report progress"
/forge {docs-dir}/todo/job-progress-design.md
```

The planner reads the document, settles any `[BLOCKING]` item with you before researching,
re-verifies every path it names, and treats decisions already recorded there as binding. It
records the path as `source_doc`, and the docs-writer closes the document out at the end of the
run — see [Design-doc closure](#design-doc-closure).

**When it is worth it.** Reach for the two-step flow when the scope is broad or contested, when
several approaches have real trade-offs, or when the decision should outlive the run that
implements it. For a well-understood change, `/forge "…"` interviews you directly and skips
the extra artifact.

---

## Pipeline stages

| Stage | Agent | What it does |
|-------|-------|-------------|
| 1 | **planner** | Interviews you, explores the codebase, writes `plan.md` |
| — | **dispatcher** | Reads the handoff log, routes or surfaces a question |
| ✋ | *approval gate* | You review the plan before any code is written |
| 2 | **coder** | Implements the plan; never writes test files |
| — | **dispatcher** | Routes or escalates back to planner if needed |
| 3 | **qa-reviewer** | Reviews touched files; writes `review-findings.md` for test-writer |
| — | **dispatcher** | Routes or sends bugs back to coder |
| ✋ | *approval gate* | You review findings before tests are written |
| 4 | **test-writer** | Writes and runs tests; escalates source bugs to coder |
| — | **dispatcher** | Confirms pass or routes back |
| 5 | **docs-writer** | Writes a changelog entry in `{docs-dir}/changes`, syncs living docs in `{living-docs-dir}`, closes out the source design doc |
| — | **dispatcher** | Confirms the docs sync, or surfaces documents it would not edit unasked |

**Researcher** is a read-only sub-agent dispatched on demand by the planner, coder, and
docs-writer to answer specific codebase questions without polluting their context.

### Living documentation sync

The docs-writer does not stop at the changelog. It builds a keyword set from the plan and the
coder's handoff log, dispatches researchers over `{living-docs-dir}` to find documents the
change affects — `*-documentation*` files, `todo/` backlogs, architecture and usage guides —
and grades each candidate before touching it:

| Grade | Action |
|-------|--------|
| `sure` | Related and demonstrably stale — apply a surgical edit |
| `unsure` | Related but the correct wording or scope is a judgment call — leave it, ask you |
| `dont-know` | Cannot tell if it is related — leave it, ask you |

Append-only history is never touched: `{docs-dir}/changes`, `{workflow-dir}` run directories,
dated archive files, and `{docs-dir}/lessons/`. Todo entries are marked done, never deleted.

Every modification is recorded with file paths and pre-edit line ranges in
`{workflow-dir}/run-{ts}/docs-updates.md` — written on every run, including runs that changed
no documentation.

### Design-doc closure

When a run started from a design doc (`/forge {docs-dir}/todo/my-feature.md`), the planner
records that path as `source_doc` and the docs-writer closes it out at the end. It checks the
document's decisions, affected files, `[BLOCKING]` and `[VERIFY]` items, and the test result
against what the run actually delivered:

- **All delivered** → frontmatter gets `status: final` and a `completed:` date. If
  `{docs-dir}/archive` exists, the document moves there; if not, it stays put — the directory
  is never created for you.
- **Partly delivered** → nothing is touched. The outstanding items are listed in
  `docs-updates.md`. A large design doc consumed by several runs stays open on purpose.
- **Ambiguous** → surfaced to you at the docs gate rather than decided.

The document body is never rewritten and no frontmatter key other than `status` and
`completed` is changed — a design doc records what was decided, not what was built.

---

## Routing and certainty grades

The dispatcher reads a `certainty` field from every handoff log:

| Grade | Action |
|-------|--------|
| `sure` | Auto-routes silently — no interruption |
| `unsure` | Pauses and surfaces a question to you |
| `dont-know` | Pauses and tells you what information is missing |

Maximum three escalation loops on any single stage before the pipeline surfaces to you
regardless of certainty.

---

## Placeholders

The agent files use four tokens that must be filled in for your project.
See [`bootstrap.md`](bootstrap.md) for descriptions, guidance, and examples for each.

| Placeholder | What it represents |
|-------------|-------------------|
| `{config-module}` | The file that centralises all env vars and constants |
| `{workflow-dir}` | Root directory for pipeline run artefacts |
| `{docs-dir}` | Root directory for project documentation — changelog, todo, and lessons live in fixed subdirectories under it |
| `{living-docs-dir}` | Documentation root the docs-writer keeps in sync |

---

## Repository layout

```
agents/
  coder.md          writes code, never test files
  dispatcher.md     routing brain — read-only, no file writes
  docs-writer.md    writes changelog entry and syncs living docs, never modifies source files
  planner.md        produces plan.md from task or existing doc
  qa-reviewer.md    reviews code, writes review-findings.md
  researcher.md     read-only codebase explorer, discarded context
  test-writer.md    writes and runs tests, escalates source bugs
commands/
  forge.md          /forge slash command orchestrator
skills/  
  interview-me/
    SKILL.md        Skill used for interviewing
  design-doc/
    SKILL.md        optional Stage 0 — interviews, writes a decision document, stops
  curate-learnings/
    SKILL.md        prunes, merges and promotes lessons/memories from measured usage
    references/     verdict policy and usage-ledger format
    scripts/        transcript scanner (read-only, stdlib only)
assets/
  pipeline-light.svg
  pipeline-dark.svg animated pipeline diagram, switched on prefers-color-scheme
  
bootstrap.md        placeholder guide for setting up a new project
```

---

## Docs
> Evolution of the pipeline and explanation of decision summarized here: [Building an Agentic Dev Pipeline — From Ad-Hoc Prompting to a Repeatable Protocol](https://dev.pazsitz.hu/building-an-agentic-dev-pipeline-from-ad-hoc-prompting-to-a-repeatable-protocol/)

---

## License

The rest of this repository is MIT — see [LICENSE](LICENSE).
