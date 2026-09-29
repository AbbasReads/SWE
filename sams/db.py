"""MySQL persistence: connection, schema/seed, and row <-> model mapping."""
import os
from contextlib import contextmanager

import pymysql
from werkzeug.security import generate_password_hash

from models import Expenditure, SalesPerson, Show, Ticket

CONFIG = dict(
    host=os.environ.get("SAMS_DB_HOST", "localhost"),
    user=os.environ.get("SAMS_DB_USER", "sams"),
    password=os.environ.get("SAMS_DB_PASSWORD", "sams"),
    database=os.environ.get("SAMS_DB_NAME", "sams"),
)
SCHEMA = os.path.join(os.path.dirname(__file__), "schema.sql")


@contextmanager
def connect():
    """One transaction per block: commit on success, roll back on error."""
    conn = pymysql.connect(**CONFIG, cursorclass=pymysql.cursors.DictCursor, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def q(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur


def init_db():
    with connect() as conn:
        with open(SCHEMA) as f:
            for stmt in f.read().split(";"):
                if stmt.strip():
                    q(conn, stmt)
        if not q(conn, "SELECT 1 FROM users").fetchone():
            # IGNORE: several Apache worker processes may seed at the same time
            for username, name, role, rate in [("manager", "Show Manager", "manager", 0),
                                               ("sales1", "Sales Person 1", "sales", 0.02),
                                               ("clerk", "Accounts Clerk", "clerk", 0)]:
                add_user(conn, username, username, name, role, rate, ignore=True)


def add_user(conn, username, password, name, role, commission_rate=0, ignore=False):
    q(conn, f"INSERT {'IGNORE ' if ignore else ''}INTO users (username, password, name, role, commission_rate) "
            "VALUES (%s,%s,%s,%s,%s)",
      (username, generate_password_hash(password), name, role, commission_rate))


def get_user(conn, username):
    return q(conn, "SELECT * FROM users WHERE username = %s", (username,)).fetchone()


def _ticket(r):
    return Ticket(r["id"], r["show_id"], r["category"], r["seat_no"], float(r["price"]),
                  r["booking_date"], r["salesperson_id"], r["status"], float(r["refund"]))


def _hhmm(td):
    minutes = int(td.total_seconds()) // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def load_show(conn, show_id, for_update=False):
    """for_update locks the show row so concurrent bookings cannot oversell or reuse a seat."""
    sql = "SELECT * FROM shows WHERE id = %s" + (" FOR UPDATE" if for_update else "")
    r = q(conn, sql, (show_id,)).fetchone()
    if r is None:
        return None
    show = Show(r["id"], r["title"], r["date"], _hhmm(r["timing"]),
                float(r["balcony_price"]), float(r["ordinary_price"]), r["balcony_seats"], r["ordinary_seats"],
                r["comp_balcony"], r["comp_ordinary"])
    show.tickets = [_ticket(t) for t in q(conn, "SELECT * FROM tickets WHERE show_id = %s", (show_id,))]
    return show


def load_shows(conn):
    return [load_show(conn, r["id"]) for r in q(conn, "SELECT id FROM shows ORDER BY date, timing")]


def save_show(conn, s: Show):
    q(conn, """INSERT INTO shows (title, date, timing, balcony_price, ordinary_price,
               balcony_seats, ordinary_seats, comp_balcony, comp_ordinary) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
      (s.title, s.date, s.timing, s.balcony_price, s.ordinary_price,
       s.balcony_seats_for_sale, s.ordinary_seats_for_sale, s.comp_balcony, s.comp_ordinary))


def update_prices(conn, show_id, balcony_price, ordinary_price):
    q(conn, "UPDATE shows SET balcony_price = %s, ordinary_price = %s WHERE id = %s",
      (balcony_price, ordinary_price, show_id))


def load_ticket(conn, ticket_id, for_update=False):
    sql = "SELECT * FROM tickets WHERE id = %s" + (" FOR UPDATE" if for_update else "")
    r = q(conn, sql, (ticket_id,)).fetchone()
    return _ticket(r) if r else None


def insert_ticket(conn, t: Ticket):
    return q(conn, """INSERT INTO tickets (show_id, category, seat_no, price, booking_date, salesperson_id)
                      VALUES (%s,%s,%s,%s,%s,%s)""",
             (t.show_id, t.category, t.seat_no, t.price, t.booking_date, t.salesperson_id)).lastrowid


def update_ticket(conn, t: Ticket):
    q(conn, "UPDATE tickets SET status = %s, refund = %s WHERE id = %s", (t.status, t.refund, t.ticket_id))


def load_salespersons(conn):
    return [SalesPerson(r["id"], r["name"], r["username"], float(r["commission_rate"]))
            for r in q(conn, "SELECT * FROM users WHERE role = 'sales' ORDER BY id")]


def load_expenditures(conn):
    return [Expenditure(r["id"], r["show_id"], r["type"], r["description"], float(r["amount"]), r["date"])
            for r in q(conn, "SELECT * FROM expenditures ORDER BY date")]


def insert_expenditure(conn, e: Expenditure):
    q(conn, "INSERT INTO expenditures (show_id, type, description, amount, date) VALUES (%s,%s,%s,%s,%s)",
      (e.show_id, e.type, e.description, e.amount, e.date))
