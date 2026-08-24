# Spec: Edit Expense

## Overview

This feature implements `GET/POST /expenses/<id>/edit`, the second of the three expense-management stubs in the Spendly roadmap (Step 8 of 9). Today a logged-in user can add expenses (`/expenses/add`) and view them on `/profile`, but has no way to correct a mistake — a wrong amount, category, date, or typo in the description — short of leaving bad data in place. This step adds an edit page, reachable from each row in the profile's "Recent expenses" list, that pre-fills a form with the existing expense's values, validates and applies changes, and redirects back to `/profile` on success. Access is scoped so a user can only edit their own expenses.

## Depends on

- Step 1 (Database Setup) — requires `get_db()`, `init_db()`, and the existing `expenses` table schema.
- Step 3 (Login and Logout) — requires `session['user_id']` to identify the current user and gate access.
- Step 4/5 (Profile Page Design + Date Filter) — the redirect target after a successful edit, and the "Recent expenses" list that links into this feature.
- Step 7 (Add Expense) — reuses the same form validation approach (`parse_expense_form`) and template conventions established there.

## Routes

- `GET /expenses/<id>/edit` — fetches the expense by `id`, verifies it belongs to `session['user_id']`, and renders an edit form pre-filled with its current amount, category, date, and description — access level: logged-in only (redirect to `/login` if no `session['user_id']`); `404` if the expense doesn't exist or belongs to a different user.
- `POST /expenses/<id>/edit` — validates form fields (same rules as add-expense), updates the expense row for the current user, and redirects to `GET /profile` on success. On validation failure, re-renders the form with an error message and the user's submitted values (except invalid ones, which are cleared). Same ownership check as `GET` — access level: logged-in only.

Both are handled by a single `edit_expense(id)` view function in `app.py` using `methods=["GET", "POST"]`, replacing the current stub.

## Database changes

No new tables or columns — the existing `expenses` table (`id, user_id, amount, category, date, description, created_at`) already supports this. Add two new functions to `database/db.py`:

- `get_expense_by_id(expense_id, user_id)` — parameterized `SELECT * FROM expenses WHERE id = ? AND user_id = ?`, returns the row or `None`, following the same connect/try/finally-close pattern as `get_user_by_id`. The `user_id` filter is what enforces ownership at the data layer, not just in the route.
- `update_expense(expense_id, user_id, amount, category, date, description)` — parameterized `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`, following the same connect/try/finally-close pattern as `create_expense`. Returns nothing (or rowcount, if useful to detect a no-op update); the `WHERE ... AND user_id = ?` clause is a second ownership guard even if the route check were ever bypassed.

## Templates

**Create:**
- `templates/edit_expense.html` — extends `base.html`; same form shell as `add_expense.html` (amount, category select, date, description) but pre-filled with the existing expense's values and posting to `url_for('edit_expense', id=expense['id'])`. Reuses `auth-card` / `form-group` / `form-input` / `btn-submit` / `auth-error` classes from `style.css` — no new global classes needed for the form shell itself.

**Modify:**
- `templates/profile.html` — add an "Edit" link/icon to each `<li class="recent-row">` in the "Recent expenses" list, pointing to `url_for('edit_expense', id=expense['id'])`.

## Files to change

- `app.py` — replace the `edit_expense(id)` stub with the real `GET`/`POST` implementation; reuse `parse_expense_form` for validation; add the ownership check (404 on missing/not-owned expense).
- `database/db.py` — add `get_expense_by_id(...)` and `update_expense(...)`.
- `templates/profile.html` — add the edit link to each recent-expense row.

## Files to create

- `templates/edit_expense.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only — no f-strings in SQL.
- Passwords hashed with werkzeug.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- DB logic lives only in `database/db.py`, never inline in `app.py`.
- Category values must be validated server-side against the fixed allowed list, same as add-expense.
- Amount must be validated as a positive numeric value server-side.
- A user must never be able to view or modify another user's expense — enforce ownership both in the route (404 if not found/owned) and in the SQL `WHERE` clause of `update_expense`.
- Redirect (`302`) to `/profile` after a successful `POST` — do not render a template directly from the `POST` handler on success.
- Use `abort(404)` for an expense that doesn't exist or isn't owned by the current user; redirect to `/login` for unauthenticated access.

## Definition of done

- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`.
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by another user returns a 404.
- [ ] Visiting `/expenses/<id>/edit` for a non-existent id returns a 404.
- [ ] Visiting `/expenses/<id>/edit` while logged in as the owner shows a form pre-filled with that expense's current amount, category, date, and description.
- [ ] Submitting valid changes updates the existing row (not a new one) and redirects to `/profile`.
- [ ] The updated values appear in `/profile`'s total spent, category breakdown, and recent-expenses list immediately after redirect.
- [ ] Submitting a negative or non-numeric amount re-renders the form with an error and does not modify the row.
- [ ] Submitting an invalid/unsupported category re-renders the form with an error and does not modify the row.
- [ ] Submitting a missing or malformed date re-renders the form with an error and does not modify the row.
- [ ] Each row in the profile's "Recent expenses" list links to the correct expense's edit page.
- [ ] All new SQL in `database/db.py` uses `?` placeholders — no string interpolation.
