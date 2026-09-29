"""Domain classes, mirroring the class diagram. No database or web code here."""
from dataclasses import dataclass, field
from datetime import date

HALL_CAPACITY = {"balcony": 200, "ordinary": 1000}   # not given in the statement; adjust per hall
CATEGORIES = ("balcony", "ordinary")


class ValidationError(Exception):
    pass


@dataclass
class Ticket:
    ticket_id: int
    show_id: int
    category: str
    seat_no: str
    price: float
    booking_date: date
    salesperson_id: int
    status: str = "BOOKED"          # BOOKED -> CANCELLED (see state diagram)
    refund: float = 0.0

    def calculate_refund(self, cancel_date: date, show_date: date) -> float:
        days_left = (show_date - cancel_date).days
        if days_left < 0:
            raise ValidationError("Show already held; ticket cannot be cancelled")
        if days_left > 3:
            deduction = 5
        elif days_left >= 1:
            deduction = 15 if self.category == "balcony" else 10
        else:                        # last day (day of the show)
            deduction = self.price / 2
        return max(self.price - deduction, 0.0)

    def cancel_booking(self, cancel_date: date, show_date: date) -> float:
        if self.status != "BOOKED":
            raise ValidationError("Ticket is not in BOOKED state")
        self.refund = self.calculate_refund(cancel_date, show_date)
        self.status = "CANCELLED"
        return self.refund

    @property
    def retained(self) -> float:
        """Money the auditorium keeps from this ticket."""
        return self.price if self.status == "BOOKED" else self.price - self.refund


@dataclass
class Show:
    show_id: int
    title: str
    date: date
    timing: str
    balcony_price: float
    ordinary_price: float
    balcony_seats_for_sale: int
    ordinary_seats_for_sale: int
    comp_balcony: int = 0
    comp_ordinary: int = 0
    tickets: list = field(default_factory=list)

    def validate(self):
        if self.balcony_seats_for_sale + self.comp_balcony > HALL_CAPACITY["balcony"]:
            raise ValidationError("Balcony seats exceed hall capacity")
        if self.ordinary_seats_for_sale + self.comp_ordinary > HALL_CAPACITY["ordinary"]:
            raise ValidationError("Ordinary seats exceed hall capacity")
        if min(self.balcony_seats_for_sale, self.ordinary_seats_for_sale,
               self.comp_balcony, self.comp_ordinary) < 0:
            raise ValidationError("Seat counts cannot be negative")
        if self.ordinary_price <= 0 or self.balcony_price <= self.ordinary_price:
            raise ValidationError("Balcony price must be greater than ordinary price")

    def price(self, category: str) -> float:
        return self.balcony_price if category == "balcony" else self.ordinary_price

    def seats_for_sale(self, category: str) -> int:
        return self.balcony_seats_for_sale if category == "balcony" else self.ordinary_seats_for_sale

    def _booked(self, category: str):
        return [t for t in self.tickets if t.category == category and t.status == "BOOKED"]

    def get_seat_availability(self, category: str) -> int:
        return self.seats_for_sale(category) - len(self._booked(category))

    def get_booked_percentage(self, category: str) -> float:
        total = self.seats_for_sale(category)
        return 100.0 * len(self._booked(category)) / total if total else 0.0

    def get_collection(self, category: str) -> float:
        return sum(t.retained for t in self.tickets if t.category == category)

    def get_total_collection(self) -> float:
        return sum(t.retained for t in self.tickets)

    def next_seat_no(self, category: str) -> str:
        prefix = "B" if category == "balcony" else "O"
        taken = {t.seat_no for t in self._booked(category)}
        n = 1
        while f"{prefix}{n}" in taken:
            n += 1
        return f"{prefix}{n}"


@dataclass
class SalesPerson:
    salesperson_id: int
    name: str
    username: str
    commission_rate: float           # e.g. 0.02 = 2 %

    def collection(self, tickets) -> float:
        return sum(t.retained for t in tickets if t.salesperson_id == self.salesperson_id)

    def commission(self, tickets) -> float:
        return self.collection(tickets) * self.commission_rate


@dataclass
class Expenditure:
    expenditure_id: int
    show_id: int
    type: str
    description: str
    amount: float
    date: date


@dataclass
class BalanceSheet:
    title: str
    total_income: float
    commission: float
    total_expenditure: float

    @property
    def net_balance(self) -> float:
        return self.total_income - self.commission - self.total_expenditure

    @staticmethod
    def generate(title, shows, expenditures, salespersons):
        tickets = [t for s in shows for t in s.tickets]
        return BalanceSheet(
            title=title,
            total_income=sum(s.get_total_collection() for s in shows),
            commission=sum(sp.commission(tickets) for sp in salespersons),
            total_expenditure=sum(e.amount for e in expenditures),
        )

    @staticmethod
    def generate_show_balance_sheet(show, expenditures, salespersons):
        exps = [e for e in expenditures if e.show_id == show.show_id]
        return BalanceSheet.generate(f"Show: {show.title} ({show.date})", [show], exps, salespersons)

    @staticmethod
    def generate_yearly_balance_sheet(year, shows, expenditures, salespersons):
        shows = [s for s in shows if s.date.year == year]
        ids = {s.show_id for s in shows}
        exps = [e for e in expenditures if e.show_id in ids]
        return BalanceSheet.generate(f"Year {year}", shows, exps, salespersons)
