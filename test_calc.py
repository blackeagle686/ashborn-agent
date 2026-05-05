import sys
sys.path.append('math_utils')
from calc import factorial

def test_factorial():
    assert factorial(0) == 1, "factorial(0) should be 1"
    assert factorial(1) == 1, "factorial(1) should be 1"
    assert factorial(5) == 120, "factorial(5) should be 120"
    print("All tests passed!")

if __name__ == "__main__":
    test_factorial()