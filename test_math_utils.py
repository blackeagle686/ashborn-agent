import unittest
from math_utils.calc import factorial

class TestFactorial(unittest.TestCase):
    def test_factorial_zero(self):
        self.assertEqual(factorial(0), 1)

    def test_factorial_one(self):
        self.assertEqual(factorial(1), 1)

    def test_factorial_five(self):
        self.assertEqual(factorial(5), 120)

    def test_factorial_negative_input(self):
        with self.assertRaises(ValueError):
            factorial(-3)

if __name__ == '__main__':
    unittest.main()