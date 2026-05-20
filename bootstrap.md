# Agent Pipeline Bootstrap Guide

Use this file when setting up the `docs/.claude/` agent pipeline for a new project.
Hand it to an LLM along with your project's `CLAUDE.md` and ask it to fill in the placeholders,
then search-replace across all agent files.

---

## Project-level placeholders

These four tokens appear in the agent files as `{name}`. They represent project-specific
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

### `{storage-write-helper}`

**Used in:** `agents/coder.md`, `agents/planner.md`, `agents/qa-reviewer.md`

**What it represents:**
A specific function or utility that all persistence writes must go through — providing
atomicity, validation, auditing, or conflict safety. Agents will flag any writes that bypass
it as convention violations.

**Guidance:**
Use `path/to/file:FunctionName` format. If multiple helpers exist for different storage
backends, pick the most critical one (usually the one handling the source-of-truth store)
and list others in `CLAUDE.md`.

| Example | Meaning |
|---------|---------|
| `storage/vault.py:atomic_write()` | Atomic markdown file writer |
| `db/repository.ts:upsert()` | Centralised DB write |
| `lib/store.go:SafeWrite` | Write-with-lock helper |

**If not applicable:** Writes are decentralised by design. Remove the `{storage-write-helper}`
bullet from each agent's convention section.

---

### `{isolation-key}`

**Used in:** `agents/coder.md`, `agents/planner.md`, `agents/qa-reviewer.md`, `agents/test-writer.md`

**What it represents:**
The field that scopes every data query and write to a specific user or tenant. Agents treat
any query missing this field as a bug. The test-writer will generate tests confirming
isolation works across two distinct values.

**Guidance:**
Use the exact field name as it appears in your data layer.

| Example | Context |
|---------|---------|
| `user_id` | Per-user isolation |
| `tenant_id` | Multi-tenant SaaS |
| `org_id` | Org-scoped data |
| `account_id` | Account-level partitioning |

**If not applicable:** Single-user or single-tenant system with no data isolation requirement.
Remove the `{isolation-key}` lines from all agent convention sections.

---

### `{workflow-dir}`

**Used in:** `commands/forge.md`, `agents/planner.md`, `agents/coder.md`, `agents/qa-reviewer.md`, `agents/test-writer.md`

**What it represents:**
The root directory where the pipeline writes its per-run working directories
(`{workflow-dir}/run-{ts}/`). Each run drops its handoff logs, plan, and review findings here.

**Guidance:**
Choose a path that is either gitignored or deliberately tracked. Using a path inside `.claude/`
keeps pipeline artefacts co-located with the agent config. Using a project-level path like
`tmp/workflow/` or `.pipeline/` separates them from Claude config.

| Example | Effect |
|---------|--------|
| `.claude/workflow` | Artefacts stay inside `.claude/` (original default) |
| `tmp/workflow` | Artefacts land in a top-level temp dir |
| `.pipeline` | Dedicated hidden dir at project root |

**Note:** Do not include a trailing slash — the pipeline appends `/run-{ts}/` itself.

---

### `{changelog-dir}`

**Used in:** `commands/forge.md` (Stage 5 — Documentation)

**What it represents:**
The directory where the pipeline writes a changelog document after each completed feature.
The documentation stage reads an existing file from this directory as a style sample, then
writes the new entry alongside it.

**Guidance:**
Use a path relative to the project root. The directory must already exist and contain at
least one sample document for the style reference to work.

| Example |
|---------|
| `docs/changes/` |
| `CHANGELOG/` |
| `.changes/` |

**If not applicable:** Your project doesn't maintain a changelog directory. Remove Stage 5
(Documentation) from `commands/forge.md` and the `changelog:` line from
the Final Summary block.

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

1. **Give the LLM this file and your project's `CLAUDE.md`.**
   Ask: *"Read bootstrap.md and CLAUDE.md. For each project-level placeholder,
   ask me one question at a time until you have a value or a 'not applicable' decision."*

2. **For each placeholder the LLM surfaces,** provide either:
   - A concrete value (e.g. `src/config.ts`)
   - `n/a` — if the concept doesn't apply to your project

3. **Have the LLM apply the values:**
   Ask: *"Now search-replace every `{placeholder}` across all files under `docs/.claude/`
   with the value I gave you. For any `n/a`, remove the corresponding bullet or section
   from the relevant agent files."*

4. **Review the results.** Spot-check that:
   - Every `{...}` token is gone from agent files (except runtime tokens)
   - Removed sections make sense (no dangling references)
   - `CLAUDE.md` documents the chosen values under a conventions section

5. **Optional:** If your project uses a different test layout, update the path template in
   `agents/test-writer.md` under "Test conventions" to match.
