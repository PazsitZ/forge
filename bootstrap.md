# Agent Pipeline Bootstrap Guide

Use this file when setting up the `.claude/` agent pipeline for a new project.
Hand it to an LLM along with your project's `CLAUDE.md` and ask it to fill in the placeholders,
then search-replace across all agent files.

---

## Project-level placeholders

These tokens appear in the agent files as `{name}`. They represent project-specific
concepts that must be resolved once at bootstrap time. For each one: decide the value,
replace it in every agent file that references it, and document it in `CLAUDE.md`.

---

### `{config-module}`

**Used in:** `agents/coder.md`, `agents/planner.md`, `agents/qa-reviewer.md`

**What it represents:**
The single file or module that centralizes all configuration constants — env vars, service
endpoints, paths, collection/table names. Agents instruct the coder to never hardcode these
values and always import from here instead.

**Guidance:**
Pick the one file where your project's constants live. If none exists yet, create it as part
of setup. Reference it as a path relative to the project root.

| Example | Stack |
|---------|-------|
| `src/config.py` | Python |
| `config/settings.ts` | TypeScript/Node |
| `lib/config.go` | Go |
| `src/main/resources/application.yml` | Java/Spring |

**If not applicable:** Your project hardcodes values or uses a framework-managed config
with no single source file. In that case, remove the `{config-module}` bullet from each
agent's convention section and describe the actual pattern in `CLAUDE.md`.

---

### `{workflow-dir}`

**Used in:** `commands/forge.md`, `agents/planner.md`, `agents/coder.md`, `agents/qa-reviewer.md`, `agents/test-writer.md`

**What it represents:**
The root directory where the pipeline writes its per-run working directories
(`{workflow-dir}/run-{ts}/`). Each run drops its handoff logs, plan, and review findings here.

**Guidance:**
Choose a path that is either gitignored or deliberately tracked. Using a path inside `.claude/`
keeps pipeline artifacts co-located with the agent config. Using a project-level path like
`tmp/workflow/` or `.pipeline/` separates them from Claude config.

| Example | Effect |
|---------|--------|
| `.claude/workflow` | Artifacts stay inside `.claude/` (original default) |
| `tmp/workflow` | Artifacts land in a top-level temp dir |
| `.pipeline` | Dedicated hidden dir at project root |

**Note:** Do not include a trailing slash — the pipeline appends `/run-{ts}/` itself.

---

### `{docs-dir}`

**Used in:** `commands/forge.md` (Stage 5 — Documentation), `agents/docs-writer.md`,
`skills/design-doc/SKILL.md`

