from decimal import Decimal
import unittest
import payment as p


class PaymentTests(unittest.TestCase):
    def test_01_new_order_is_empty_draft(self):
        order = p.Order()
        self.assertEqual(order.items, [])
        self.assertEqual(order.status, "draft")

    def test_02_add_item(self):
        order = p.Order()
        order.add_item("Книга", "250.00", 2)
        item = order.items[0]
        self.assertEqual((item.name, item.price, item.quantity),
                         ("Книга", Decimal("250.00"), 2))

    def test_03_total_uses_decimal(self):
        order = p.Order()
        order.add_item("Карандаш", "0.10", 3)
        order.add_item("Блокнот", "1.20", 2)
        self.assertEqual(order.total, Decimal("2.70"))
        self.assertIsInstance(order.total, Decimal)

    def test_04_product_name_must_not_be_blank(self):
        for name in ("", "  ", "\t"):
            with self.subTest(name=repr(name)):
                with self.assertRaises(ValueError):
                    p.Order().add_item(name, "10.00", 1)
        order = p.Order()
        order.add_item("  Книга  ", "10.00", 1)
        self.assertEqual(order.items[0].name, "Книга")

    def test_05_price_must_be_positive_finite_decimal(self):
        for price in ("0", "-1", "NaN", "Infinity", "abc"):
            with self.subTest(price=price):
                with self.assertRaises(ValueError):
                    p.Order().add_item("Книга", price, 1)

    def test_06_quantity_must_be_positive_integer(self):
        for quantity in (0, -1, 1.5, True, "2"):
            with self.subTest(quantity=quantity):
                with self.assertRaises(ValueError):
                    p.Order().add_item("Книга", "10.00", quantity)

    def test_07_checkout_requires_items(self):
        with self.assertRaises(p.OrderStateError):
            p.Order().checkout()
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        self.assertEqual(order.status, "pending")

    def test_08_checked_out_order_cannot_be_edited(self):
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        with self.assertRaises(p.OrderStateError):
            order.add_item("Блокнот", "20.00", 1)
        self.assertEqual(len(order.items), 1)

    def test_09_successful_payment(self):
        order = p.Order()
        order.add_item("Книга", "250.00", 2)
        order.checkout()
        gateway = p.FakeGateway()
        receipt = p.PaymentService(gateway).pay(order, "pay-09")
        self.assertEqual(order.status, "paid")
        self.assertEqual(receipt.amount, Decimal("500.00"))
        self.assertEqual(receipt.transaction_id, "txn-1")
        self.assertEqual(gateway.calls, [(Decimal("500.00"), "pay-09")])

    def test_10_decline_does_not_mark_order_paid(self):
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        gateway = p.FakeGateway(approve=False)
        with self.assertRaises(p.PaymentDeclined):
            p.PaymentService(gateway).pay(order, "pay-10")
        self.assertEqual(order.status, "pending")
        self.assertEqual(len(gateway.calls), 1)

    def test_11_provider_error_is_translated(self):
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        gateway = p.FakeGateway(fail=True)
        with self.assertRaises(p.PaymentProviderError):
            p.PaymentService(gateway).pay(order, "pay-11")
        self.assertEqual(order.status, "pending")

    def test_12_only_pending_order_can_be_paid(self):
        gateway = p.FakeGateway()
        service = p.PaymentService(gateway)
        with self.assertRaises(p.OrderStateError):
            service.pay(p.Order(), "draft-key")
        self.assertEqual(gateway.calls, [])
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        service.pay(order, "first-key")
        with self.assertRaises(p.OrderStateError):
            service.pay(order, "second-key")
        self.assertEqual(len(gateway.calls), 1)

    def test_13_same_key_returns_same_receipt_without_charge(self):
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        gateway = p.FakeGateway()
        service = p.PaymentService(gateway)
        first = service.pay(order, "same-key")
        second = service.pay(order, "same-key")
        self.assertIs(first, second)
        self.assertEqual(len(gateway.calls), 1)

    def test_14_key_cannot_be_reused_for_another_order(self):
        first, second = p.Order(), p.Order()
        for order in (first, second):
            order.add_item("Книга", "10.00", 1)
            order.checkout()
        gateway = p.FakeGateway()
        service = p.PaymentService(gateway)
        service.pay(first, "shared-key")
        with self.assertRaises(p.IdempotencyConflict):
            service.pay(second, "shared-key")
        self.assertEqual(second.status, "pending")
        self.assertEqual(len(gateway.calls), 1)

    def test_15_key_is_required_and_failed_attempt_can_be_retried(self):
        order = p.Order()
        order.add_item("Книга", "10.00", 1)
        order.checkout()
        gateway = p.FakeGateway(approve=False)
        service = p.PaymentService(gateway)
        for key in ("", " ", None):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    service.pay(order, key)
        self.assertEqual(gateway.calls, [])
        with self.assertRaises(p.PaymentDeclined):
            service.pay(order, "retry-key")
        gateway.approve = True
        receipt = service.pay(order, "retry-key")
        self.assertEqual(order.status, "paid")
        self.assertEqual(receipt.amount, Decimal("10.00"))
        self.assertEqual(len(gateway.calls), 2)
