"""Tests for the dashboard date filter feature (spec: .claude/specs/05-date-filter.md).

Covers:
- GET /profile with no query params -> unchanged all-time behavior (DoD item 1)
- GET /profile with a valid start_date/end_date range -> scoped stats,
  category breakdown, and recent expenses (DoD item 2)
- Date-filter form inputs pre-filled from active query params (DoD item 3)
- "Clear filter" link only rendered when a filter is active (DoD item 4)
- Inverted / malformed dates never crash the app and fall back to all-time
  data with a validation notice (DoD item 5)
- A valid range with zero matching expenses shows the
  "No expenses in this range." empty state (DoD item 6)
- database/db.py functions accept optional start_date/end_date and are safe
  against injection via parameter binding (DoD item 7)
- Access level for /profile remains logged-in only
"""

from werkzeug.security import generate_password_hash

from database import db as db_module


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _create_user(email="filtertest@example.com"):
    return db_module.create_user(
        "Filter Tester", email, generate_password_hash("password123")
    )


def _insert_expense(user_id, amount, category, date, description=None):
    conn = db_module.get_db()
    try:
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
    finally:
        conn.close()


def _login(client, user_id):
    with client.session_transaction() as sess:
        sess["user_id"] = user_id


def _seed_sample_expenses(user_id):
    """5 expenses: 3 inside 2026-08-01..2026-08-10, 2 outside it."""
    _insert_expense(user_id, 50.00, "Food", "2026-08-01", "Groceries A")
    _insert_expense(user_id, 20.00, "Transport", "2026-08-05", "Bus fare A")
    _insert_expense(user_id, 30.00, "Food", "2026-08-10", "Dinner A")
    _insert_expense(user_id, 100.00, "Shopping", "2026-08-15", "Shoes A")
    _insert_expense(user_id, 15.00, "Entertainment", "2026-07-20", "Movie A")


# --------------------------------------------------------------------------
# Access level - unchanged, logged-in only
# --------------------------------------------------------------------------

def test_profile_redirects_when_logged_out(client):
    response = client.get("/profile")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_profile_with_filter_params_still_redirects_when_logged_out(client):
    response = client.get("/profile?start_date=2026-08-01&end_date=2026-08-10")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


# --------------------------------------------------------------------------
# DoD 1: no query params -> unchanged all-time behavior
# --------------------------------------------------------------------------

