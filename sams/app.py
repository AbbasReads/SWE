"""Flask routes, grouped by actor. Routes stay thin: validate input, call models, persist via db."""
import os
from datetime import date, time
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from pymysql.err import IntegrityError
from werkzeug.security import check_password_hash

import db
from models import CATEGORIES, BalanceSheet, Expenditure, Show, Ticket, ValidationError

app = Flask(__name__)
app.secret_key = os.environ.get("SAMS_SECRET", "sams-lab-secret")


@app.template_filter("rs")
def rupees(amount):
    return f"{'−' if amount < 0 else ''}Rs {abs(amount):,.2f}"


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if session.get("role") != role:
                flash("Access denied", "error")
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@app.route("/")
def home():
    return render_template("home.html")


# ---------- Authentication ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        with db.connect() as conn:
            user = db.get_user(conn, request.form["username"])
        if user and check_password_hash(user["password"], request.form["password"]):
            session.update(user_id=user["id"], name=user["name"], role=user["role"])
            return redirect(url_for("home"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- Spectator ----------

@app.route("/availability")
def availability():
    with db.connect() as conn:
        shows = [s for s in db.load_shows(conn) if s.date >= date.today()]
    return render_template("availability.html", shows=shows)


# ---------- Show Manager ----------

@app.route("/manager/shows", methods=["GET", "POST"])
@role_required("manager")
def manager_shows():
    if request.method == "POST":
        f = request.form
        try:
            # one date may have several shows: one Show per comma-separated timing
            timings = [t.strip() for t in f["timings"].split(",") if t.strip()]
            if not timings:
                raise ValueError("enter at least one timing")
            shows = [Show(0, f["title"], date.fromisoformat(f["date"]), time.fromisoformat(t).strftime("%H:%M"),
                          float(f["balcony_price"]), float(f["ordinary_price"]),
                          int(f["balcony_seats"]), int(f["ordinary_seats"]),
                          int(f["comp_balcony"] or 0), int(f["comp_ordinary"] or 0)) for t in timings]
            for show in shows:
                show.validate()
            with db.connect() as conn:
                for show in shows:
                    db.save_show(conn, show)
            flash(f"Show configuration saved ({len(shows)} show(s))")
        except (ValueError, ValidationError) as e:
            flash(f"Error: {e}", "error")
        except IntegrityError:
            flash("Error: a show already exists at that date and time", "error")
        return redirect(url_for("manager_shows"))
    with db.connect() as conn:
        shows = db.load_shows(conn)
    return render_template("shows.html", shows=shows)


@app.route("/manager/shows/<int:show_id>/prices", methods=["POST"])
@role_required("manager")
def set_prices(show_id):
    with db.connect() as conn:
        show = db.load_show(conn, show_id)
        try:
            show.balcony_price = float(request.form["balcony_price"])
            show.ordinary_price = float(request.form["ordinary_price"])
            show.validate()
            db.update_prices(conn, show_id, show.balcony_price, show.ordinary_price)
            flash("Prices updated")
        except (ValueError, ValidationError) as e:
            flash(f"Error: {e}", "error")
    return redirect(url_for("manager_shows"))


@app.route("/manager/salespersons", methods=["GET", "POST"])
@role_required("manager")
def manager_salespersons():
    with db.connect() as conn:
        if request.method == "POST":
            f = request.form
            if db.get_user(conn, f["username"]):
                flash("Error: username already exists", "error")
            else:
                db.add_user(conn, f["username"], f["password"], f["name"], "sales",
                            float(f["commission"]) / 100)
                flash("Sales person account created")
            return redirect(url_for("manager_salespersons"))
        salespersons = db.load_salespersons(conn)
        tickets = [t for s in db.load_shows(conn) for t in s.tickets]
    return render_template("salespersons.html", salespersons=salespersons, tickets=tickets)


@app.route("/manager/stats")
@role_required("manager")
def manager_stats():
    with db.connect() as conn:
        shows = db.load_shows(conn)
    return render_template("stats.html", shows=shows, categories=CATEGORIES)


@app.route("/manager/balance")
@role_required("manager")
def manager_balance():
    with db.connect() as conn:
        shows = db.load_shows(conn)
        exps = db.load_expenditures(conn)
        sps = db.load_salespersons(conn)
    sheet = None
    if request.args.get("show"):
        show = next((s for s in shows if s.show_id == int(request.args["show"])), None)
        if show:
            sheet = BalanceSheet.generate_show_balance_sheet(show, exps, sps)
    elif request.args.get("year"):
        sheet = BalanceSheet.generate_yearly_balance_sheet(int(request.args["year"]), shows, exps, sps)
    return render_template("balance.html", shows=shows, sheet=sheet, this_year=date.today().year)


# ---------- Sales Person ----------

@app.route("/sales/book", methods=["GET", "POST"])
@role_required("sales")
def sales_book():
    with db.connect() as conn:
        if request.method == "POST":
            show = db.load_show(conn, int(request.form["show"]), for_update=True)
            category = request.form["category"]
            qty = int(request.form["qty"])
            if category not in CATEGORIES or qty < 1:
                flash("Error: invalid request", "error")
            elif show.date < date.today():
                flash("Error: show already held", "error")
            elif show.get_seat_availability(category) < qty:
                flash(f"Error: only {show.get_seat_availability(category)} seats available", "error")
            else:
                booked = []
                for _ in range(qty):
                    t = Ticket(0, show.show_id, category, show.next_seat_no(category),
                               show.price(category), date.today(), session["user_id"])
                    t.ticket_id = db.insert_ticket(conn, t)
                    show.tickets.append(t)
                    booked.append(t)
                return render_template("tickets.html", tickets=booked, show=show)
            return redirect(url_for("sales_book"))
        shows = [s for s in db.load_shows(conn) if s.date >= date.today()]
    return render_template("book.html", shows=shows)


@app.route("/sales/ticket/<int:ticket_id>")
@role_required("sales")
def print_ticket(ticket_id):
    with db.connect() as conn:
        t = db.load_ticket(conn, ticket_id)
        if t is None:
            flash("Error: no such ticket", "error")
            return redirect(url_for("sales_cancel"))
        show = db.load_show(conn, t.show_id)
    return render_template("tickets.html", tickets=[t], show=show)


@app.route("/sales/cancel", methods=["GET", "POST"])
@role_required("sales")
def sales_cancel():
    if request.method == "POST":
        with db.connect() as conn:
            t = db.load_ticket(conn, int(request.form["ticket_id"]), for_update=True)
            if t is None:
                flash("Error: no such ticket", "error")
            else:
                show = db.load_show(conn, t.show_id)
                try:
                    refund = t.cancel_booking(date.fromisoformat(request.form["cancel_date"]), show.date)
                    db.update_ticket(conn, t)
                    flash(f"Ticket #{t.ticket_id} cancelled. Refund: Rs {refund:.2f}")
                except ValidationError as e:
                    flash(f"Error: {e}", "error")
        return redirect(url_for("sales_cancel"))
    return render_template("cancel.html", today=date.today())


# ---------- Accounts Clerk ----------

@app.route("/clerk/expenditure", methods=["GET", "POST"])
@role_required("clerk")
def clerk_expenditure():
    with db.connect() as conn:
        if request.method == "POST":
            f = request.form
            try:
                amount = float(f["amount"])
                if amount <= 0:
                    raise ValueError("amount must be positive")
                db.insert_expenditure(conn, Expenditure(0, int(f["show"]), f["type"], f["description"],
                                                        amount, date.today()))
                flash("Expenditure recorded")
            except ValueError as e:
                flash(f"Error: {e}", "error")
            return redirect(url_for("clerk_expenditure"))
        shows = db.load_shows(conn)
        exps = db.load_expenditures(conn)
    return render_template("expenditure.html", shows=shows, exps=exps,
                           titles={s.show_id: s.title for s in shows})


if __name__ == "__main__":
    db.init_db()
    app.run(debug=True)
