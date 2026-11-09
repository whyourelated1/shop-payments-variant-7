from decimal import Decimal, InvalidOperation
from dataclasses import dataclass


DRAFT = "draft"
PENDING = "pending"
PAID = "paid"


@dataclass(frozen=True)
class LineItem:
    name: str
    price: Decimal
    quantity: int


def _product_name(name):
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Product name is required")
    return name.strip()


def _price(value):
    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid price") from exc
    if not price.is_finite() or price <= 0:
        raise ValueError("Price must be positive and finite")
    return price


def _quantity(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Quantity must be a positive integer")
    return value


class OrderStateError(ValueError):
    pass


class Order:
    def __init__(self):
        self.items = []
        self.status = DRAFT

    def add_item(self, name, price, quantity):
        self.require_state(DRAFT)
        name = _product_name(name)
        price = _price(price)
        quantity = _quantity(quantity)
        self.items.append(LineItem(name, price, quantity))

    @property
    def total(self):
        return sum((item.price * item.quantity for item in self.items), Decimal("0.00"))

    def checkout(self):
        self.require_state(DRAFT)
        if not self.items:
            raise OrderStateError("Cannot checkout an empty order")
        self.status = PENDING

    def require_state(self, expected):
        if self.status != expected:
            raise OrderStateError(f"Expected {expected}, got {self.status}")


@dataclass(frozen=True)
class Receipt:
    transaction_id: str
    amount: Decimal


class IdempotencyConflict(ValueError):
    pass


class PaymentProviderError(Exception):
    pass


class PaymentDeclined(Exception):
    pass


class FakeGateway:
    def __init__(self, approve=True, fail=False):
        self.fail = fail
        self.approve = approve
        self.calls = []

    def charge(self, amount, key):
        self.calls.append((amount, key))
        if self.fail:
            raise ConnectionError("Provider unavailable")
        if not self.approve:
            return None
        return f"txn-{len(self.calls)}"


@dataclass(frozen=True)
class PaymentAttempt:
    order: Order
    receipt: Receipt


class PaymentService:
    def __init__(self, gateway):
        self.gateway = gateway
        self._receipts = {}

    def pay(self, order, key):
        key = self._normalize_key(key)
        if key in self._receipts:
            attempt = self._receipts[key]
            if attempt.order is not order:
                raise IdempotencyConflict("Key belongs to another order")
            return attempt.receipt
        order.require_state(PENDING)
        transaction_id = self._charge(order.total, key)
        self._require_approved(transaction_id)
        receipt = Receipt(transaction_id, order.total)
        self._mark_paid(order)
        self._receipts[key] = PaymentAttempt(order, receipt)
        return receipt

    @staticmethod
    def _mark_paid(order):
        order.status = PAID

    @staticmethod
    def _require_approved(transaction_id):
        if transaction_id is None:
            raise PaymentDeclined("Payment declined")

    def _charge(self, amount, key):
        try:
            return self.gateway.charge(amount, key)
        except ConnectionError as exc:
            raise PaymentProviderError("Payment provider unavailable") from exc

    @staticmethod
    def _normalize_key(key):
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Idempotency key is required")
        return key.strip()

# Receipt formatting is provided by reporting.format_amount.
