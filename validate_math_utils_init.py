import os

# Check if the file exists and has zero content
try:
    assert os.path.exists('math_utils/__init__.py'), "File math_utils/__init__.py does not exist"
    size = os.stat('math_utils/__init__.py').st_size
    assert size == 0, f"File math_utils/__init__.py is not empty (size: {size} bytes)"
    print("✅ Validation passed: math_utils/__init__.py exists and has zero content.")
except Exception as e:
    print(f"❌ Validation failed: {e}")
    exit(1)