# Unit tests for math_utils.calc.factorial function
import unittest
from math_utils.calc import factorial

class TestFactorial(unittest.TestCase):

    def test_factorial_zero(self):
        """Test factorial of 0"""
        self.assertEqual(factorial(0), 1)

    def test_factorial_one(self):
        """Test factorial of 1"""
        self.assertEqual(factorial(1), 1)

    def test_factorial_five(self):
        """Test factorial of 5"""
        self.assertEqual(factorial(5), 120)

    def test_factorial_ten(self):
        """Test factorial of 10"""
        self.assertEqual(factorial(10), 3628800)

    def test_factorial_negative_number(self):
        """Test that negative input raises ValueError"""
        with self.assertRaises(ValueError) as context:
            factorial(-1)
        self.assertEqual(str(context.exception), "Factorial is not defined for negative numbers")

if __name__ == '__main__':
    unittest.main()