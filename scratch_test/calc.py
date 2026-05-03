import math

def factorial(n):
    """Calculate factorial of n using iterative approach."""
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

if __name__ == "__main__":
    # Compute factorial of 5
    result = factorial(5)
    print(f"Factorial of 5 is: {result}")
