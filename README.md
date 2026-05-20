# Forge

**Structured, multi-agent development pipeline for [Claude Code](https://docs.anthropic.com/en/docs/claude-code)**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

A drop-in set of Claude Code agent definitions and a slash command that turn a task description
into reviewed, tested code — with human approval gates at each major stage.
Language and framework agnostic. Configurable for any project via five placeholders.

```
idea or plan doc
       │
   [planner]  ←── grill-me interview
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
   [docs stage]
       │
     done
```

Escalation paths run in both directions — the coder can send ambiguous requirements back to
the planner; the qa-reviewer can send bugs back to the coder; the test-writer can surface
source bugs before they reach you.

---

## Requirements

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (any recent version)
- A project with a `CLAUDE.md` at its root

---

## Installation

1. Copy the `agents/`, `commands/`, and `bootstrap.md` into your project's `.claude/` directory:

   ```
   .claude/
     agents/
       coder.md
       dispatcher.md
       planner.md
       qa-reviewer.md
       researcher.md
       test-writer.md
     commands/
       forge.md
     bootstrap.md          ← fill this in first
   ```

2. Open `bootstrap.md` with your LLM and fill in the five project-level placeholders.
   The guide walks through each one and tells you what to remove if a concept doesn't apply.

3. Run `/forge` inside Claude Code.

---

## Usage

```
/forge "add email notifications when a job finishes"
/forge docs/plans/my-feature.md
```

The first form interviews you to clarify scope, then plans and builds.
The second form reads an existing plan document and picks up from there.

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
| 5 | *(orchestrator)* | Writes a changelog entry in `{changelog-dir}` |

**Researcher** is a read-only sub-agent dispatched on demand by the planner and coder to
answer specific codebase questions without polluting their context.

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

The agent files use five tokens that must be filled in for your project.
See [`bootstrap.md`](bootstrap.md) for descriptions, guidance, and examples for each.

| Placeholder | What it represents |
|-------------|-------------------|
| `{config-module}` | The file that centralises all env vars and constants |
| `{storage-write-helper}` | The function all persistence writes go through |
| `{isolation-key}` | The field that scopes data per user or tenant |
| `{workflow-dir}` | Root directory for pipeline run artefacts |
| `{changelog-dir}` | Directory where changelog entries are written |

---

## Repository layout

```
agents/
  coder.md          writes code, never test files
  dispatcher.md     routing brain — read-only, no file writes
  planner.md        produces plan.md from task or existing doc
  qa-reviewer.md    reviews code, writes review-findings.md
  researcher.md     read-only codebase explorer, discarded context
  test-writer.md    writes and runs tests, escalates source bugs
commands/
  forge.md the /forge slash command orchestrator
bootstrap.md        placeholder guide for setting up a new project
```

---

## Acknowledgements

The `grill-me` skill (`commands/grill-me/skill.md`) is taken from
[mattpocock/skills](https://github.com/mattpocock/skills) and is used here unmodified.

> MIT License — Copyright (c) 2026 Matt Pocock

Full license: https://github.com/mattpocock/skills/blob/main/LICENSE

---

## License

The rest of this repository is MIT — see [LICENSE](LICENSE).
