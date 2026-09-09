# -*- coding: utf-8 -*-
"""سيفتي — تطبيق مصاريف الشريكين (وأصدقائهم المغتربين)."""

import os
import sys
import sqlite3
from datetime import date
from pathlib import Path

DEFAULT_CATEGORIES = ["إيجار", "بقالة وأكل", "فواتير", "نت وموبايل", "مواصلات", "ترفيه وخروج", "صحة", "أخرى"]

_conn = None


def db_path() -> Path:
    """مسار قاعدة البيانات على الجهاز المحلي (تخزين داخلي بدون حسابات)."""
    override = os.environ.get("SAYFATY_DB")
    if override:
        return Path(override)
    # أولًا: مجلد بيانات التطبيق (يعمل على أندرويد)
    for home in (Path.home(), Path.cwd()):
        try:
            d = home / ".sayfaty"
            d.mkdir(parents=True, exist_ok=True)
            # تحقق قابلية الكتابة
            probe = d / ".probe"
            probe.write_text("ok")
            probe.unlink()
            return d / "sayfaty.db"
        except Exception:
            continue
    # أخيرًا: مجلد مؤقت
    from tempfile import gettempdir
    d = Path(gettempdir()) / "sayfaty"
    d.mkdir(parents=True, exist_ok=True)
    return d / "sayfaty.db"


def connect():
    global _conn
    if _conn is None:
        p = db_path()
        _conn = sqlite3.connect(str(p))
        _conn.row_factory = sqlite3.Row
        _init(_conn)
    return _conn


def _init(c):
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            advance REAL NOT NULL DEFAULT 0,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,          -- YYYY-MM-DD
            description TEXT NOT NULL,
            category TEXT DEFAULT 'أخرى',
            amount REAL NOT NULL,
            paid_by TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'مشترك',  -- مشترك / فردي
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settlements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            day TEXT NOT NULL,
            payer TEXT NOT NULL,
            receiver TEXT NOT NULL,
            amount REAL NOT NULL,
            note TEXT DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    c.commit()


# ---------------------------------------------------------
# Members
# ---------------------------------------------------------
def list_members():
    return connect().execute("SELECT * FROM members ORDER BY id").fetchall()


def add_member(name, advance, note=""):
    c = connect()
    c.execute("INSERT INTO members (name, advance, note) VALUES (?,?,?)", (name.strip(), float(advance or 0), note))
    c.commit()


def update_member(mid, name, advance, note=""):
    c = connect()
    c.execute("UPDATE members SET name=?, advance=?, note=? WHERE id=?", (name.strip(), float(advance or 0), note, mid))
    c.commit()


def delete_member(mid):
    c = connect()
    c.execute("DELETE FROM members WHERE id=?", (mid,))
    c.commit()


# ---------------------------------------------------------
# Expenses
# ---------------------------------------------------------
def add_expense(day, description, category, amount, paid_by, kind, note=""):
    c = connect()
    c.execute(
        "INSERT INTO expenses (day,description,category,amount,paid_by,kind,note) VALUES (?,?,?,?,?,?,?)",
        (str(day), description.strip(), category, float(amount or 0), paid_by, kind, note),
    )
    c.commit()


def list_expenses(limit=200):
    return connect().execute("SELECT * FROM expenses ORDER BY day DESC, id DESC LIMIT ?", (limit,)).fetchall()


def delete_expense(eid):
    c = connect()
    c.execute("DELETE FROM expenses WHERE id=?", (eid,))
    c.commit()


# ---------------------------------------------------------
# Settlements
# ---------------------------------------------------------
def add_settlement(day, payer, receiver, amount, note=""):
    c = connect()
    c.execute(
        "INSERT INTO settlements (day,payer,receiver,amount,note) VALUES (?,?,?,?,?)",
        (str(day), payer, receiver, float(amount or 0), note),
    )
    c.commit()


def list_settlements(limit=200):
    return connect().execute("SELECT * FROM settlements ORDER BY day DESC, id DESC LIMIT ?", (limit,)).fetchall()


def delete_settlement(sid):
    c = connect()
    c.execute("DELETE FROM settlements WHERE id=?", (sid,))
    c.commit()


# ---------------------------------------------------------
# Settings / categories
# ---------------------------------------------------------
def get_setting(key, default=""):
    r = connect().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else default


def set_setting(key, value):
    c = connect()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)", (key, str(value)))
    c.commit()


def list_categories():
    raw = get_setting("categories", ",".join(DEFAULT_CATEGORIES))
    cats = [x.strip() for x in raw.split(",") if x.strip()]
    if not cats:
        cats = list(DEFAULT_CATEGORIES)
    return cats


def save_categories(cats):
    set_setting("categories", ",".join(x.strip() for x in cats if x.strip()))


def currency():
    return get_setting("currency", "ج.م")


def set_currency(v):
    set_setting("currency", v or "ج.م")


# ---------------------------------------------------------
# Summary / برامج الحساب (نفس منطق ملف الإكسل)
# ---------------------------------------------------------
def summary():
    c = connect()
    members = list_members()
    expenses = c.execute("SELECT * FROM expenses").fetchall()
    settlements = c.execute("SELECT * FROM settlements").fetchall()
    names = [m["name"] for m in members]

    total_all = sum(e["amount"] for e in expenses)
    total_shared = sum(e["amount"] for e in expenses if e["kind"] == "مشترك")
    total_advance = sum(m["advance"] for m in members)
    n = len(names)
    share_each = round(total_shared / n, 2) if n else 0.0

    rows = []
    for m in members:
        paid_shared = sum(
            e["amount"] for e in expenses if e["paid_by"] == m["name"] and e["kind"] == "مشترك"
        )
        received = sum(s["amount"] for s in settlements if s["receiver"] == m["name"])
        paid_out = sum(s["amount"] for s in settlements if s["payer"] == m["name"])
        balance = m["advance"] + paid_shared - share_each
        net = balance + paid_out - received
        rows.append(
            {
                "id": m["id"],
                "name": m["name"],
                "advance": m["advance"],
                "paid_shared": round(paid_shared, 2),
                "share": share_each,
                "balance": round(balance, 2),
                "received": round(received, 2),
                "paid_out": round(paid_out, 2),
                "net": round(net, 2),
            }
        )

    # breakdown by category
    cat_totals = {cat: 0.0 for cat in list_categories()}
    for e in expenses:
        cat_totals[e["category"]] = cat_totals.get(e["category"], 0.0) + e["amount"]

    return {
        "total_all": round(total_all, 2),
        "total_shared": round(total_shared, 2),
        "total_advance": round(total_advance, 2),
        "count": n,
        "share_each": share_each,
        "rows": rows,
        "categories": cat_totals,
        "expense_count": len(expenses),
        "settlement_count": len(settlements),
    }


def fmt(v):
    """تنسيق مبلغ عربي بفاصلة الآلاف."""
    s = f"{v:,.2f}".replace(",", "،")
    if s.endswith(".00"):
        s = s[:-3]
    return s


def today_str():
    return date.today().isoformat()