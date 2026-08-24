import os
import re
from datetime import datetime

from flask import Flask, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_user,
    get_category_breakdown,
    get_db,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
)

app = Flask(__name__)
# dev-only: regenerates on restart, invalidating existing sessions
app.secret_key = os.urandom(24)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@app.context_processor
def inject_current_user():
    user_id = session.get("user_id")
    return {"current_user": get_user_by_id(user_id) if user_id else None}


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not name or not email or not password:
        return render_template("register.html", error="All fields are required.")

    if not EMAIL_RE.match(email):
        return render_template(
            "register.html", error="Please enter a valid email address."
        )

    if len(password) < 8:
        return render_template(
            "register.html", error="Password must be at least 8 characters long."
        )

    if get_user_by_email(email) is not None:
        return render_template(
            "register.html", error="An account with this email already exists."
        )

    password_hash = generate_password_hash(password)
    create_user(name, email, password_hash)
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = get_user_by_email(email)
    if user is None or not check_password_hash(user["password_hash"], password):
        return render_template("login.html", error="Invalid email or password.")

    session["user_id"] = user["id"]
    return redirect(url_for("profile"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/how-it-works")
def how_it_works():
    return "#"  # i will add things later


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

def parse_date_range(start_str, end_str):
    """Validate a start/end date pair for the profile date filter.

    Returns (start_date, end_date, error):
      - (None, None, None)        -> no filter requested (both blank)
      - (None, None, "message")   -> malformed/incomplete/inverted input;
                                      caller should fall back to all-time data
      - ("YYYY-MM-DD", "YYYY-MM-DD", None) -> valid, inclusive range
    """
    start_str = (start_str or "").strip()
    end_str = (end_str or "").strip()

    if not start_str and not end_str:
        return None, None, None

    if not start_str or not end_str:
        return None, None, "Please provide both a start and end date to filter."

    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end = datetime.strptime(end_str, "%Y-%m-%d")
    except ValueError:
        return None, None, "Enter valid dates in YYYY-MM-DD format."

    if start > end:
        return None, None, "Start date must be on or before end date."

    # Return the normalized, zero-padded form (not the raw input) so the
    # SQL BETWEEN clause — a plain TEXT/lexicographic comparison — always
    # compares against a canonical YYYY-MM-DD string.
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"), None


@app.route("/profile")
def profile():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    user = get_user_by_id(user_id)
    member_since = datetime.strptime(
        user["created_at"], "%Y-%m-%d %H:%M:%S"
    ).strftime("%B %Y")

    start_param = request.args.get("start_date", "")
    end_param = request.args.get("end_date", "")
    start_date, end_date, filter_error = parse_date_range(start_param, end_param)
    filter_active = start_date is not None

    # Pre-fill the form with the validated/normalized values when the filter
    # is active; on invalid input, clear the fields instead of echoing back
    # the raw (possibly malformed) text the user typed.
    start_date_value = start_date or ""
    end_date_value = end_date or ""

    total_spent, expense_count = get_expense_summary(
        user_id, start_date=start_date, end_date=end_date
    )

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        total_spent=total_spent,
        expense_count=expense_count,
        category_breakdown=get_category_breakdown(
            user_id, start_date=start_date, end_date=end_date
        ),
        recent_expenses=get_recent_expenses(
            user_id, start_date=start_date, end_date=end_date
        ),
        filter_active=filter_active,
        filter_error=filter_error,
        start_date_value=start_date_value,
        end_date_value=end_date_value,
    )


@app.route("/expenses/add")
def add_expense():
    return "Add expense — coming in Step 7"


@app.route("/expenses/<int:id>/edit")
def edit_expense(id):
    return "Edit expense — coming in Step 8"


@app.route("/expenses/<int:id>/delete")
def delete_expense(id):
    return "Delete expense — coming in Step 9"


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
