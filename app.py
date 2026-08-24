import os
import re
from datetime import datetime

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database.db import (
    create_expense,
    create_user,
    delete_expense as delete_expense_db,
    get_category_breakdown,
    get_db,
    get_expense_by_id,
    get_expense_summary,
    get_recent_expenses,
    get_user_by_email,
    get_user_by_id,
    init_db,
    seed_db,
    update_expense,
)

app = Flask(__name__)
# dev-only: regenerates on restart, invalidating existing sessions
app.secret_key = os.urandom(24)

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_CATEGORIES = [
    "Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other",
]
# Reject nan/inf/scientific notation/signs before float() gets a chance to accept them.
AMOUNT_RE = re.compile(r"^\d+(\.\d{1,2})?$")
MAX_DESCRIPTION_LENGTH = 500


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


def parse_expense_form(form):
    """Validate the add-expense form fields.

    Returns (values, error):
      - values: dict with amount/category/date/description, all as strings
        (amount holds the parsed float on success). Each field is validated
        independently; a field that fails is cleared to "" while other
        valid fields are preserved for re-display.
      - error: None if every field is valid, else the first validation
        message encountered, checked in order amount -> category -> date
        -> description.
    """
    error = None

    amount_raw = (form.get("amount") or "").strip()
    if AMOUNT_RE.match(amount_raw) and float(amount_raw) > 0:
        amount = float(amount_raw)
    else:
        amount = ""
        error = error or "Enter a valid positive amount."

    category_raw = (form.get("category") or "").strip()
    if category_raw in ALLOWED_CATEGORIES:
        category = category_raw
    else:
        category = ""
        error = error or "Select a valid category."

    date_raw = (form.get("date") or "").strip()
    if not date_raw:
        date = ""
        error = error or "Date is required."
    else:
        try:
            parsed_date = datetime.strptime(date_raw, "%Y-%m-%d")
        except ValueError:
            date = ""
            error = error or "Enter a valid date in YYYY-MM-DD format."
        else:
            if parsed_date.date() > datetime.now().date():
                date = ""
                error = error or "Date cannot be in the future."
            else:
                date = parsed_date.strftime("%Y-%m-%d")

    description_raw = (form.get("description") or "").strip()
    if len(description_raw) > MAX_DESCRIPTION_LENGTH:
        description = ""
        error = error or "Description must be 500 characters or fewer."
    else:
        description = description_raw

    values = {
        "amount": amount,
        "category": category,
        "date": date,
        "description": description,
    }
    return values, error


@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    if request.method == "GET":
        return render_template(
            "add_expense.html",
            categories=ALLOWED_CATEGORIES,
            amount="",
            category="",
            date=datetime.now().strftime("%Y-%m-%d"),
            description="",
        )

    values, error = parse_expense_form(request.form)
    if error:
        return render_template(
            "add_expense.html", categories=ALLOWED_CATEGORIES, error=error, **values
        )

    create_expense(
        user_id=user_id,
        amount=values["amount"],
        category=values["category"],
        date=values["date"],
        description=values["description"] or None,
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=ALLOWED_CATEGORIES,
            amount=expense["amount"],
            category=expense["category"],
            date=expense["date"],
            description=expense["description"] or "",
        )

    values, error = parse_expense_form(request.form)
    if error:
        return render_template(
            "edit_expense.html",
            expense=expense,
            categories=ALLOWED_CATEGORIES,
            error=error,
            **values,
        )

    update_expense(
        expense_id=id,
        user_id=user_id,
        amount=values["amount"],
        category=values["category"],
        date=values["date"],
        description=values["description"] or None,
    )
    return redirect(url_for("profile"))


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
def delete_expense(id):
    user_id = session.get("user_id")
    if user_id is None:
        return redirect(url_for("login"))

    expense = get_expense_by_id(id, user_id)
    if expense is None:
        abort(404)

    if request.method == "GET":
        return render_template("delete_expense.html", expense=expense)

    delete_expense_db(id, user_id)
    return redirect(url_for("profile"))


if __name__ == "__main__":
    with app.app_context():
        init_db()
        seed_db()
    app.run(debug=True, port=5001)
