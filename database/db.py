import os
import sqlite3

from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "expense_tracker.db"
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                date TEXT NOT NULL,
                description TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.commit()
    finally:
        conn.close()


def seed_db():
    conn = get_db()
    try:
        if conn.execute("SELECT 1 FROM users LIMIT 1").fetchone() is not None:
            return

        password_hash = generate_password_hash("demo123")
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Demo User", "demo@spendly.com", password_hash),
        )
        user_id = cursor.lastrowid

        sample_expenses = [
            (user_id, 45.50, "Food", "2026-08-02", "Groceries at supermarket"),
            (user_id, 12.00, "Transport", "2026-08-03", "Bus fare"),
            (user_id, 89.99, "Bills", "2026-08-05", "Electricity bill"),
            (user_id, 25.00, "Health", "2026-08-08", "Pharmacy purchase"),
            (user_id, 60.00, "Entertainment", "2026-08-11", "Movie night"),
            (user_id, 150.00, "Shopping", "2026-08-14", "New shoes"),
            (user_id, 18.75, "Food", "2026-08-18", "Lunch with coworkers"),
            (user_id, 30.00, "Other", "2026-08-21", "Miscellaneous expense"),
        ]
        conn.executemany(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            sample_expenses,
        )
        conn.commit()
    finally:
        conn.close()


def get_user_by_email(email):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
    finally:
        conn.close()


def get_user_by_id(user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    finally:
        conn.close()


def create_user(name, email, password_hash):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, password_hash),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def _apply_date_range(query, params, start_date, end_date):
    """Append a parameterized 'AND date BETWEEN ? AND ?' clause when both
    start_date and end_date are given. Trusts already-validated
    YYYY-MM-DD strings — callers own date parsing/validation.
    """
    if start_date and end_date:
        query += " AND date BETWEEN ? AND ?"
        params += [start_date, end_date]
    return query, params


def get_expense_summary(user_id, start_date=None, end_date=None):
    conn = get_db()
    try:
        query = (
            "SELECT COALESCE(SUM(amount), 0) AS total, COUNT(*) AS count "
            "FROM expenses WHERE user_id = ?"
        )
        params = [user_id]
        query, params = _apply_date_range(query, params, start_date, end_date)
        row = conn.execute(query, params).fetchone()
        return row["total"], row["count"]
    finally:
        conn.close()


def get_category_breakdown(user_id, start_date=None, end_date=None):
    conn = get_db()
    try:
        query = "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ?"
        params = [user_id]
        query, params = _apply_date_range(query, params, start_date, end_date)
        query += " GROUP BY category ORDER BY total DESC"
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def get_recent_expenses(user_id, limit=5, start_date=None, end_date=None):
    conn = get_db()
    try:
        query = "SELECT * FROM expenses WHERE user_id = ?"
        params = [user_id]
        query, params = _apply_date_range(query, params, start_date, end_date)
        query += " ORDER BY date DESC, id DESC LIMIT ?"
        params.append(limit)
        return conn.execute(query, params).fetchall()
    finally:
        conn.close()


def create_expense(user_id, amount, category, date, description):
    conn = get_db()
    try:
        cursor = conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, amount, category, date, description),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_expense_by_id(expense_id, user_id):
    conn = get_db()
    try:
        return conn.execute(
            "SELECT * FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        ).fetchone()
    finally:
        conn.close()


def update_expense(expense_id, user_id, amount, category, date, description):
    conn = get_db()
    try:
        conn.execute(
            "UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? "
            "WHERE id = ? AND user_id = ?",
            (amount, category, date, description, expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()


def delete_expense(expense_id, user_id):
    conn = get_db()
    try:
        conn.execute(
            "DELETE FROM expenses WHERE id = ? AND user_id = ?",
            (expense_id, user_id),
        )
        conn.commit()
    finally:
        conn.close()
