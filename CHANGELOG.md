# Changelog

## 2026-08-02

The `docs-writer` agent now syncs living documentation, not just the changelog.

**Added**
- `{living-docs-dir}` placeholder — the documentation root the sync operates on. Documented in `bootstrap.md` with a "not applicable" removal path.
- Living-doc discovery in `agents/docs-writer.md`: a keyword set derived from `plan.md` and the coder handoff log, then up to three **researcher** dispatches over `{living-docs-dir}`. The agent gains `Edit` and `Task`; it has no Grep or Bash, so all searching goes through the researcher.
- Per-document grading before any edit — `sure` applies a surgical edit, `unsure` and `dont-know` are recorded as pending and surfaced to the user. Explicit exclusion list for append-only history: `{changelog-dir}`, `{workflow-dir}` run directories, dated archive files, `docs/lessons/`.
- Audit log `{run_dir}/docs-updates.md` — written on every run, including no-op runs. Records the keyword set, the researcher dispatches, and each modification with its pre-edit line ranges, plus pending and skipped sections.
- Post-docs-writer dispatcher and a docs-sync gate in `commands/forge.md` (`Apply` / `Skip` / `Abort`). Stage 5 was previously terminal and had no dispatcher.

**Changed**
- Resume mode scans for `docs-writer.md` and re-enters at the Stage 5 dispatcher.
- Final Summary reports updated and pending living docs and lists `docs-updates.md`.
- `agents/dispatcher.md` accepts `post-docs-writer` and `docs-writer` as a `next` value.

## 2026-08-01
Added `design-doc` Skill. This produces a specific document, which can be inputted to the `forge` pipleine's planner.
It creates a mid-high level design-doc. This produces a wider scopeddesign with additional components, discovering goals, options, risks and consequences.

## 2026-07-30
Replaced the `grill-me` skill to `interview-me`.
Using similar basis as Matt Pocock's grill-me, but widely extended

Notable changes to Forge. The planner agent carries its own contract version (`v0`–`v4`).

`v2`–`v4` came out of a five-model comparison (Sonnet 5 plus three open-weight models,
six plan artifacts) run against the published `v1`. Rationale and failure analysis:
[Small Models Are Prompt Linters - How a Model Eval Turned out Agent Contract Refinement](https://dev.pazsitz.hu/how-a-model-eval-turned-out-agent-contract-refinement/))

| Version | Words | Released |
|---|---|---|
| [v4](#v4--2026-07-29) | 1,660 | 2026-07-29 |
| [v3](#v3--unreleased) | 1,476 | — |
| [v2](#v2--unreleased) | 1,878 | — |
| [v1](#v1--initial-release) | 1,388 | initial release |
| [v0](#v0--pre-release) | 955 | — |

---

## v4 — 2026-07-29

Planner 1,476 → 1,660 words.

**Added**
- `## Hazards` — required `plan.md` section between `## Reachability` and `## Requirements`. Table: obstacle, where, why the naive approach fails, resolution, cost. `none` when research found no obstacle.
- Hazard-vs-options boundary rule in `## Multiple solutions` — one defensible resolution is a row; a resolution that is itself a fork goes to the user.
- Escalation condition: a `## Hazards` row with no priceable resolution.
- Self-check item: every `## Hazards` row names a `file:line` and a resolution, or the section reads `none`.
- Revision record — handoff log `## did` records any discarded draft approach and why it lost.
- **Validator pass** before the plan approval gate (`commands/forge.md`): required sections, unresolved `Reachability` rows, `[BLOCKING]` alongside `certainty: sure`, researcher dispatch recorded.

**Changed**
- Orchestrator gates use the `{workflow-dir}` placeholder — several had a hardcoded `.claude/workflow/`.
- Router-identity rule reworded.

**Removed**
- Duplicated no-Grep prose from the `## Reachability` placeholder — restated `## Tools`, and sat inside the fence, so it was copied into every generated `plan.md`.

---

## v3 — unreleased

Planner 1,878 → 1,476 words. Reorganised, not appended.

**Added**
- `## Tools` — new section, placed *before* `## Input modes`. No-Grep/no-Bash constraint stated ahead of the workflow depending on it.
- Stop rule in `## Response to orchestrator` — planner ends at `plan.md` + handoff log. No implementation, tests or changelogs. Previously lived only in the orchestrator, where long runs diluted it out of context.

**Changed**
- `## Exploration findings` moved inside the fenced `plan.md` template (was below the fence under an "optional section" preamble, and got omitted).
- `## Parallel exploration` + `## Researcher subagent` → merged into `## Researcher dispatch`.
- `## Escalation conditions` → `## Interview vs escalate`, keyed on what is missing: preference → `interview-me`; unobtainable fact or contradiction → escalate; fact a grep answers → dispatch a researcher.
- `## Plan document format` → `## plan.md format`.

**Fixed**
- `## Forbidden in plan.md` → `## Banned in plan.md`, and its self-check to `no banned string appears outside ## Open questions`. Read literally the old check asserted the *heading* must not appear in the artifact — trivially true, so it passed unconditionally.

---

## v2 — unreleased

Planner 1,388 → 1,878 words. Superseded by `v3`; compliance did not improve.

**Added**
- Role preamble — output is a spec not prose; discovery is the planner's job, not the coder's; unmade forks and silent defaults both count as failures.
- `## Forbidden in plan.md` — banned phrases (`need to check`, `should verify`, `TBD`, future-tense references to research, conditionals over unknown facts), legal only in `## Open questions`.
- Explicit wait-for-researchers rule.
- Pre-handoff self-check against a fixed list.

---

## v1 — initial release

Planner 955 → 1,388 words. Initial public release: planner, coder, qa-reviewer,
test-writer, docs-writer, researcher, dispatcher, the `/forge` orchestrator, `bootstrap.md`.

**Added**
- `## Reachability` — every changed symbol, every `file:line` that reads or calls it, and whether that file is in `files to modify`.
- No-Grep/no-Bash tooling constraint — every line number comes from a researcher dispatch, quoted in the handoff log.
- `[BLOCKING]` / `[VERIFY]` tagging in `## Open questions`.

---

## v0 — pre-release

955 words. Nine sections. No reachability, no tagging, no tooling constraint.

---

## Migration

Replace `agents/planner.md` wholesale — the changes are structural and the file was
reorganised twice. Re-apply your placeholders (`{config-module}` in `## Project context`
is the easiest to miss). Consumers of `plan.md` gain one required section, `## Hazards`.
