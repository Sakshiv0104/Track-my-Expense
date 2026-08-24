# Spec: Registration

## Overview

This feature implements the working registration flow for Spendly. The `GET /register` route already renders `register.html`, whose form posts to `/register`, but no server-side handling exists yet — submitting the form currently does nothing. This step adds the `POST /register` logic: validating input, checking for duplicate emails, hashing the password with `werkzeug`, and inserting the new user into the `users` table created in Step 1. This is the first piece of real user-facing functionality built on top of the database layer, and it unblocks login/session work in later steps.

## Depends on

- Step 1 (Database Setup) — requires the `users` table, `get_db()`, and `PRAGMA foreign_keys = ON` to already exist in `database/db.py`.

## Routes

- `POST /register` — accepts the registration form (name, email, password), validates it, hashes the password, and creates the user — public
- `GET /register` — unchanged, still renders `register.html` (now the same route function will accept both `GET` and `POST`)

## Database changes

No new tables or columns — the `users` table from Step 1 already has everything needed (`name`, `email`, `password_hash`).

Two new functions must be added to `database/db.py` (never inline in `app.py`):

- `get_user_by_email(email)` — runs a parameterized `SELECT` and returns the matching row or `None`
- `create_user(name, email, password_hash)` — runs a parameterized `INSERT` into `users` and returns the new user's id

## Templates

**Create:** None — `register.html` already exists.

**Modify:**
- `templates/register.html` — change the form's hardcoded `action="/register"` to `action="{{ url_for('register') }}"` per the no-hardcoded-URLs rule. Keep the existing `{% if error %}` block for validation/duplicate-email messages.

## Files to change

- `app.py` — update the `register` view to accept `GET` and `POST`; on `POST`, validate the form, call the new `database/db.py` helpers, and either re-render `register.html` with an `error` on failure or redirect to `/login` on success
- `templates/register.html` — fix hardcoded form action to use `url_for()`
- `database/db.py` — add `get_user_by_email()` and `create_user()`

## Files to create

None.

## New dependencies

No new dependencies — `werkzeug.security.generate_password_hash` is already used in `database/db.py`.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` before storage — never store plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic lives in `database/db.py`, never inline in the route
- Use `url_for()` for every internal link/redirect — never hardcode paths
- Validate on the server even though the form has `required`/`type="email"` attributes client-side (name non-empty, valid email format, password minimum length of 8 to match the placeholder text)
- Reject duplicate emails with a friendly error re-rendered on the form (via `get_user_by_email()`), not a raw `IntegrityError` traceback
- On success, redirect (302) to `GET /login` — do not start a session or log the user in (session/login logic is out of scope for this step)

## Definition of done

- [ ] Submitting the registration form with a new name/email/password creates a row in `users` with a hashed (not plaintext) password
- [ ] After a successful registration, the browser is redirected to `/login`
- [ ] Submitting the form with an email that already exists in `users` re-renders `register.html` with a visible error and does not create a duplicate row
- [ ] Submitting the form with a password under 8 characters re-renders `register.html` with a visible error and does not create a row
- [ ] Submitting the form with a missing/invalid field re-renders `register.html` with a visible error
- [ ] The registration form's `action` uses `{{ url_for('register') }}`, not a hardcoded `/register` string
- [ ] All new queries in `database/db.py` use `?` parameterized placeholders
- [ ] The app starts and runs without errors on `python app.py` (port 5001)
