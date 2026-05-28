import sqlite3
import os
from datetime import datetime

DB_PATH = os.getenv("DB_PATH", "dayplus.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS products (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                name            TEXT    NOT NULL,
                category        TEXT    NOT NULL DEFAULT 'Boshqa',
                photo_id        TEXT,
                manufactured_at TEXT    NOT NULL,
                expires_at      TEXT    NOT NULL,
                arrived_at      TEXT    NOT NULL,
                remind_days     INTEGER NOT NULL DEFAULT 3,
                quantity        INTEGER NOT NULL DEFAULT 1,
                batch_number    TEXT,
                is_notified     INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS templates (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                name        TEXT    NOT NULL,
                category    TEXT    NOT NULL DEFAULT 'Boshqa',
                remind_days INTEGER NOT NULL DEFAULT 3,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS shop_settings (
                user_id     INTEGER PRIMARY KEY,
                shop_name   TEXT    NOT NULL DEFAULT 'Do''kon',
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS discount_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id  INTEGER NOT NULL REFERENCES products(id),
                old_price   INTEGER NOT NULL,
                new_price   INTEGER NOT NULL,
                reason      TEXT,
                image_path  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
    print("✅ Database initialized")


# ──────────────────────────────────────────
# Products
# ──────────────────────────────────────────

def add_product(user_id, name, category, photo_id,
                manufactured_at, expires_at, arrived_at,
                remind_days, quantity=1, batch_number=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO products
               (user_id, name, category, photo_id, manufactured_at,
                expires_at, arrived_at, remind_days, quantity, batch_number)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, name, category, photo_id,
             manufactured_at, expires_at, arrived_at,
             remind_days, quantity, batch_number)
        )
        return cur.lastrowid


def get_products(user_id, category=None):
    with get_conn() as conn:
        if category:
            rows = conn.execute(
                "SELECT * FROM products WHERE user_id=? AND category=? ORDER BY expires_at",
                (user_id, category)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM products WHERE user_id=? ORDER BY expires_at",
                (user_id,)
            ).fetchall()
    return [dict(r) for r in rows]


def search_products(user_id, query):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM products WHERE user_id=? AND name LIKE ? ORDER BY expires_at",
            (user_id, f"%{query}%")
        ).fetchall()
    return [dict(r) for r in rows]


def get_product(product_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM products WHERE id=?", (product_id,)
        ).fetchone()
    return dict(row) if row else None


def update_product(product_id, **kwargs):
    allowed = {"name", "category", "expires_at", "manufactured_at",
               "arrived_at", "remind_days", "quantity", "batch_number"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    sets = ", ".join(f"{k}=?" for k in fields)
    with get_conn() as conn:
        conn.execute(
            f"UPDATE products SET {sets} WHERE id=?",
            (*fields.values(), product_id)
        )


def delete_product(product_id, user_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM products WHERE id=? AND user_id=?",
            (product_id, user_id)
        )


def mark_notified(product_id):
    with get_conn() as conn:
        conn.execute(
            "UPDATE products SET is_notified=1 WHERE id=?", (product_id,)
        )


def get_expiring_products():
    today = datetime.now().strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM products
               WHERE date(expires_at, '-' || remind_days || ' days') <= ?
                 AND is_notified = 0""",
            (today,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_expiring_today_tomorrow(user_id):
    from datetime import date, timedelta
    today = date.today().strftime("%Y-%m-%d")
    tomorrow = (date.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM products
               WHERE user_id=? AND expires_at <= ?
               ORDER BY expires_at""",
            (user_id, tomorrow)
        ).fetchall()
    return [dict(r) for r in rows]


def get_weekly_stats(user_id):
    from datetime import date, timedelta
    today = date.today()
    week_ago = (today - timedelta(days=7)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    next_week = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    with get_conn() as conn:
        expired = conn.execute(
            "SELECT COUNT(*) FROM products WHERE user_id=? AND expires_at < ?",
            (user_id, today_str)
        ).fetchone()[0]
        expiring = conn.execute(
            "SELECT COUNT(*) FROM products WHERE user_id=? AND expires_at BETWEEN ? AND ?",
            (user_id, today_str, next_week)
        ).fetchone()[0]
        total = conn.execute(
            "SELECT COUNT(*) FROM products WHERE user_id=?", (user_id,)
        ).fetchone()[0]
    return {"expired": expired, "expiring": expiring, "total": total}


def get_loss_stats(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT p.name, p.quantity, d.old_price, d.new_price
               FROM products p
               LEFT JOIN discount_requests d ON d.product_id = p.id
               WHERE p.user_id=? AND p.expires_at < date('now')""",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


# ──────────────────────────────────────────
# Templates
# ──────────────────────────────────────────

def save_template(user_id, name, category, remind_days):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM templates WHERE user_id=? AND name=?",
            (user_id, name)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE templates SET category=?, remind_days=? WHERE id=?",
                (category, remind_days, existing[0])
            )
        else:
            conn.execute(
                "INSERT INTO templates (user_id, name, category, remind_days) VALUES (?,?,?,?)",
                (user_id, name, category, remind_days)
            )


def get_templates(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM templates WHERE user_id=? ORDER BY name",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_template(template_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM templates WHERE id=?", (template_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_template(template_id, user_id):
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM templates WHERE id=? AND user_id=?",
            (template_id, user_id)
        )


# ──────────────────────────────────────────
# Shop settings
# ──────────────────────────────────────────

def get_shop_name(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT shop_name FROM shop_settings WHERE user_id=?", (user_id,)
        ).fetchone()
    return row[0] if row else "Do'kon"


def set_shop_name(user_id, name):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO shop_settings (user_id, shop_name)
               VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET shop_name=excluded.shop_name""",
            (user_id, name)
        )


# ──────────────────────────────────────────
# Discount
# ──────────────────────────────────────────

def add_discount(product_id, old_price, new_price, reason, image_path=None):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO discount_requests
               (product_id, old_price, new_price, reason, image_path)
               VALUES (?, ?, ?, ?, ?)""",
            (product_id, old_price, new_price, reason, image_path)
        )
        return cur.lastrowid
