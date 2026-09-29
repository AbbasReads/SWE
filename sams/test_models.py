import unittest
from datetime import date

from models import BalanceSheet, Expenditure, SalesPerson, Show, Ticket, ValidationError

SHOW_DATE = date(2026, 12, 10)


def make_show(**kw):
    args = dict(show_id=1, title="Drama", date=SHOW_DATE, timing="18:00", balcony_price=100,
                ordinary_price=60, balcony_seats_for_sale=150, ordinary_seats_for_sale=900)
    args.update(kw)
    return Show(**args)


def make_ticket(category="ordinary", price=60):
    return Ticket(1, 1, category, "O1", price, date(2026, 12, 1), salesperson_id=7)


class RefundTests(unittest.TestCase):
    def test_more_than_three_days(self):
        self.assertEqual(make_ticket().calculate_refund(date(2026, 12, 6), SHOW_DATE), 55)

    def test_within_three_days_ordinary(self):
        self.assertEqual(make_ticket().calculate_refund(date(2026, 12, 7), SHOW_DATE), 50)

    def test_within_three_days_balcony(self):
        self.assertEqual(make_ticket("balcony", 100).calculate_refund(date(2026, 12, 9), SHOW_DATE), 85)

    def test_last_day(self):
        self.assertEqual(make_ticket("balcony", 100).calculate_refund(SHOW_DATE, SHOW_DATE), 50)

    def test_after_show_rejected(self):
        with self.assertRaises(ValidationError):
            make_ticket().calculate_refund(date(2026, 12, 11), SHOW_DATE)

    def test_cannot_cancel_twice(self):
        t = make_ticket()
        t.cancel_booking(date(2026, 12, 1), SHOW_DATE)
        self.assertEqual(t.status, "CANCELLED")
        with self.assertRaises(ValidationError):
            t.cancel_booking(date(2026, 12, 1), SHOW_DATE)


class ShowTests(unittest.TestCase):
    def test_capacity_exceeded(self):
        with self.assertRaises(ValidationError):
            make_show(balcony_seats_for_sale=190, comp_balcony=20).validate()

    def test_balcony_must_cost_more(self):
        with self.assertRaises(ValidationError):
            make_show(balcony_price=50).validate()

    def test_availability_and_seat_reuse(self):
        s = make_show(ordinary_seats_for_sale=2)
        s.tickets = [Ticket(1, 1, "ordinary", "O1", 60, SHOW_DATE, 7),
                     Ticket(2, 1, "ordinary", "O2", 60, SHOW_DATE, 7)]
        self.assertEqual(s.get_seat_availability("ordinary"), 0)
        self.assertEqual(s.get_booked_percentage("ordinary"), 100)
        s.tickets[0].cancel_booking(date(2026, 12, 1), SHOW_DATE)
        self.assertEqual(s.get_seat_availability("ordinary"), 1)
        self.assertEqual(s.next_seat_no("ordinary"), "O1")


class BalanceSheetTests(unittest.TestCase):
    def test_show_balance_sheet(self):
        s = make_show()
        t1, t2 = make_ticket(), make_ticket()
        t2.cancel_booking(date(2026, 12, 1), SHOW_DATE)   # auditorium keeps Rs 5
        s.tickets = [t1, t2]
        sp = SalesPerson(7, "A", "a", 0.10)
        exp = Expenditure(1, 1, "Staff", "", 20, SHOW_DATE)
        sheet = BalanceSheet.generate_show_balance_sheet(s, [exp], [sp])
        self.assertEqual(sheet.total_income, 65)
        self.assertAlmostEqual(sheet.commission, 6.5)
        self.assertAlmostEqual(sheet.net_balance, 65 - 6.5 - 20)

    def test_yearly_filters_by_year(self):
        s1, s2 = make_show(), make_show(show_id=2, date=date(2025, 5, 1))
        s1.tickets = [make_ticket()]
        sheet = BalanceSheet.generate_yearly_balance_sheet(2026, [s1, s2], [], [])
        self.assertEqual(sheet.total_income, 60)


if __name__ == "__main__":
    unittest.main()
