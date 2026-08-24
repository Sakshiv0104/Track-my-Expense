# Expense Tracker

![Expense Tracker hero banner](static/images/hero-banner.jpg)

A lightweight personal expense tracker built with **Flask** and **SQLite**. Register an account, log expenses, filter them by date, edit or delete entries, and track spending from a simple dashboard.

- **Backend:** Flask (single `app.py`, no blueprints)
- **Database:** SQLite, raw parameterized queries, no ORM
- **Frontend:** Jinja2 templates + vanilla CSS/JS, no frontend framework
- **Deployment:** Railway

---

## Built with Claude Code: a spec-driven development case study

This project was built end-to-end as a structured exercise in using **Claude Code** as a disciplined engineering collaborator rather than a one-shot code generator. Every feature (registration, login/logout, the profile dashboard, date filtering, add/edit/delete expense) went through the same repeatable pipeline, enforced by custom tooling rather than ad hoc prompting.

### 1. A steering SPEC (`CLAUDE.md`)
Before any feature work started, the project's architecture, code style, tech constraints, route status table, and "never do this" list were written into `CLAUDE.md`. This is the single source of truth Claude Code reads on every turn. It's what stops the model from reaching for an ORM, hardcoding a URL, or implementing a stub route ahead of schedule.

### 2. SPEC-first feature planning
Each step of the roadmap started as a **spec**, not code. The custom `/create-spec` slash command:
- verifies the working tree is clean and creates a `feature/<name>` branch off `main`,
- reads `CLAUDE.md`, `app.py`, `database/db.py`, and every existing spec to avoid duplicating work,
- writes a structured spec to `.claude/specs/` covering routes, DB changes, templates, files touched, and a testable "definition of done."

Nine specs (`.claude/specs/01-database-setup.md` to `10-final-edits.md`) and matching implementation plans (`.claude/plans/`) trace the full build, one Claude Code **PLAN MODE** session per feature, before a single line of implementation code was written.

### 3. GIT discipline as a first-class constraint
Every feature lived on its own branch and was merged via PR (`feature/registration`, `feature/login-logout`, `feature/date_filter`, `feature/add-expense`, `feature/edit-expense`, `feature/delete-expense`, and so on), visible directly in the commit history. The `/create-spec` command enforces this: it refuses to start new work on a dirty tree and always branches from a freshly pulled `main`.

### 4. Guardrails via HOOKS
`.claude/settings.json` wires in two hooks that run automatically, independent of what any prompt says:
- **PostToolUse** on `Write`/`Edit`: auto-formats any touched `.py` file with `black`.
- **PreToolUse** on `Bash`: blocks destructive commands (`rm`, `truncate`, `unlink`) targeting protected paths like `spendly.db`, `.env`, or `migrations/`.

### 5. Purpose-built SUBAGENTS
Rather than one general-purpose agent doing everything, the project defines narrow subagents in `.claude/agents/`, each with a scoped tool set and a single job:
- **spec-test-writer**: writes pytest cases *from the spec's requirements*, deliberately never from reading the implementation, so tests check intent rather than mirror bugs.
- **test-runner**: executes only the relevant test file and produces a pass/fail report; it never edits code.
- **spendly-security-reviewer** / **quality-reviewer**: run in parallel over the same diff, one focused purely on security, the other on Flask code quality, never overlapping concerns.
- **deployment-video-maker**: drives a Playwright script (`tools/record_demo.py`) against the live deployment to record a demo walkthrough (login, add expense, delete expense, logout).

### 6. Orchestrated pipelines via custom SLASH COMMANDS
Two commands chain subagents into a repeatable pipeline instead of relying on remembering the right sequence of manual steps:
- **`/test-feature <spec>`**: invokes `spec-test-writer`, waits for it to finish, then hands off to `test-runner`, and reports a single pass/fail verdict.
- **`/code-review-feature <spec>`**: runs `spendly-security-reviewer` and `spendly-quality-reviewer` in parallel over the current diff, merges their findings into one report with a combined action plan and overall verdict, and only touches code after explicit approval.

### 7. SKILLS for consistent design
A custom `ui-designer` skill (`.claude/skills/ui-designer/`) encodes the project's visual language (fintech-style cards, spacing, shadows, Lucide icons) so every new page or component matches the existing UI instead of drifting stylistically feature by feature.

### 8. DEPLOYMENT and verification
The app was prepared and deployed to **Railway** (`Procfile`, environment config), and a dedicated Playwright-based tool plus subagent records a working end-to-end demo video against the live URL as a final verification step: proof the deployed app actually works, not just that tests pass locally.

**The result:** a small Flask app built the way a production feature would be. Spec reviewed before code, tests derived from intent, security and quality reviewed independently, and every step traceable through its own branch, spec, and PR.

---

## Local development

```bash
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

python app.py                     # runs on http://localhost:5001
```

## Testing

```bash
pytest                            # run all tests
pytest tests/test_foo.py          # run a specific test file
pytest -k "test_name"             # run a specific test by name
```
