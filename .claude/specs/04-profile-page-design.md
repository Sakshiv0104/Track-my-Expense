# Spec: Profile Page Design

## Overview

This feature implements the working `GET /profile` page for Spendly. It currently is a stub that returns the raw string `"Profile page — coming in Step 4"`. This step replaces that stub with a real, styled page showing the logged-in user's account details (name, email, member-since date) plus a fuller picture of their expense activity: two summary stats, a spend-by-category chart, and a recent-expenses list. Since a profile is inherently personal, this step also introduces the app's first login-required route: an unauthenticated visitor hitting `/profile` is redirected to `/login` instead of seeing the stub. This is a read-only "view profile" page — editing profile fields, and editing/deleting expenses, is not part of this step.

When a logged-in user visits `/profile`, they see four expense-related pieces, top to bottom:

1. **Total spent** (stat card) — lifetime sum of their expenses
2. **Expenses logged** (stat card) — lifetime count of their expenses
3. **Spend by category** (bar chart) — every category they've spent in, ranked highest to lowest, each row showing the category name and the amount spent, bar length proportional to amount
4. **Recent expenses** (list) — their 5 most recent expenses (date, category, description, amount), newest first

Each category has its own validated color (bar fill / dot / tag tint), always paired with its text label — see "Rules for implementation" for the palette source and its limits.

## Depends on

- Step 1 (Database Setup) — requires `get_db()`, the `users` and `expenses` tables.
- Step 2 (Registration) — requires real user accounts to exist.
- Step 3 (Login and Logout) — requires `session['user_id']` to be set on login so `/profile` knows who the current user is.

## Routes

- `GET /profile` — renders `profile.html` with the current user's account info and expense summary — logged-in only (redirects to `GET /login` if `session.get('user_id')` is not set)

No other routes are added or changed.

## Database changes

No new tables or columns — `users` and `expenses` already have everything needed.

Three new functions must be added to `database/db.py` (never inline in `app.py`):

- `get_expense_summary(user_id)` — runs a parameterized aggregate query (`SUM(amount)`, `COUNT(*)`) against `expenses` for the given `user_id` and returns total spent and expense count (total defaults to `0` when the user has no expenses, not `None`)
- `get_category_breakdown(user_id)` — runs a parameterized `SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category ORDER BY total DESC` and returns the rows (empty list, not an error, when the user has no expenses)
- `get_recent_expenses(user_id, limit=5)` — runs a parameterized `SELECT ... FROM expenses WHERE user_id = ? ORDER BY date DESC, id DESC LIMIT ?` and returns the rows (empty list when the user has no expenses)