def test_no_query_params_shows_alltime_totals(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    # all-time total = 50 + 20 + 30 + 100 + 15 = 215.00, count = 5
    assert "215.00" in html
    assert '<div class="stat-value">5</div>' in html


def test_no_query_params_shows_all_categories(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    for category in ("Food", "Transport", "Shopping", "Entertainment"):
        assert category in html


def test_no_query_params_shows_all_recent_expenses(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    for description in ("Groceries A", "Bus fare A", "Dinner A", "Shoes A", "Movie A"):
        assert description in html


def test_no_query_params_no_filter_ui_shown(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    assert "Clear filter" not in html
    assert "Showing:" not in html


# --------------------------------------------------------------------------
# DoD 2: valid range scopes stats, category breakdown, recent expenses
# --------------------------------------------------------------------------

def test_valid_range_scopes_total_and_count(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?start_date=2026-08-01&end_date=2026-08-10")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    # in-range total = 50 + 20 + 30 = 100.00, count = 3
    assert "100.00" in html
    assert '<div class="stat-value">3</div>' in html


def test_valid_range_scopes_category_breakdown(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    # Food = 50 + 30 = 80.00, Transport = 20.00 within range
    assert "Food" in html
    assert "Transport" in html
    # Shopping and Entertainment expenses fall outside the range
    assert "Shopping" not in html
    assert "Entertainment" not in html


def test_valid_range_scopes_recent_expenses(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    for description in ("Groceries A", "Bus fare A", "Dinner A"):
        assert description in html
    for description in ("Shoes A", "Movie A"):
        assert description not in html


def test_range_boundaries_are_inclusive(client):
    user_id = _create_user()
    _insert_expense(user_id, 10.00, "Food", "2026-08-01", "Boundary start")
    _insert_expense(user_id, 20.00, "Food", "2026-08-10", "Boundary end")
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    assert "Boundary start" in html
    assert "Boundary end" in html
    assert '<div class="stat-value">2</div>' in html


# --------------------------------------------------------------------------
# DoD 3: form inputs pre-filled from active query params
# --------------------------------------------------------------------------

def test_form_inputs_prefilled_with_active_filter(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    assert 'name="start_date"' in html
    assert 'name="end_date"' in html
    assert 'value="2026-08-01"' in html
    assert 'value="2026-08-10"' in html


def test_form_inputs_blank_with_no_filter(client):
    user_id = _create_user()
    _login(client, user_id)

    html = client.get("/profile").get_data(as_text=True)

    assert 'value="2026-08-01"' not in html
    assert 'value="2026-08-10"' not in html


# --------------------------------------------------------------------------
# DoD 4: "Clear filter" only when a filter is active
# --------------------------------------------------------------------------

def test_clear_filter_link_present_when_filter_active(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    assert "Clear filter" in html


def test_clear_filter_target_returns_alltime_view(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    # simulate following the "Clear filter" link: plain GET /profile
    html = client.get("/profile").get_data(as_text=True)

    assert "215.00" in html
    assert "Clear filter" not in html


def test_showing_label_present_when_filter_active(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-08-01&end_date=2026-08-10"
    ).get_data(as_text=True)

    assert "Showing:" in html
    assert "2026-08-01" in html
    assert "2026-08-10" in html


# --------------------------------------------------------------------------
# DoD 5: invalid input never crashes, falls back to all-time + notice
# --------------------------------------------------------------------------

def test_start_after_end_falls_back_to_alltime_without_crash(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?start_date=2026-08-10&end_date=2026-08-01")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    # falls back to all-time totals
    assert "215.00" in html
    # no active filter UI when falling back
    assert "Clear filter" not in html
    assert "Showing:" not in html


def test_malformed_date_falls_back_to_alltime_without_crash(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?start_date=not-a-date&end_date=2026-08-10")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "215.00" in html
    assert "Clear filter" not in html


def test_only_start_date_provided_falls_back_to_alltime(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?start_date=2026-08-01")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "215.00" in html
    assert "Clear filter" not in html


def test_only_end_date_provided_falls_back_to_alltime(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?end_date=2026-08-10")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "215.00" in html
    assert "Clear filter" not in html


def test_invalid_date_range_does_not_return_server_error(client):
    user_id = _create_user()
    _login(client, user_id)

    # garbage input on both ends
    response = client.get("/profile?start_date=xxxx&end_date=yyyy")

    assert response.status_code == 200


# --------------------------------------------------------------------------
# DoD 6: zero matching expenses -> empty-state message, not an error
# --------------------------------------------------------------------------

def test_valid_range_with_no_matches_shows_empty_state(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    response = client.get("/profile?start_date=2026-09-01&end_date=2026-09-05")
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "No expenses in this range." in html
    # none of the seeded descriptions should leak through
    for description in ("Groceries A", "Bus fare A", "Dinner A", "Shoes A", "Movie A"):
        assert description not in html


def test_valid_range_with_no_matches_shows_zero_totals(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)
    _login(client, user_id)

    html = client.get(
        "/profile?start_date=2026-09-01&end_date=2026-09-05"
    ).get_data(as_text=True)

    assert '<div class="stat-value">0</div>' in html


# --------------------------------------------------------------------------
# DoD 7: database/db.py functions accept optional start_date/end_date and
# use parameterized queries
# --------------------------------------------------------------------------

def test_get_expense_summary_without_dates_matches_alltime(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    total, count = db_module.get_expense_summary(user_id)

    assert total == 215.00
    assert count == 5


def test_get_expense_summary_with_dates_scopes_result(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    total, count = db_module.get_expense_summary(
        user_id, start_date="2026-08-01", end_date="2026-08-10"
    )

    assert total == 100.00
    assert count == 3


def test_get_expense_summary_partial_dates_behaves_as_unfiltered(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    total, count = db_module.get_expense_summary(user_id, start_date="2026-08-01")

    assert total == 215.00
    assert count == 5


def test_get_category_breakdown_without_dates_matches_alltime(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    rows = db_module.get_category_breakdown(user_id)
    categories = {row["category"] for row in rows}

    assert categories == {"Food", "Transport", "Shopping", "Entertainment"}


def test_get_category_breakdown_with_dates_scopes_result(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    rows = db_module.get_category_breakdown(
        user_id, start_date="2026-08-01", end_date="2026-08-10"
    )
    totals = {row["category"]: row["total"] for row in rows}

    assert totals == {"Food": 80.00, "Transport": 20.00}


def test_get_recent_expenses_without_dates_matches_alltime(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    rows = db_module.get_recent_expenses(user_id)

    assert len(rows) == 5


def test_get_recent_expenses_with_dates_scopes_result(client):
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    rows = db_module.get_recent_expenses(
        user_id, start_date="2026-08-01", end_date="2026-08-10"
    )
    descriptions = {row["description"] for row in rows}

    assert descriptions == {"Groceries A", "Bus fare A", "Dinner A"}


def test_get_recent_expenses_respects_limit_within_range(client):
    user_id = _create_user()
    for day in range(1, 8):
        _insert_expense(
            user_id, 5.00, "Food", f"2026-08-0{day}", f"Item {day}"
        )

    rows = db_module.get_recent_expenses(
        user_id, limit=3, start_date="2026-08-01", end_date="2026-08-07"
    )

    assert len(rows) == 3


def test_date_functions_do_not_filter_across_other_users(client):
    user_a = _create_user("a@example.com")
    user_b = _create_user("b@example.com")
    _insert_expense(user_a, 40.00, "Food", "2026-08-05", "A's lunch")
    _insert_expense(user_b, 999.00, "Food", "2026-08-05", "B's lunch")

    total, count = db_module.get_expense_summary(
        user_a, start_date="2026-08-01", end_date="2026-08-10"
    )

    assert total == 40.00
    assert count == 1


def test_date_range_params_are_safely_bound_not_interpolated(client):
    """Malicious-looking date strings must be treated as literal parameter
    values (never string-interpolated into SQL) and simply match nothing."""
    user_id = _create_user()
    _seed_sample_expenses(user_id)

    total, count = db_module.get_expense_summary(
        user_id,
        start_date="' OR '1'='1",
        end_date="' OR '1'='1",
    )

    # Neither raises nor returns the all-time data; the bogus literal
    # value matches no rows in the BETWEEN clause.
    assert total == 0
    assert count == 0
