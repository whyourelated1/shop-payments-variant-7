import unittest
from reporting import format_amount


class ReportingTests(unittest.TestCase):
    def test_receipt_amount(self):
        self.assertEqual(format_amount("1250.5"), "1 250,50 RUB")

    def test_zero(self):
        self.assertEqual(format_amount("0"), "0,00 RUB")

    def test_negative_is_rejected(self):
        with self.assertRaises(ValueError):
            format_amount("-1")

    def test_non_finite_is_rejected(self):
        with self.assertRaises(ValueError):
            format_amount("NaN")


if __name__ == "__main__":
    unittest.main()
