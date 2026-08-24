# Spec: Delete Expense

## Overview

This feature implements `GET/POST /expenses/<id>/delete`, the last of the three expense-management stubs in the Spendly roadmap (Step 9 of 9). A logged-in user can already add (`/expenses/add`) and correct (`/expenses/<id>/edit`) expenses, but has no way to remove one that was entered by mistake or is no longer relevant. This step adds a confirmation page reachable from each row in the profile's "Recent expenses" list — `GET` shows a "are you sure?" page for the expense, `POST` permanently deletes it and redirects back to `/profile`. Access is scoped so a user can only delete their own expenses, matching the ownership rules already established for edit.

## Depends on

- Step 1 (Database Setup) — requires `get_db()`, `init_db()`, and the existing `expenses` table schema.
- Step 3 (Login and Logout) — requires `session['user_id']` to identify the current user and gate access.
- Step 4/5 (Profile Page Design + Date Filter) — the redirect target after a successful delete, and the "Recent expenses" list that links into this feature.
- Step 8 (Edit Expense) — reuses the same ownership-check pattern (`get_expense_by_id`) and template conventions established there.

## Routes

- `GET /expenses/<id>/delete` — fetches the expense by `id`, verifies it belongs to `session['user_id']`, and renders a confirmation page showing the expense's amount, category, date, and description with a "Delete" button and a "Cancel" link back to `/profile` — access level: logged-in only (redirect to `/login` if no `session['user_id']`); `404` if the expense doesn't exist or belongs to a different user. Nothing is deleted on `GET`.
- `POST /expenses/<id>/delete` — re-verifies ownership, deletes the expense row, and redirects to `GET /profile` on success. Same ownership check as `GET` — access level: logged-in only.

Both are handled by a single `delete_expense(id)` view function in `app.py` using `methods=["GET", "POST"]`, replacing the current stub.

## Database changes

No new tables or columns — the existing `expenses` table already supports this. Add one new function to `database/db.py`:

- `delete_expense(expense_id, user_id)` — parameterized `DELETE FROM expenses WHERE id = ? AND user_id = ?`, following the same connect/try/finally-close pattern as `update_expense`. The `WHERE ... AND user_id = ?` clause is a second ownership guard even if the route check were ever bypassed.

This reuses the existing `get_expense_by_id(expense_id, user_id)` from Step 8 for the ownership check on `GET` and `POST` — no new read function needed.

## Templates

**Create:**
- `templates/delete_expense.html` — extends `base.html`; a confirmation card showing the expense's category, amount, date, and description, a `POST` form to `url_for('delete_expense', id=expense['id'])` with a submit button styled as a destructive action, and a "Cancel" link back to `url_for('profile')`. Reuses `auth-card` / `btn-primary` conventions from `style.css`; a new `btn-danger` class may be added to `style.css` (CSS variables only, no hardcoded hex) for the destructive button.

**Modify:**
- `templates/profile.html` — add a "Delete" link next to the existing "Edit" link in each `<li class="recent-row">`'s `.recent-side`, pointing to `url_for('delete_expense', id=expense['id'])`.

## Files to change

- `app.py` — replace the `delete_expense(id)` stub with the real `GET`/`POST` implementation; add the ownership check (404 on missing/not-owned expense).
- `database/db.py` — add `delete_expense(expense_id, user_id)`.
- `templates/profile.html` — add the delete link to each recent-expense row.
- `static/css/style.css` — add a `btn-danger` class if a destructive-styled button is needed (CSS variables only).

## Files to create

- `templates/delete_expense.html`

## New dependencies

No new dependencies.

## Rules for implementation

- No SQLAlchemy or ORMs.
- Parameterised queries only — no f-strings in SQL.
- Passwords hashed with werkzeug.
- Use CSS variables — never hardcode hex values.
- All templates extend `base.html`.
- DB logic lives only in `database/db.py`, never inline in `app.py`.
- The actual deletion must only ever happen on `POST`, never on `GET` — a `GET` request must be side-effect-free so a browser prefetch or accidental link click can't delete data.
- A user must never be able to view or delete another user's expense — enforce ownership both in the route (404 if not found/owned) and in the SQL `WHERE` clause of `delete_expense`.
- Redirect (`302`) to `/profile` after a successful `POST` — do not render a template directly from the `POST` handler on success.
- Use `abort(404)` for an expense that doesn't exist or isn't owned by the current user; redirect to `/login` for unauthenticated access.

## Definition of done

- [ ] Visiting `/expenses/<id>/delete` while logged out redirects to `/login`.
- [ ] Visiting `/expenses/<id>/delete` for an expense owned by another user returns a 404.
- [ ] Visiting `/expenses/<id>/delete` for a non-existent id returns a 404.
- [ ] Visiting `/expenses/<id>/delete` while logged in as the owner shows a confirmation page with that expense's amount, category, date, and description.
- [ ] Visiting `/expenses/<id>/delete` via `GET` does not delete the expense — it still appears in `/profile` afterward.
- [ ] Submitting the confirmation form (`POST`) deletes the expense and redirects to `/profile`.
- [ ] The deleted expense no longer appears in `/profile`'s total spent, category breakdown, or recent-expenses list immediately after redirect.
- [ ] `POST /expenses/<id>/delete` for an expense owned by another user returns a 404 and does not delete the row.
- [ ] Each row in the profile's "Recent expenses" list links to the correct expense's delete-confirmation page.
- [ ] All new SQL in `database/db.py` uses `?` placeholders — no string interpolation.