**What it represents:**
The root directory for the project's own documentation — the single placeholder that
replaces `docs/changes`, `docs/lessons`, `docs/todo` and similar hardcoded paths. Every
pipeline artifact that isn't code lives in a **fixed subdirectory** under this root:
`{docs-dir}/changes` (changelog), `{docs-dir}/todo` (design docs from the `design-doc`
skill). See [Document directory layout](#document-directory-layout) below for the full list.

Only the root is a placeholder. The subdirectory names themselves (`changes`, `todo`, …)
are conventions baked into the agent and skill files — do not turn them into placeholders
too. If a project needs a different subdirectory name, edit the reference directly in the
file that uses it rather than adding another `{...}` token.

**Guidance:**
Use a path relative to the project root. `{docs-dir}/changes` must already exist and
contain at least one sample document for the changelog style reference to work.

| Example |
|---------|
| `docs` |
| `documentation` |
| `.docs` |

**If not applicable:** Your project doesn't maintain a changelog. Remove Part A
(Changelog) from `agents/docs-writer.md` and the `changelog:` line from the Final Summary
block in `commands/forge.md`. Keep Stage 5 if you still want the living-doc sync. If your
project keeps no documentation at all, also remove the `design-doc` skill's write step.

---

### `{living-docs-dir}`

**Used in:** `commands/forge.md` (Stage 5 — Documentation), `agents/docs-writer.md`

**What it represents:**
The root of the project's **living documentation** — documents that describe how the system
currently works or what is currently planned, and therefore go stale when the code changes.
After each run, the docs-writer dispatches researchers over this tree, grades every candidate
document, and updates the ones that the change made false.

This is the opposite of `{docs-dir}/changes`, which is an append-only history. The docs-writer
never edits `{docs-dir}/changes`, `{workflow-dir}`, dated archive files, or `{docs-dir}/lessons/` —
correcting a historical record falsifies it.

**Guidance:**
Point this at the documentation root, not at an individual file. One directory only; if your
docs are split across several roots, pick the common ancestor. Typical contents the sync
targets: `*-documentation*` files and directories, `todo/`, `bugs/` backlogs, architecture and design
notes, setup and usage guides.

| Example | Effect |
|---------|--------|
| `docs` | Whole docs tree, minus the excluded subdirectories |
| `docs/reference` | Narrow — only the reference set is kept in sync |
| `.` | Whole repo; use only if documentation lives beside the code |

**Note:** Do not include a trailing slash.

**If not applicable:** Your project keeps no living documentation. Remove Part B (Living
documentation sync), Part C (Design-doc closure) and Part D (Audit log) from
`agents/docs-writer.md`, and in `commands/forge.md` drop the post-docs-writer dispatcher and
the `living docs:` and `design doc:` lines from the Final Summary.

---

## Document directory layout

Reference only — none of the entries below are placeholders. Each is a fixed subdirectory
name baked into the agent/skill files that reference it, always relative to `{docs-dir}`.
If a project wants a different name for one of these, edit the reference directly in the
listed file(s) rather than introducing a new `{...}` token.

| Directory | Written by | Read by | Purpose |
|---|---|---|---|
| `{docs-dir}/changes` | `agents/docs-writer.md` | style-sample step in `agents/docs-writer.md` | Append-only changelog, one file per completed run. Never edited after the fact. |
| `{docs-dir}/todo` | `skills/design-doc/SKILL.md` | `commands/forge.md` (doc-first mode input), `agents/docs-writer.md` (marks resolved entries done, never deletes) | Design/analysis documents awaiting a `/forge` run, and the open backlog. |
| `{docs-dir}/lessons` | project-specific (not written by this pipeline) | — | The user's own record of what happened. Explicitly excluded from the docs-writer's living-doc sync — never edited or corrected retroactively. |
| `{docs-dir}/archive` | `agents/docs-writer.md` (Part C4) | — | **Optional.** Design docs the pipeline has fully delivered, moved out of `{docs-dir}/todo` after being marked `status: final`. If the directory does not exist, the move is skipped — the docs-writer never creates it. Delete the directory to opt out of archiving. |

`{living-docs-dir}` (see above) typically points at `{docs-dir}` itself, so the sync
naturally treats `{docs-dir}/changes`, `{docs-dir}/lessons`, and `{workflow-dir}` as
excluded subtrees rather than in-scope documentation.

---

## Runtime template tokens

These tokens are **not** filled in at bootstrap time. The pipeline populates them
automatically at runtime. No action needed — listed here for reference.

| Token | Populated by | Meaning |
|-------|-------------|---------|
| `{ts}` | orchestrator at run start | Timestamp for the current run (`YYYYMMDD-HHMMSS`) |
| `{date}` | derived from `{ts}` | Date portion of the run timestamp |
| `{feature}` | derived from plan title | Short slug for the feature being built |
| `{kebab-case-feature-name}` | derived from plan title | Kebab-case slug used in filenames |
| `{module}` | path template | Source package subdirectory in test file paths |
| `{filename}` / `{file}` | path template | File name in test or handoff references |
| `{symbol}` | path template | Code symbol (function, class) in plan examples |
| `{package}` | path template | Package directory referenced by the researcher |
| `{instruction}` | user input at gate | Fix instruction passed at a review approval gate |

---

## Bootstrap workflow

Typical session with an LLM:

1. **Give the LLM this file and your project's `CLAUDE.md` / `copilot-instructions.md`.**
   Ask: *"Read bootstrap.md and project relavant .md. For each project-level placeholder,
   ask me one question at a time until you have a value or a 'not applicable' decision."*

2. **For each placeholder the LLM surfaces,** provide either:
   - A concrete value (e.g. `src/config.ts`)
   - `n/a` — if the concept doesn't apply to your project

3. **Have the LLM apply the values:**
   Ask: *"Now search-replace every `{placeholder}` across all files under `.claude/`
   with the value I gave you. For any `n/a`, remove the corresponding bullet or section
   from the relevant agent files."*

4. **Review the results.** Spot-check that:
   - Every `{...}` token is gone from agent files (except runtime tokens)
   - Removed sections make sense (no dangling references)

5. **Optional:** If your project uses a different test layout, update the path template in
   `agents/test-writer.md` under "Test conventions" to match.
