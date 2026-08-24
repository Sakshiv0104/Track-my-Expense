# Spec: Add Expense

## Overview

This feature implements `GET/POST /expenses/add`, the first of the three expense-management stubs in the Spendly roadmap (Step 7 of 9). Today a logged-in user can see their expenses on `/profile` but has no way to create one — all data comes from `seed_db()`. This step adds a form page where a logged-in user enters an amount, category, date, and optional description, validates the input server-side, inserts the row into the existing `expenses` table, and redirects back to `/profile` so the new expense shows up immediately in the totals, category breakdown, and recent-expenses list.

## Depends on

- Step 1 (Database Setup) — requires `get_db()`, `init_db()`, and the existing `expenses` table schema.
- Step 3 (Login and Logout) — requires `session['user_id']` to identify the current user and gate access.
- Step 4/5 (Profile Page Design + Date Filter) — the redirect target after a successful add; `get_expense_summary`, `get_category_breakdown`, `get_recent_expenses` are unaffected but will reflect the new row once inserted.

## Routes

- `GET /expenses/add` — renders the add-expense form, pre-filled with today's date — access level: logged-in only (redirect to `/login` if no `session['user_id']`).
- `POST /expenses/add` — validates form fields, inserts the expense for the current user, and redirects to `GET /profile` on success. On validation failure, re-renders the form with an error message and the user's submitted values (except invalid ones, which are cleared) — access level: logged-in only.

Both are handled by a single `add_expense()` view function in `app.py` using `methods=["GET", "POST"]`, replacing the current stub.

## Database changes

No new tables or columns — the existing `expenses` table (`id, user_id, amount, category, date, description, created_at`) already supports this. Add one new function to `database/db.py`:

- `create_expense(user_id, amount, category, date, description)` — parameterized `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`, returns `cursor.lastrowid`, following the same connect/try/finally-close pattern as `create_user`.

## Templates

**Create:**
- `templates/add_expense.html` — extends `base.html`; form with fields for amount, category (select, fixed list matching the CSS category palette: Food, Transport, Bills, Health, Entertainment, Shopping, Other), date (`<input type="date">`, defaulting to today), description (optional text input), and a submit button. Reuses `auth-card` / `form-group` / `form-input` / `btn-submit` / `auth-error` classes from `style.css` — no new global classes needed for the form shell itself.

**Modify:**
- No existing templates change. (`base.html` nav already links only to `/profile`; no new nav entry is in scope for this step.)

## Files to change

- `app.py` — replace the `add_expense()` stub with the real `GET`/`POST` implementation; add server-side validation (amount is a positive number, category is one of the fixed allowed values, date is a valid `YYYY-MM-DD` not in the future, description length capped e.g. 500 chars).
- `database/db.py` — add `create_expense(...)`.

## Files to create

- `templates/add_expense.html`
- `static/css/add_expense.css` — page-specific styles only if the reused `style.css` classes aren't sufficient (e.g. a `<select>` variant); keep additions minimal and scoped to this page.

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterized queries only — no f-strings in SQL.
- All templates extend `base.html`.
- Use CSS variables — never hardcode hex values.
- DB logic lives only in `database/db.py`, never inline in `app.py`.
- Category values must be validated server-side against the fixed allowed list — never trust the submitted string directly in a DB write beyond the parameterized value itself.
- Amount must be validated as a positive numeric value server-side (client-side `type="number"` is not sufficient).
- Redirect (`302`) to `/profile` after a successful `POST` — do not render a template directly from the `POST` handler on success (avoids re-submit-on-refresh).
- Use `abort(403)` or redirect to `/login` for unauthenticated access — do not leak the form to logged-out users.

## Definition of done

- [ ] Visiting `/expenses/add` while logged out redirects to `/login`.
- [ ] Visiting `/expenses/add` while logged in shows a form with amount, category, date (defaulted to today), and description fields.
- [ ] Submitting valid data creates a new row in `expenses` for the current user and redirects to `/profile`.
- [ ] The newly added expense appears in `/profile`'s total spent, category breakdown, and recent-expenses list immediately after redirect.
- [ ] Submitting a negative or non-numeric amount re-renders the form with an error and does not insert a row.
- [ ] Submitting an invalid/unsupported category re-renders the form with an error and does not insert a row.
- [ ] Submitting a missing or malformed date re-renders the form with an error and does not insert a row.
- [ ] Description is optional — submitting without one succeeds and stores `NULL`/empty.
- [ ] All new SQL in `database/db.py` uses `?` placeholders — no string interpolation.
