"""Tests for the Edit Expense feature (spec: .claude/specs/08-edit-expense.md).

Covers, mapped to the spec's Definition of done:
- GET/POST /expenses/<id>/edit while logged out redirects to /login
  (DoD item 1)
- GET/POST /expenses/<id>/edit for an expense owned by another user returns
  404 (DoD item 2)
- GET/POST /expenses/<id>/edit for a non-existent id returns 404
  (DoD item 3)
- GET while logged in as the owner pre-fills the form with the expense's
  current amount, category, date, and description (DoD item 4)
- Valid POST updates the existing row (not a new one) and redirects to
  /profile (DoD item 5)
- Updated values appear in /profile's total spent, category breakdown, and
  recent-expenses list immediately after redirect (DoD item 6)
- Negative/non-numeric amount re-renders the form with an error and does
  not modify the row (DoD item 7)
- Invalid/unsupported category re-renders the form with an error and does
  not modify the row (DoD item 8)
- Missing/malformed date re-renders the form with an error and does not
  modify the row (DoD item 9)
- Each row in the profile's "Recent expenses" list links to the correct
  expense's edit page (DoD item 10)
- Parameterized SQL (DoD item 11) is not directly HTTP-testable; covered
  indirectly by the ownership-enforcement tests against
  database/db.py's get_expense_by_id / update_expense (the WHERE ... AND
  user_id = ? clause the spec calls out as a second ownership guard).

Also covers direct database/db.py unit tests for get_expense_by_id and
update_expense, since the spec's "Database changes" section documents
these as new, contract-bearing functions.
"""

from datetime import datetime

from werkzeug.security import generate_password_hash

