"""Tests for the Delete Expense feature (spec: .claude/specs/09-delete-expense.md).

Covers, mapped to the spec's Definition of done:
- GET /expenses/<id>/delete while logged out redirects to /login
  (DoD item 1)
- GET /expenses/<id>/delete for an expense owned by another user returns
  404 (DoD item 2)
- GET /expenses/<id>/delete for a non-existent id returns 404 (DoD item 3)
- GET while logged in as the owner shows a confirmation page with that
  expense's amount, category, date, and description (DoD item 4)
- GET does not delete the expense -- it still appears in /profile
  afterward (DoD item 5)
- POST deletes the expense and redirects (302) to /profile (DoD item 6)
- The deleted expense no longer appears in /profile's total spent,
  category breakdown, or recent-expenses list immediately after redirect
  (DoD item 7)
- POST for an expense owned by another user returns 404 and does not
  delete the row (DoD item 8)
- Each row in the profile's "Recent expenses" list links to the correct
  expense's delete-confirmation page (DoD item 9)
- All new SQL in database/db.py uses ? placeholders -- no string
  interpolation (DoD item 10). Exercised both via source inspection of
  database/db.py's delete_expense (the project's existing convention,
  since this isn't independently observable over HTTP) and behaviorally
  via the ownership-guard unit tests below.

Also covers a POST /expenses/<id>/delete-while-logged-out guard (auth must
be checked before any deletion happens), and direct database/db.py unit
tests for delete_expense, since the spec's "Database changes" section
documents it as a new, contract-bearing function.
"""

import inspect
from datetime import datetime

from werkzeug.security import generate_password_hash

from database import db as db_module


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _create_user(email="deleteexpense@example.com"):
    return db_module.create_user(
        "Delete Expense Tester", email, generate_password_hash("password123")
    )


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _create_expense(
    user_id, amount=42.50, category="Food", date=None, description="Lunch"
):
    return db_module.create_expense(
        user_id=user_id,
        amount=amount,
        category=category,
        date=date or _today(),
        description=description,
    )


def _expense_row(expense_id):
    conn = db_module.get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ?", (expense_id,)
        ).fetchone()
    finally:
        conn.close()


def _expense_rows_for(user_id):
    conn = db_module.get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchall()
    finally:
        conn.close()


def _today():
    return datetime.now().strftime("%Y-%m-%d")


def _delete_url(expense_id):
    return f"/expenses/{expense_id}/delete"


# --------------------------------------------------------------------------
# DoD 1: logged-out access redirects to /login
# --------------------------------------------------------------------------

def test_get_delete_expense_redirects_when_logged_out(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)

    response = client.get(_delete_url(expense_id))

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_delete_expense_redirects_when_logged_out(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)

    response = client.post(_delete_url(expense_id))

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_delete_expense_while_logged_out_does_not_delete_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)

    client.post(_delete_url(expense_id))

    row = _expense_row(expense_id)
    assert row is not None


# --------------------------------------------------------------------------
# DoD 2: expense owned by another user returns 404 (GET)
# --------------------------------------------------------------------------

def test_get_delete_expense_owned_by_another_user_returns_404(client):
    owner_id = _create_user("owner@example.com")
    other_id = _create_user("other@example.com")
    expense_id = _create_expense(owner_id)
    _login(client, other_id)

    response = client.get(_delete_url(expense_id))

    assert response.status_code == 404


# --------------------------------------------------------------------------
# DoD 3: non-existent id returns 404
# --------------------------------------------------------------------------

