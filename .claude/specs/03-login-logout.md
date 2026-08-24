# Spec: Login and Logout

## Overview

This feature implements session-based authentication for Spendly. `GET /login` currently only renders `login.html` — the form posts to `/login` but nothing handles it, and the app has no session logic anywhere. `GET /logout` is a stub that returns a raw string. Since a logout has nothing to log out of without a working login, this step implements both together: `POST /login` verifies credentials and starts a Flask session, and `GET /logout` tears that session down. This unblocks Step 4 (Profile) and any future route that needs to know "who is the current user."

## Depends on

- Step 1 (Database Setup) — requires the `users` table and `get_db()`.
- Step 2 (Registration) — requires `get_user_by_email()` in `database/db.py` and working user creation, so there are real credentials to log in with.

## Routes

- `POST /login` — accepts email + password from `login.html`, verifies the password hash, and on success stores the user's id in the session — public
- `GET /login` — unchanged, still renders `login.html` (route function now accepts both `GET` and `POST`)
- `GET /logout` — clears the session and redirects to the landing page — logged-in (safe to hit while logged out too; it just no-ops)

## Database changes

No new tables or columns. No new functions needed — `get_user_by_email()` (added in Step 2) is sufficient to look up the user for password verification.

## Templates

**Create:** None.

**Modify:**
- `templates/login.html` — change the form's hardcoded `action="/login"` to `action="{{ url_for('login') }}"`; add an `{% if error %}` block matching the pattern already used in `register.html`.
- `templates/base.html` — nav currently always shows "Sign in" / "Get started". Make it conditional on `session.get('user_id')`: logged out shows the existing links, logged in shows a "Log out" link (`url_for('logout')`) instead.

## Files to change

- `app.py` — add `app.secret_key` (required for Flask sessions to work at all); update `login` view to accept `GET` and `POST`; on `POST`, validate credentials with `check_password_hash`, set `session['user_id']` on success or re-render `login.html` with an `error` on failure; implement `logout` to call `session.clear()` and redirect to `landing`
- `templates/login.html` — fix hardcoded form action, add error display
- `templates/base.html` — conditional nav based on session state

## Files to create

None.

## New dependencies

No new dependencies — `werkzeug.security.check_password_hash` pairs with the `generate_password_hash` already used in `database/db.py`; Flask sessions are built into Flask.

## Rules for implementation

- No SQLAlchemy or ORMs
- Parameterised queries only — never f-strings in SQL
- Passwords verified with `werkzeug.security.check_password_hash` — never compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- All DB logic lives in `database/db.py`, never inline in the route
- Use `url_for()` for every internal link/redirect — never hardcode paths
- On failed login (unknown email or wrong password), show one generic error ("Invalid email or password") — never reveal which field was wrong
- `session.clear()` on logout, not just deleting `user_id`, so no stale session data lingers
- Do not implement `GET /profile` or any other stub beyond `/login` and `/logout` — those stay stubs per the roadmap

## Definition of done

- [ ] Submitting `login.html` with a valid registered email/password sets a session and redirects away from `/login`
- [ ] Submitting `login.html` with a wrong password or unknown email re-renders `login.html` with a visible generic error and does not set a session
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/`
- [ ] Visiting `/logout` while logged out does not error — it just redirects to `/`
- [ ] After login, the navbar shows a "Log out" link instead of "Sign in" / "Get started"
- [ ] After logout, the navbar reverts to showing "Sign in" / "Get started"
- [ ] The login form's `action` uses `{{ url_for('login') }}`, not a hardcoded `/login` string
- [ ] `app.py` sets `app.secret_key` so sessions actually persist between requests
- [ ] The app starts and runs without errors on `python app.py` (port 5001)
