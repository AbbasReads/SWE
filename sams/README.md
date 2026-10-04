# Students' Auditorium Management Software (SAMS)

A web-based system for managing a college auditorium — scheduling shows, selling/cancelling tickets, recording expenses, and generating balance sheets.

**Stack (as required by the problem statement):** Linux · MySQL (MariaDB) · Apache (mod\_wsgi) · Python / Flask — containerised with Docker.

---

## Quick Start

```bash
docker compose up --build       # First run → builds images and starts everything
docker compose up               # Subsequent runs
docker compose down             # Stop (data is kept)
docker compose down -v          # Stop and wipe the database
```

App runs at **http://localhost:8080**

### Default Logins

| Role | Username | Password |
|------|----------|----------|
| Show Manager | `manager` | `manager` |
| Sales Person | `sales1` | `sales1` |
| Accounts Clerk | `clerk` | `clerk` |

---

## Features by Role

### Show Manager
- Create shows (title, date, time, seat counts, prices)
- View booking statistics (% occupancy, total collection)
- View balance sheets per show or per year
- Manage sales staff

### Sales Person
- Book tickets for customers (balcony / ordinary)
- Cancel tickets with auto-calculated refund
- Reprint existing tickets

### Accounts Clerk
- Record and view expenditures per show

### Public (No Login)
- View upcoming shows and seat availability at `/availability`

---

## Cancellation & Refund Rules

| When Cancelled | Deduction |
|----------------|-----------|
| More than 3 days before show | Rs 5 flat |
| 1–3 days before (ordinary seat) | Rs 10 flat |
| 1–3 days before (balcony seat) | Rs 15 flat |
| On the day of the show | 50% of ticket price |
| After the show | ❌ Not allowed |

---

## Project Structure

```
sams/
├── app.py              ← All web routes (Flask controller)
├── models.py           ← Business logic (refunds, seats, balance sheets)
├── db.py               ← Database layer (all SQL lives here)
├── schema.sql          ← Creates the 4 DB tables
├── sams.wsgi           ← Apache entry point for mod_wsgi
├── requirements.txt    ← Python dependencies
├── test_models.py      ← 11 automated unit tests (all pass)
├── Dockerfile          ← App container recipe
├── docker-compose.yml  ← Starts app + database together
├── templates/          ← 12 Jinja2 HTML templates
├── static/style.css    ← All CSS styling
└── docker/apache.conf  ← Apache virtual host config
```

---

## Tech Stack

| Technology | Role |
|------------|------|
| **Python / Flask** | Web framework & routing |
| **MySQL (MariaDB 11)** | Persistent relational database |
| **Apache + mod\_wsgi** | Production web server (2 procs × 5 threads) |
| **Docker / Compose** | Containerised deployment |
| **PyMySQL** | Python ↔ MySQL connector |
| **Werkzeug** | Password hashing (bcrypt-style) |
| **Jinja2** | HTML templating |

---

## Database Schema

Four tables: `users`, `shows`, `tickets`, `expenditures`.  
InnoDB engine used throughout for transactions, row-level locking (prevents double-booking), and foreign key constraints.

**Balance sheet formula:**
```
Net Balance = Total Income − Salesperson Commissions − Expenditures
```

---

## Running Tests

```bash
pip install -r requirements.txt
python -m unittest              # Runs 11 model tests (no DB required)
```

Tests cover: refund calculations, capacity limits, pricing rules, balance sheet math, and cancellation edge cases.

---

## Security

- Passwords stored as **hashed values** (never plain text)
- **Role-based access control** — each role sees only their own pages
- **Session-based authentication**
- **Parameterised SQL queries** — prevents SQL injection
- `SELECT ... FOR UPDATE` row locking — prevents double-booking race conditions
