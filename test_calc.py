def factorial(n):
    if n == 0 or n == 1:
        return 1
    else:
        return n * factorial(n - 1)

# Test case
def test_factorial():
    assert factorial(5) == 120

if __name__ == "__main__":
    test_factorial()
    print("Test passed!")