def test_get_delete_expense_nonexistent_id_returns_404(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.get(_delete_url(999999))

    assert response.status_code == 404


def test_post_delete_expense_nonexistent_id_returns_404(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(_delete_url(999999))

    assert response.status_code == 404


# --------------------------------------------------------------------------
# DoD 4: GET while logged in as the owner shows a confirmation page with
# the expense's amount, category, date, and description
# --------------------------------------------------------------------------

def test_get_delete_expense_shows_confirmation_page_with_expense_details(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id,
        amount=42.50,
        category="Food",
        date="2026-08-10",
        description="Lunch with team",
    )
    _login(client, user_id)

    response = client.get(_delete_url(expense_id))
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "42.5" in html
    assert "Food" in html
    assert "2026-08-10" in html
    assert "Lunch with team" in html


# --------------------------------------------------------------------------
# DoD 5: GET does not delete the expense -- it still appears in /profile
# afterward
# --------------------------------------------------------------------------

def test_get_delete_expense_is_side_effect_free(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", description="Lunch"
    )
    _login(client, user_id)

    client.get(_delete_url(expense_id))

    row = _expense_row(expense_id)
    assert row is not None
    assert float(row["amount"]) == 42.50

    profile_html = client.get("/profile").get_data(as_text=True)
    assert "Lunch" in profile_html


# --------------------------------------------------------------------------
# DoD 6: POST deletes the expense and redirects (302) to /profile
# --------------------------------------------------------------------------

def test_post_delete_expense_redirects_to_profile(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)
    _login(client, user_id)

    response = client.post(_delete_url(expense_id))

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_delete_expense_removes_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)
    _login(client, user_id)

    client.post(_delete_url(expense_id))

    row = _expense_row(expense_id)
    assert row is None


def test_post_delete_expense_does_not_render_template_directly(client):
    """Spec: 'do not render a template directly from the POST handler on
    success' -- a successful POST must be a redirect, not a 200 with HTML."""
    user_id = _create_user()
    expense_id = _create_expense(user_id)
    _login(client, user_id)

    response = client.post(_delete_url(expense_id))

    assert response.status_code == 302


# --------------------------------------------------------------------------
# DoD 7: deleted expense no longer appears in /profile's total spent,
# category breakdown, or recent-expenses list immediately after redirect
# --------------------------------------------------------------------------

def test_deleted_expense_removed_from_profile_total_spent(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    client.post(_delete_url(expense_id))

    total_spent, expense_count = db_module.get_expense_summary(user_id)
    assert total_spent == 0
    assert expense_count == 0


def test_deleted_expense_removed_from_category_breakdown(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    client.post(_delete_url(expense_id))

    breakdown = db_module.get_category_breakdown(user_id)
    categories = [row["category"] for row in breakdown]
    assert "Food" not in categories


def test_deleted_expense_removed_from_profile_recent_list(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", description="Lunch with team"
    )
    _login(client, user_id)

    client.post(_delete_url(expense_id))
    html = client.get("/profile").get_data(as_text=True)

    assert "Lunch with team" not in html
    assert _delete_url(expense_id) not in html


def test_deleted_expense_does_not_affect_other_remaining_expenses(client):
    user_id = _create_user()
    keep_id = _create_expense(
        user_id, amount=10.00, category="Transport", description="Bus fare"
    )
    delete_id = _create_expense(
        user_id, amount=42.50, category="Food", description="Lunch"
    )
    _login(client, user_id)

    client.post(_delete_url(delete_id))
    html = client.get("/profile").get_data(as_text=True)

    assert "Bus fare" in html
    row = _expense_row(keep_id)
    assert row is not None
    assert float(row["amount"]) == 10.00


# --------------------------------------------------------------------------
# DoD 8: POST for an expense owned by another user returns 404 and does
# not delete the row
# --------------------------------------------------------------------------

def test_post_delete_expense_owned_by_another_user_returns_404(client):
    owner_id = _create_user("owner2@example.com")
    other_id = _create_user("other2@example.com")
    expense_id = _create_expense(owner_id)
    _login(client, other_id)

    response = client.post(_delete_url(expense_id))

    assert response.status_code == 404


def test_post_delete_expense_owned_by_another_user_does_not_delete_row(client):
    owner_id = _create_user("owner3@example.com")
    other_id = _create_user("other3@example.com")
    expense_id = _create_expense(owner_id, amount=42.50, category="Food")
    _login(client, other_id)

    client.post(_delete_url(expense_id))

    row = _expense_row(expense_id)
    assert row is not None
    assert float(row["amount"]) == 42.50


# --------------------------------------------------------------------------
# DoD 9: each row in the profile's "Recent expenses" list links to the
# correct expense's delete-confirmation page
# --------------------------------------------------------------------------

def test_recent_expenses_rows_link_to_correct_delete_page(client):
    user_id = _create_user()
    expense_1 = _create_expense(
        user_id, amount=10.00, category="Food", date="2026-08-01"
    )
    expense_2 = _create_expense(
        user_id, amount=20.00, category="Transport", date="2026-08-02"
    )
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    assert _delete_url(expense_1) in html
    assert _delete_url(expense_2) in html


# --------------------------------------------------------------------------
# DoD 10: all new SQL in database/db.py uses ? placeholders -- no string
# interpolation. Follows the project's existing convention (see
# test_08-edit-expense.py) of exercising this behaviorally through the
# ownership-guard tests, plus a source-inspection check on delete_expense
# specifically since it is the new function this spec introduces.
# --------------------------------------------------------------------------

def test_delete_expense_source_uses_parameterized_placeholders():
    source = inspect.getsource(db_module.delete_expense)

    assert "?" in source
    # No f-string/format-based interpolation of expense_id or user_id into
    # the SQL string.
    assert "f\"" not in source
    assert "f'" not in source
    assert ".format(" not in source
    assert "%s" not in source


# --------------------------------------------------------------------------
# Database changes: delete_expense(expense_id, user_id) contract, including
# the ownership guard enforced via "WHERE ... AND user_id = ?"
# --------------------------------------------------------------------------

def test_delete_expense_deletes_matching_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=15.00, category="Transport")

    db_module.delete_expense(expense_id, user_id)

    row = _expense_row(expense_id)
    assert row is None


def test_delete_expense_is_a_no_op_when_user_id_does_not_match(client):
    """The WHERE ... AND user_id = ? clause is a second ownership guard --
    calling delete_expense with the wrong user_id must not delete the row,
    even if a route-level check were bypassed."""
    owner_id = _create_user("owner4@example.com")
    other_id = _create_user("other4@example.com")
    expense_id = _create_expense(owner_id, amount=15.00, category="Transport")

    db_module.delete_expense(expense_id, other_id)

    row = _expense_row(expense_id)
    assert row is not None
    assert float(row["amount"]) == 15.00


def test_delete_expense_nonexistent_id_does_not_raise(client):
    user_id = _create_user()

    # Should be a no-op, not an error.
    db_module.delete_expense(999999, user_id)

    rows = _expense_rows_for(user_id)
    assert rows == []