from database import db as db_module


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _create_user(email="editexpense@example.com"):
    return db_module.create_user(
        "Edit Expense Tester", email, generate_password_hash("password123")
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


def _valid_payload(**overrides):
    payload = {
        "amount": "99.99",
        "category": "Bills",
        "date": _today(),
        "description": "Updated description",
    }
    payload.update(overrides)
    return payload


def _edit_url(expense_id):
    return f"/expenses/{expense_id}/edit"


# --------------------------------------------------------------------------
# DoD 1: logged-out access redirects to /login (GET and POST)
# --------------------------------------------------------------------------

def test_get_edit_expense_redirects_when_logged_out(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)

    response = client.get(_edit_url(expense_id))

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_edit_expense_redirects_when_logged_out(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)

    response = client.post(_edit_url(expense_id), data=_valid_payload())

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_edit_expense_while_logged_out_does_not_modify_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")

    client.post(_edit_url(expense_id), data=_valid_payload())

    row = _expense_row(expense_id)
    assert float(row["amount"]) == 42.50
    assert row["category"] == "Food"


# --------------------------------------------------------------------------
# DoD 2: expense owned by another user returns 404 (GET and POST), and the
# row is left untouched
# --------------------------------------------------------------------------

def test_get_edit_expense_owned_by_another_user_returns_404(client):
    owner_id = _create_user("owner@example.com")
    other_id = _create_user("other@example.com")
    expense_id = _create_expense(owner_id)
    _login(client, other_id)

    response = client.get(_edit_url(expense_id))

    assert response.status_code == 404


def test_post_edit_expense_owned_by_another_user_returns_404(client):
    owner_id = _create_user("owner2@example.com")
    other_id = _create_user("other2@example.com")
    expense_id = _create_expense(owner_id)
    _login(client, other_id)

    response = client.post(_edit_url(expense_id), data=_valid_payload())

    assert response.status_code == 404


def test_post_edit_expense_owned_by_another_user_does_not_modify_row(client):
    owner_id = _create_user("owner3@example.com")
    other_id = _create_user("other3@example.com")
    expense_id = _create_expense(owner_id, amount=42.50, category="Food")
    _login(client, other_id)

    client.post(_edit_url(expense_id), data=_valid_payload())

    row = _expense_row(expense_id)
    assert float(row["amount"]) == 42.50
    assert row["category"] == "Food"


# --------------------------------------------------------------------------
# DoD 3: non-existent id returns 404 (GET and POST)
# --------------------------------------------------------------------------

def test_get_edit_expense_nonexistent_id_returns_404(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.get(_edit_url(999999))

    assert response.status_code == 404


def test_post_edit_expense_nonexistent_id_returns_404(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(_edit_url(999999), data=_valid_payload())

    assert response.status_code == 404


# --------------------------------------------------------------------------
# DoD 4: GET while logged in as the owner pre-fills the form
# --------------------------------------------------------------------------

def test_get_edit_expense_prefills_form_with_current_values(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id,
        amount=42.50,
        category="Food",
        date="2026-08-10",
        description="Lunch with team",
    )
    _login(client, user_id)

    response = client.get(_edit_url(expense_id))
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html
    assert 'name="category"' in html
    assert 'name="date"' in html
    assert 'name="description"' in html
    assert "42.5" in html
    assert "2026-08-10" in html
    assert "Lunch with team" in html


# --------------------------------------------------------------------------
# DoD 5: valid POST updates the existing row (not a new one) and redirects
# --------------------------------------------------------------------------

def test_post_valid_data_redirects_to_profile(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id)
    _login(client, user_id)

    response = client.post(_edit_url(expense_id), data=_valid_payload())

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_valid_data_updates_existing_row_not_a_new_one(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", description="Lunch"
    )
    _login(client, user_id)

    client.post(
        _edit_url(expense_id),
        data=_valid_payload(
            amount="99.99",
            category="Bills",
            date=_today(),
            description="Updated description",
        ),
    )

    rows = _expense_rows_for(user_id)
    assert len(rows) == 1  # no new row was inserted
    row = rows[0]
    assert row["id"] == expense_id  # same row, updated in place
    assert float(row["amount"]) == 99.99
    assert row["category"] == "Bills"
    assert row["description"] == "Updated description"


def test_post_valid_data_does_not_modify_other_users_expenses(client):
    user_a = _create_user("a2@example.com")
    user_b = _create_user("b2@example.com")
    expense_a = _create_expense(user_a, amount=10.00, category="Food")
    expense_b = _create_expense(user_b, amount=20.00, category="Transport")
    _login(client, user_a)

    client.post(_edit_url(expense_a), data=_valid_payload())

    row_b = _expense_row(expense_b)
    assert float(row_b["amount"]) == 20.00
    assert row_b["category"] == "Transport"


# --------------------------------------------------------------------------
# DoD 6: updated values reflected in /profile's totals, category breakdown,
# and recent-expenses list immediately after redirect
# --------------------------------------------------------------------------

def test_updated_expense_reflected_in_profile_after_edit(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", description="Lunch with team"
    )
    _login(client, user_id)

    client.post(
        _edit_url(expense_id),
        data=_valid_payload(
            amount="99.99",
            category="Bills",
            date=_today(),
            description="Electricity bill",
        ),
    )

    html = client.get("/profile").get_data(as_text=True)

    assert "99.99" in html
    assert "Bills" in html
    assert "Electricity bill" in html


def test_updated_expense_total_spent_reflects_new_amount(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    client.post(
        _edit_url(expense_id),
        data=_valid_payload(amount="100.00", category="Food"),
    )

    total_spent, expense_count = db_module.get_expense_summary(user_id)
    assert total_spent == 100.00
    assert expense_count == 1


# --------------------------------------------------------------------------
# DoD 7: negative or non-numeric amount re-renders form, no modification
# --------------------------------------------------------------------------

def test_post_negative_amount_rerenders_form_without_modifying_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    response = client.post(
        _edit_url(expense_id), data=_valid_payload(amount="-10.00")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html
    row = _expense_row(expense_id)
    assert float(row["amount"]) == 42.50
    assert row["category"] == "Food"


def test_post_non_numeric_amount_rerenders_form_without_modifying_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    response = client.post(
        _edit_url(expense_id), data=_valid_payload(amount="not-a-number")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html
    row = _expense_row(expense_id)
    assert float(row["amount"]) == 42.50


# --------------------------------------------------------------------------
# DoD 8: invalid/unsupported category re-renders form, no modification
# --------------------------------------------------------------------------

def test_post_invalid_category_rerenders_form_without_modifying_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=42.50, category="Food")
    _login(client, user_id)

    response = client.post(
        _edit_url(expense_id), data=_valid_payload(category="Groceries")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="category"' in html
    row = _expense_row(expense_id)
    assert row["category"] == "Food"


# --------------------------------------------------------------------------
# DoD 9: missing or malformed date re-renders form, no modification
# --------------------------------------------------------------------------

def test_post_missing_date_rerenders_form_without_modifying_row(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", date="2026-08-10"
    )
    _login(client, user_id)

    payload = _valid_payload()
    del payload["date"]

    response = client.post(_edit_url(expense_id), data=payload)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="date"' in html
    row = _expense_row(expense_id)
    assert row["date"] == "2026-08-10"


def test_post_malformed_date_rerenders_form_without_modifying_row(client):
    user_id = _create_user()
    expense_id = _create_expense(
        user_id, amount=42.50, category="Food", date="2026-08-10"
    )
    _login(client, user_id)

    response = client.post(
        _edit_url(expense_id), data=_valid_payload(date="not-a-date")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="date"' in html
    row = _expense_row(expense_id)
    assert row["date"] == "2026-08-10"


# --------------------------------------------------------------------------
# DoD 10: each recent-expenses row links to the correct expense's edit page
# --------------------------------------------------------------------------

def test_recent_expenses_rows_link_to_correct_edit_page(client):
    user_id = _create_user()
    expense_1 = _create_expense(
        user_id, amount=10.00, category="Food", date="2026-08-01"
    )
    expense_2 = _create_expense(
        user_id, amount=20.00, category="Transport", date="2026-08-02"
    )
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    assert _edit_url(expense_1) in html
    assert _edit_url(expense_2) in html


# --------------------------------------------------------------------------
# Database changes: get_expense_by_id / update_expense contracts, including
# the ownership guard enforced via "WHERE ... AND user_id = ?"
# (DoD item 11 -- parameterized SQL -- is exercised indirectly here, since
# it isn't directly observable over HTTP.)
# --------------------------------------------------------------------------

def test_get_expense_by_id_returns_row_for_correct_owner(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=15.00, category="Transport")

    row = db_module.get_expense_by_id(expense_id, user_id)

    assert row is not None
    assert row["id"] == expense_id
    assert float(row["amount"]) == 15.00


def test_get_expense_by_id_returns_none_for_wrong_owner(client):
    owner_id = _create_user("owner4@example.com")
    other_id = _create_user("other4@example.com")
    expense_id = _create_expense(owner_id, amount=15.00, category="Transport")

    row = db_module.get_expense_by_id(expense_id, other_id)

    assert row is None


def test_get_expense_by_id_returns_none_for_nonexistent_id(client):
    user_id = _create_user()

    row = db_module.get_expense_by_id(999999, user_id)

    assert row is None


def test_update_expense_updates_matching_row(client):
    user_id = _create_user()
    expense_id = _create_expense(user_id, amount=15.00, category="Transport")

    db_module.update_expense(
        expense_id=expense_id,
        user_id=user_id,
        amount=30.00,
        category="Bills",
        date=_today(),
        description="Updated via db call",
    )

    row = _expense_row(expense_id)
    assert float(row["amount"]) == 30.00
    assert row["category"] == "Bills"
    assert row["description"] == "Updated via db call"


def test_update_expense_is_a_no_op_when_user_id_does_not_match(client):
    """The WHERE ... AND user_id = ? clause is a second ownership guard --
    calling update_expense with the wrong user_id must not modify the row,
    even if a route-level check were bypassed."""
    owner_id = _create_user("owner5@example.com")
    other_id = _create_user("other5@example.com")
    expense_id = _create_expense(owner_id, amount=15.00, category="Transport")

    db_module.update_expense(
        expense_id=expense_id,
        user_id=other_id,
        amount=999.00,
        category="Bills",
        date=_today(),
        description="Should not apply",
    )

    row = _expense_row(expense_id)
    assert float(row["amount"]) == 15.00
    assert row["category"] == "Transport"