`get_user_by_id()` (added in Step 3's groundwork, already used by `inject_current_user`) is reused to fetch the profile's name/email/created_at — no changes needed there.

## Templates

**Create:**
- `templates/profile.html` — extends `base.html`; shows the user's name, email, and member-since date (formatted from `created_at`); two stat cards (total spent, expense count); a "Spend by category" bar chart built from `get_category_breakdown()`; a "Recent expenses" list built from `get_recent_expenses()`. Both the chart and the list render an empty-state message ("No expenses yet.") instead of an empty chart/table when the user has no expenses.

**Modify:**
- `templates/base.html` — the logged-in nav state (added in Step 3) shows "Welcome, {name}" and "Log out" but has no link to `/profile` at all; add a dedicated `<a href="{{ url_for('profile') }}">Profile</a>` link between them. "Welcome, {name}" stays plain text (`<span>`), not a disguised link — a user shouldn't have to guess that a greeting is clickable.
- `app.py`'s `login` view (from Step 3) — change the post-login redirect from `url_for('landing')` to `url_for('profile')`, so a user lands on their profile immediately after signing in instead of having to navigate there manually.

## Files to change

- `app.py` — replace the `profile` stub: check `session.get('user_id')`, redirect to `url_for('login')` if absent, otherwise fetch the user via `get_user_by_id()`, the summary via `get_expense_summary()`, the breakdown via `get_category_breakdown()`, and the recent list via `get_recent_expenses()`, then render `profile.html` with all four; also change the `login` view's post-success redirect to `url_for('profile')`
- `database/db.py` — add `get_expense_summary(user_id)`, `get_category_breakdown(user_id)`, `get_recent_expenses(user_id, limit=5)`
- `templates/base.html` — add a "Profile" nav link next to the plain-text "Welcome, {name}" greeting

## Files to create

- `templates/profile.html`
- `static/css/profile.css` — profile-page-only styles, linked only from `profile.html`, following the same pattern as `static/css/landing.css`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords are never displayed or re-hashed on this page — this step is read-only
- Use CSS variables (from `style.css`'s `:root`) — never hardcode hex values in `profile.css`
- All templates extend `base.html`
- All DB logic lives in `database/db.py`, never inline in the route
- Use `url_for()` for every internal link/redirect — never hardcode paths
- `get_expense_summary()` must return `0`/`0` (not `None`) for a user with no expenses — use `COALESCE(SUM(amount), 0)` in the query
- `get_category_breakdown()` and `get_recent_expenses()` must return an empty list (not `None`, not an error) for a user with no expenses
- Each of the 7 fixed categories has a dedicated color: `--cat-food`, `--cat-transport`, `--cat-bills`, `--cat-health`, `--cat-entertainment`, `--cat-shopping`, `--cat-other` (plus `-light` tints), defined in `style.css`'s `:root`. These are the dataviz skill's **documented, pre-validated 8-hue categorical palette** (not eyeballed) — the project's earlier mock-card palette (`--accent`, `--accent-2`, plus two hardcoded hex values) was rejected for this because it fails colorblind-safety validation. The chosen 7 slots pass all six checks against Spendly's white card surface (only a contrast WARN on 3 hues, mitigated below).
- Color is a **secondary** identity channel, never the only one — every category is still directly text-labeled (bar chart row name, recent-expenses tag text), which satisfies the palette's required contrast/CVD relief. Text itself is never colored by category — only the bar fill, a small dot next to the category name, and the recent-expenses tag *background* (light tint) carry the hue; tag text stays neutral ink.
- **Known limitation, accepted deliberately:** the palette's validated adjacency guarantee assumes the fixed slot order (1↔2, 2↔3, …) is what's visually adjacent. The category chart instead sorts by amount, so which two categories end up next to each other depends on the logged-in user's data, not the palette's fixed order — the adjacency validation doesn't strictly cover every possible pairing. This is accepted because the always-present text label is the primary identity channel regardless of which colors end up adjacent.
- The category bar chart follows fixed mark specs: bars ≤ 24px thick, rounded only at the data end (square at the baseline), value labeled at the tip, no gridlines/axis — it's a ranked comparison, not a scale
- Do not implement editing profile fields, changing password, or any `POST` handling on `/profile` — out of scope for this step
- Do not implement `/expenses/add`, `/expenses/<id>/edit`, or `/expenses/<id>/delete` — those stay stubs per the roadmap; the recent-expenses list is read-only with no edit/delete links

## Definition of done

- [ ] Submitting the login form with valid credentials lands the user directly on `/profile` — no extra click required
- [ ] After logging in, the navbar has a dedicated "Profile" link, separate from the plain-text "Welcome, {name}" greeting
- [ ] Visiting `/profile` while logged out redirects to `/login` and does not leak any profile data
- [ ] Visiting `/profile` while logged in renders `profile.html` (not a raw string) showing the correct name, email, and member-since date for the current session user
- [ ] The stats block shows the correct total spent and expense count for the demo user's 8 seeded expenses
- [ ] The "Spend by category" chart shows one bar per category the demo user has spent in, ranked highest to lowest, each with a visible amount label
- [ ] The "Recent expenses" list shows the demo user's 5 most recent expenses, newest first, with date/category/description/amount
- [ ] A user with zero expenses sees `0` total spent, `0` expenses, and an empty-state message in place of the chart and the recent-expenses list — not an error or a blank section
- [ ] Each category shows its own color (bar fill, dot, or tag tint) from the `--cat-*` tokens in `style.css` — text itself is never colored, only marks/backgrounds
- [ ] `profile.html` extends `base.html` and pulls in `static/css/profile.css`
- [ ] All new/changed queries in `database/db.py` use `?` parameterized placeholders
- [ ] The app starts and runs without errors on `python app.py` (port 5001)
