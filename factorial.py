def factorial(n):
    """
    Compute the factorial of a non-negative integer n using an iterative approach.

    Args:
        n (int): A non-negative integer.

    Returns:
        int: The factorial of n.

    Raises:
        ValueError: If n is negative.
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer.")
    
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers.")
    
    result = 1
    for i in range(1, n + 1):
        result *= i
    
    return result
