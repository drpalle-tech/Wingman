"""Shopping cart totals."""

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True)
class LineItem:
    sku: str
    unit_price: Decimal
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError(f"quantity must be positive, got {self.quantity}")
        if self.unit_price < 0:
            raise ValueError(f"unit_price must not be negative, got {self.unit_price}")


@dataclass
class Cart:
    items: list[LineItem] = field(default_factory=list)

    def add(self, item: LineItem) -> None:
        self.items.append(item)

    def subtotal(self) -> Decimal:
        return sum((item.unit_price * item.quantity for item in self.items), Decimal("0"))

    def total(self, tax_rate: Decimal) -> Decimal:
        if not Decimal("0") <= tax_rate < Decimal("1"):
            raise ValueError(f"tax_rate must be in [0, 1), got {tax_rate}")
        return (self.subtotal() * (1 + tax_rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
