"""Tests for the Add Expense feature (spec: .claude/specs/07-add-expense.md).

Covers:
- GET /expenses/add redirects logged-out users to /login (DoD item 1)
- GET /expenses/add while logged in shows the form with amount, category,
  date (defaulted to today), and description fields (DoD item 2)
- POST with valid data creates a row in `expenses` for the current user and
  redirects to /profile (DoD item 3)
- The newly added expense appears in /profile's total, category breakdown,
  and recent-expenses list immediately after redirect (DoD item 4)
- Negative/non-numeric amount re-renders the form and does not insert a row
  (DoD item 5)
- Invalid/unsupported category re-renders the form and does not insert a row
  (DoD item 6)
- Missing/malformed date re-renders the form and does not insert a row
  (DoD item 7)
- Description is optional -- omitting it succeeds and stores NULL/empty
  (DoD item 8)
- Access is gated for POST as well as GET (Routes: access level logged-in
  only for both GET and POST)
- Extra coverage from "Rules for implementation": date must not be in the
  future; description is capped in length.
"""

from datetime import datetime, timedelta

from werkzeug.security import generate_password_hash

from database import db as db_module


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _create_user(email="addexpense@example.com"):
    return db_module.create_user(
        "Add Expense Tester", email, generate_password_hash("password123")
    )


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


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
        "amount": "42.50",
        "category": "Food",
        "date": _today(),
        "description": "Lunch with team",
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------
# DoD 1: logged-out access redirects to /login (GET and POST)
# --------------------------------------------------------------------------

def test_get_add_expense_redirects_when_logged_out(client):
    response = client.get("/expenses/add")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_redirects_when_logged_out(client):
    response = client.post("/expenses/add", data=_valid_payload())
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_post_add_expense_while_logged_out_creates_no_row(client):
    user_id = _create_user()
    client.post("/expenses/add", data=_valid_payload())

    rows = _expense_rows_for(user_id)
    assert len(rows) == 0


# --------------------------------------------------------------------------
# DoD 2: GET while logged in shows the form with the required fields,
# date defaulted to today
# --------------------------------------------------------------------------

