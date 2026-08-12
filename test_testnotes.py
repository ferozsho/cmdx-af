import os

def test_testnotes_exists():
    assert os.path.exists('TESTNOTES.md'), "TESTNOTES.md should exist"

def test_testnotes_not_empty():
    with open('TESTNOTES.md', 'r') as f:
        content = f.read().strip()
    assert content, "TESTNOTES.md should not be empty"

def test_testnotes_contains_project_structure():
    with open('TESTNOTES.md', 'r') as f:
        content = f.read().lower()
    assert 'project structure' in content or 'structure' in content, "TESTNOTES.md should mention project structure"
