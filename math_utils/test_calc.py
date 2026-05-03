from math_utils.calc import factorial

# Test factorial function
def test_factorial():
    assert factorial(5) == 120, "factorial(5) should return 120"

if __name__ == "__main__":
    test_factorial()
    print("Test passed!")
