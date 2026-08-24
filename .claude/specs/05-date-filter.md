# Spec: Dashboard Date Filter

## Overview

This feature adds date-range filtering to the `/profile` dashboard. Today `/profile` always shows lifetime totals, an all-time category breakdown, and the 5 most recent expenses with no way to narrow the view. This step adds a simple date-range filter (start date + end date) so a logged-in user can see their stats, category breakdown, and recent expenses scoped to a specific period (e.g. "this month", "last 30 days", or any custom range) instead of only ever seeing all-time data. The filter is expressed as URL query parameters on `GET /profile` so the filtered view stays bookmarkable and shareable, and no new routes or JS frameworks are needed.

## Depends on

- Step 1 (Database Setup) — requires `get_db()`, the `users` and `expenses` tables.
- Step 3 (Login and Logout) — requires `session['user_id']` to identify the current user.
- Step 4 (Profile Page Design) — requires the existing `/profile` route, `profile.html`, and the `get_expense_summary`, `get_category_breakdown`, `get_recent_expenses` functions this step modifies.

## Routes

- `GET /profile` — modified (not new): now accepts optional `start_date` and `end_date` query string params (`YYYY-MM-DD`). When both are present and valid, the stats, category breakdown, and recent-expenses list are scoped to that inclusive date range. When absent, invalid, or `start_date > end_date`, the page falls back to the existing all-time behavior and shows a non-blocking notice for the invalid case. Access level unchanged — logged-in only.

## Database changes

No new tables or columns — `expenses.date` (`YYYY-MM-DD` TEXT) already supports range filtering.

Modify three existing functions in `database/db.py` to accept optional `start_date=None, end_date=None` keyword args. When both are provided, add a parameterized `AND date BETWEEN ? AND ?` clause; when not provided, behave exactly as today (no query shape change, so existing callers/tests are unaffected):

- `get_expense_summary(user_id, start_date=None, end_date=None)`
- `get_category_breakdown(user_id, start_date=None, end_date=None)`
- `get_recent_expenses(user_id, limit=5, start_date=None, end_date=None)`

## Templates

**Create:**
- No new templates.

**Modify:**
- `templates/profile.html` — add a date-filter form above the stats block: two `<input type="date">` fields (`start_date`, `end_date`) plus an "Apply" submit button, using `method="GET"` action `{{ url_for('profile') }}` so filtering is a plain navigation, not JS/AJAX. Pre-fill both inputs from the current query params (via `request.args`) so the filter persists across reloads. Add a "Clear filter" link (plain `<a href="{{ url_for('profile') }}">`) that only renders when a filter is active. When a filter is active, show a small "Showing: {start_date} – {end_date}" label near the stats. When the filter yields zero expenses in range, reuse the existing empty-state pattern ("No expenses in this range.") instead of an error.

## Files to change

- `app.py` — in the `profile` view, read `start_date`/`end_date` from `request.args`, validate them (parseable `YYYY-MM-DD`, `start_date <= end_date`), and pass them through to `get_expense_summary`, `get_category_breakdown`, `get_recent_expenses`; pass the (possibly cleared) `start_date`/`end_date` and a validation `error` (if any) to the template
- `database/db.py` — add optional `start_date`/`end_date` params to `get_expense_summary`, `get_category_breakdown`, `get_recent_expenses`
- `templates/profile.html` — add the date-filter form, the "Showing: X – Y" label, the "Clear filter" link, and the "No expenses in this range." empty state

## Files to create

- None.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL, including the new `BETWEEN ? AND ?` clause
- Passwords hashed with werkzeug (unaffected by this step — no auth logic changes)
- Use CSS variables — never hardcode hex values in any new/changed CSS
- All templates extend `base.html` (unaffected — `profile.html` already does)
- Date parsing/validation happens in `app.py`, not in templates and not in `database/db.py` — the DB layer trusts already-validated `YYYY-MM-DD` strings
- Invalid or malformed date input must never raise an unhandled exception or a raw traceback — fall back to all-time data plus a validation message
- `start_date`/`end_date` are optional on all three DB functions — omitting them must reproduce the exact current (Step 4) query behavior, since other future callers may not filter
- Do not add a JS date-range picker or any client-side filtering — the filter is a plain GET form, consistent with "Vanilla JS only" and keeping this step server-rendered
- Do not touch `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete` — those remain stubs per the roadmap

## Definition of done

- [ ] Visiting `/profile` with no query params shows the same all-time stats, category breakdown, and recent expenses as before this step
- [ ] Visiting `/profile?start_date=2026-08-01&end_date=2026-08-10` shows total spent, expense count, category breakdown, and recent expenses computed only from expenses dated in that inclusive range
- [ ] The date-filter form's inputs are pre-filled with the active `start_date`/`end_date` after applying a filter
- [ ] A "Clear filter" link is visible only when a filter is active, and clicking it returns to the all-time `/profile` view
- [ ] Submitting `start_date` after `end_date` (or a malformed date) does not crash the app — it falls back to all-time data and shows a validation message
- [ ] A date range with zero matching expenses shows "No expenses in this range." instead of an empty chart/list or an error
- [ ] All new/changed queries in `database/db.py` use `?` parameterized placeholders, including the `BETWEEN` clause
- [ ] The app starts and runs without errors on `python app.py` (port 5001)
