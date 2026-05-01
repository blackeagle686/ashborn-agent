"""
Integration test for the new surgical file editing tools.
Tests: import, file_read_lines, and file_update_multi (line-range + search-replace).
"""
import sys, os
sys.path.insert(0, os.path.join(os.getcwd(), "venv/lib/python3.12/site-packages"))
sys.path.insert(0, os.getcwd())

print("=== 1. Import Tests ===")
try:
    from ashborn.tools.file_tools import file_read_lines_tool, file_update_multi_tool
    print("✓ ashborn.tools.file_tools")
except Exception as e:
    print(f"✗ {e}")
    sys.exit(1)

try:
    from ashborn.agent import get_ashborn_agent
    print("✓ ashborn.agent")
except Exception as e:
    print(f"✗ {e}")

try:
    from ashborn.cognition import AshbornPlanner, AshbornThinker, AshbornLoop
    print("✓ ashborn.cognition")
except Exception as e:
    print(f"✗ {e}")
    sys.exit(1)

# ── Create a temp file for functional tests ────────────────────────────────
TMPFILE = "scratch/_test_edit_target.py"
os.makedirs("scratch", exist_ok=True)
with open(TMPFILE, "w") as f:
    f.write("""\
# original file
TIMEOUT = 30
VERSION = "1.0"

def greet():
    return "hello"

def add(a, b):
    return a + b
""")

print("\n=== 2. file_read_lines Test ===")
result = file_read_lines_tool(file_path=TMPFILE)
print(result)
assert "L1:" in result and "TIMEOUT" in result, "file_read_lines failed"
print("✓ file_read_lines returns numbered output")

print("\n=== 3. file_update_multi — line_range edit ===")
result = file_update_multi_tool(
    file_path=TMPFILE,
    edits=[{"line_start": 2, "line_end": 2, "new_content": "TIMEOUT = 60"}]
)
print(result)
with open(TMPFILE) as f:
    content = f.read()
assert "TIMEOUT = 60" in content, "line_range edit failed"
assert "VERSION" in content, "line_range edit destroyed other content!"
print("✓ line_range edit applied, rest of file intact")

print("\n=== 4. file_update_multi — search/replace edit ===")
result = file_update_multi_tool(
    file_path=TMPFILE,
    edits=[{"search": 'VERSION = "1.0"', "replace": 'VERSION = "2.0"'}]
)
print(result)
with open(TMPFILE) as f:
    content = f.read()
assert 'VERSION = "2.0"' in content, "search/replace failed"
assert "def greet" in content, "search/replace destroyed rest of file!"
print("✓ search/replace applied, rest of file intact")

print("\n=== 5. file_update_multi — overlap detection ===")
result = file_update_multi_tool(
    file_path=TMPFILE,
    edits=[
        {"line_start": 2, "line_end": 4, "new_content": "X = 1"},
        {"line_start": 3, "line_end": 5, "new_content": "Y = 2"},
    ]
)
print(result)
assert "Overlapping" in result, "Overlap detection failed!"
print("✓ Overlapping edit correctly rejected")

print("\n=== 6. file_update_multi — search not found ===")
result = file_update_multi_tool(
    file_path=TMPFILE,
    edits=[{"search": "THIS_DOES_NOT_EXIST", "replace": "nope"}]
)
print(result)
assert "not found" in result.lower(), "Missing search string should fail!"
print("✓ Missing search text correctly reported")

print("\n=== 7. AshbornPlanner._detect_existing_files ===")
# fake a planner with minimal stub
class FakeLLM: pass
class FakeTools:
    def get_all_tools_info(self): return []
planner = AshbornPlanner.__new__(AshbornPlanner)
planner.llm = FakeLLM()
planner.tools = FakeTools()
task = {"title": f"edit {TMPFILE}", "description": f"Change timeout in {TMPFILE}"}
detected = planner._detect_existing_files(task)
print(f"  Detected: {detected}")
assert TMPFILE in detected, "File detection failed"
print("✓ _detect_existing_files correctly found existing file in task")

print("\n=== All tests passed ✓ ===")
os.remove(TMPFILE)
