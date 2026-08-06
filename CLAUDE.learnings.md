## Self-improvement
Update `docs/lessons/lessons.md` whenever something learning-worthy happens, not only when corrected:
- User correction — pattern + rule to prevent recurrence.
- Self-caught mistake — same, even if fixed before the user noticed.
- Notable observation, which would have changed an action — a non-obvious gotcha, dead end, or confirmed-good approach worth remembering.

Structure similarly as Memories (MEMORY.md) formatted, `date — [link](file.md) — one clause, ≤200 chars` in lessons.md only. Individual lession files separatly stored.
Before being write-only, do a quick sanity check first, a new file requires that no existing lesson states the same rule.
One rule per lesson, per session.

Shape of an individual lesson file, stored as `docs/lessons/YYYY-MM-DD-<slug>.md`:
- Frontmatter: `name` (the slug), `date`, `type` (correction | mistake | observation).
- Body: the rule in one sentence, then `**Why:**` with the case it came from, then `**How to apply:**` with what to do differently.
- Keep the `lessons.md` index line under 200 characters. The index loads every session, the file does not, so detail belongs in the file.

At session start for a known project: review `docs/lessons/lessons.md` if it exists.