# SAMS – HTTP API

Server-rendered web app (Flask behind Apache/mod_wsgi). Every endpoint returns HTML.

**Conventions**

- **Requests:** `GET` for pages, `POST` with form bodies (`application/x-www-form-urlencoded`) for actions.
- **Post/Redirect/Get:** a successful `POST` answers `302` back to its page with a message. The one exception is booking, which returns the printable tickets directly.
- **Auth:** the session cookie is set by `/login` and signed with `SAMS_SECRET`. Role-protected endpoints use `role_required(role)`. A wrong or missing role returns `302 → /login` with *Access denied*.
- **Errors:** validation errors are shown as a red message on the redirected page. Nothing is written when an error occurs, because each request is one MySQL transaction.
- **Dates:** `YYYY-MM-DD`; times `HH:MM`; money in rupees.

## Public

| Method | Endpoint | Input | Result |
|---|---|---|---|
| GET | `/` | – | Home: tiles for the current role |
| GET | `/availability` | – | Upcoming shows with balcony / ordinary seats left and prices |
| GET | `/login` | – | Login form |
| POST | `/login` | `username`, `password` | `302 → /` and session set · `200` *Invalid username or password* |
| GET | `/logout` | – | Clears session, `302 → /` |

## Show Manager (`role = manager`)

| Method | Endpoint | Input | Result |
|---|---|---|---|
| GET | `/manager/shows` | – | Shows list + new-show form |
| POST | `/manager/shows` | `title`, `date`, `timings` (e.g. `10:00, 18:00`), `balcony_seats`, `ordinary_seats`, `comp_balcony`, `comp_ordinary`, `balcony_price`, `ordinary_price` | One show per timing. Errors: seats exceed hall capacity, balcony price ≤ ordinary price, show already at that date/time |
| POST | `/manager/shows/<show_id>/prices` | `balcony_price`, `ordinary_price` | Updates prices (same price rule) |
| GET | `/manager/salespersons` | – | Sales persons with collection and commission + new-account form |
| POST | `/manager/salespersons` | `name`, `username`, `password`, `commission` (%) | Creates sales person login. Error: username exists |
| GET | `/manager/stats` | – | Per show: % booked and amount collected, per seat class |
| GET | `/manager/balance` | `?show=<id>` or `?year=<yyyy>` | Balance sheet: income, commission, expenditure, net |

## Sales Person (`role = sales`)

| Method | Endpoint | Input | Result |
|---|---|---|---|
| GET | `/sales/book` | – | Booking form with seats left per class |
| POST | `/sales/book` | `show`, `category` (`balcony`/`ordinary`), `qty` | `200` printable tickets with seat numbers; sale records the sales person id. Errors: show already held, only *N* seats available |
| GET | `/sales/ticket/<ticket_id>` | – | Reprint a ticket |
| GET | `/sales/cancel` | – | Cancellation form |
| POST | `/sales/cancel` | `ticket_id`, `cancel_date` | Marks ticket `CANCELLED`, releases seat, shows refund. Errors: no such ticket, already cancelled, show already held |

Refund = price − Rs 5 (3+ clear days before), − Rs 10 ordinary / Rs 15 balcony (3 to 1 days), − 50 % (last day).

## Accounts Clerk (`role = clerk`)

| Method | Endpoint | Input | Result |
|---|---|---|---|
| GET | `/clerk/expenditure` | – | Expenditure form + list |
| POST | `/clerk/expenditure` | `show`, `type`, `description`, `amount` (> 0) | Records expenditure against the show |