def test_get_add_expense_logged_in_returns_200_with_form_fields(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.get("/expenses/add")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html
    assert 'name="category"' in html
    assert 'name="date"' in html
    assert 'name="description"' in html


def test_get_add_expense_date_field_defaults_to_today(client):
    user_id = _create_user()
    _login(client, user_id)

    html = client.get("/expenses/add").get_data(as_text=True)

    assert f'value="{_today()}"' in html


# --------------------------------------------------------------------------
# DoD 3: valid POST creates a row for the current user and redirects
# --------------------------------------------------------------------------

def test_post_valid_data_redirects_to_profile(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post("/expenses/add", data=_valid_payload())

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_valid_data_inserts_row_with_correct_values(client):
    user_id = _create_user()
    _login(client, user_id)

    client.post(
        "/expenses/add",
        data=_valid_payload(
            amount="42.50",
            category="Food",
            date=_today(),
            description="Lunch with team",
        ),
    )

    rows = _expense_rows_for(user_id)
    assert len(rows) == 1
    row = rows[0]
    assert row["user_id"] == user_id
    assert float(row["amount"]) == 42.50
    assert row["category"] == "Food"
    assert row["date"] == _today()
    assert row["description"] == "Lunch with team"


def test_post_valid_data_does_not_create_row_for_other_users(client):
    user_a = _create_user("a@example.com")
    user_b = _create_user("b@example.com")
    _login(client, user_a)

    client.post("/expenses/add", data=_valid_payload())

    assert len(_expense_rows_for(user_a)) == 1
    assert len(_expense_rows_for(user_b)) == 0


# --------------------------------------------------------------------------
# DoD 4: newly added expense appears in /profile's totals, category
# breakdown, and recent-expenses list immediately after redirect
# --------------------------------------------------------------------------

def test_new_expense_reflected_in_profile_after_add(client):
    user_id = _create_user()
    _login(client, user_id)

    client.post(
        "/expenses/add",
        data=_valid_payload(
            amount="42.50",
            category="Food",
            date=_today(),
            description="Lunch with team",
        ),
    )

    html = client.get("/profile").get_data(as_text=True)

    assert "42.50" in html
    assert "Food" in html
    assert "Lunch with team" in html


# --------------------------------------------------------------------------
# DoD 5: negative or non-numeric amount re-renders form, no row inserted
# --------------------------------------------------------------------------

def test_post_negative_amount_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(amount="-10.00")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html  # form re-rendered
    assert len(_expense_rows_for(user_id)) == 0


def test_post_non_numeric_amount_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(amount="not-a-number")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="amount"' in html
    assert len(_expense_rows_for(user_id)) == 0


def test_post_zero_amount_rerenders_form_without_inserting(client):
    """Amount must be positive per spec ('positive numeric value')."""
    user_id = _create_user()
    _login(client, user_id)

    response = client.post("/expenses/add", data=_valid_payload(amount="0"))

    assert response.status_code == 200
    assert len(_expense_rows_for(user_id)) == 0


# --------------------------------------------------------------------------
# DoD 6: invalid/unsupported category re-renders form, no row inserted
# --------------------------------------------------------------------------

def test_post_invalid_category_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(category="Groceries")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="category"' in html
    assert len(_expense_rows_for(user_id)) == 0


def test_post_empty_category_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post("/expenses/add", data=_valid_payload(category=""))

    assert response.status_code == 200
    assert len(_expense_rows_for(user_id)) == 0


# --------------------------------------------------------------------------
# DoD 7: missing or malformed date re-renders form, no row inserted
# --------------------------------------------------------------------------

def test_post_missing_date_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    payload = _valid_payload()
    del payload["date"]

    response = client.post("/expenses/add", data=payload)
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="date"' in html
    assert len(_expense_rows_for(user_id)) == 0


def test_post_malformed_date_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(date="not-a-date")
    )
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert 'name="date"' in html
    assert len(_expense_rows_for(user_id)) == 0


def test_post_future_date_rerenders_form_without_inserting(client):
    """Rules for implementation: date must be valid YYYY-MM-DD not in the
    future."""
    user_id = _create_user()
    _login(client, user_id)

    future_date = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    response = client.post(
        "/expenses/add", data=_valid_payload(date=future_date)
    )

    assert response.status_code == 200
    assert len(_expense_rows_for(user_id)) == 0


# --------------------------------------------------------------------------
# DoD 8: description is optional
# --------------------------------------------------------------------------

def test_post_without_description_succeeds(client):
    user_id = _create_user()
    _login(client, user_id)

    payload = _valid_payload()
    del payload["description"]

    response = client.post("/expenses/add", data=payload)

    assert response.status_code == 302
    assert "/profile" in response.headers["Location"]


def test_post_without_description_stores_null_or_empty(client):
    user_id = _create_user()
    _login(client, user_id)

    payload = _valid_payload()
    del payload["description"]
    client.post("/expenses/add", data=payload)

    rows = _expense_rows_for(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] in (None, "")


def test_post_with_empty_string_description_succeeds(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(description="")
    )

    assert response.status_code == 302
    rows = _expense_rows_for(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] in (None, "")


# --------------------------------------------------------------------------
# Extra: description length cap ("Rules for implementation")
# --------------------------------------------------------------------------

def test_post_overlong_description_rerenders_form_without_inserting(client):
    user_id = _create_user()
    _login(client, user_id)

    response = client.post(
        "/expenses/add", data=_valid_payload(description="x" * 501)
    )

    assert response.status_code == 200
    assert len(_expense_rows_for(user_id)) == 0


# --------------------------------------------------------------------------
# database/db.py: create_expense uses parameterized queries and returns
# the new row's id
# --------------------------------------------------------------------------

def test_create_expense_returns_new_row_id_and_persists(client):
    user_id = _create_user()

    new_id = db_module.create_expense(
        user_id=user_id,
        amount=15.00,
        category="Transport",
        date=_today(),
        description="Bus fare",
    )

    rows = _expense_rows_for(user_id)
    assert len(rows) == 1
    assert rows[0]["id"] == new_id
    assert rows[0]["amount"] == 15.00
    assert rows[0]["category"] == "Transport"
    assert rows[0]["description"] == "Bus fare"


def test_create_expense_description_defaults_supported_as_none(client):
    """create_expense accepts description=None per its documented signature."""
    user_id = _create_user()

    db_module.create_expense(
        user_id=user_id,
        amount=5.00,
        category="Other",
        date=_today(),
        description=None,
    )

    rows = _expense_rows_for(user_id)
    assert len(rows) == 1
    assert rows[0]["description"] is None
