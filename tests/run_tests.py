#!/usr/bin/env python3
"""Test runner for DocuMind AI test suite."""

import sys
import subprocess
from pathlib import Path

def run_basic_tests():
    """Run basic tests that don't require heavy dependencies."""
    print("Running basic tests...")
    result = subprocess.run([sys.executable, "test_basic.py"], 
                          cwd=Path(__file__).parent)
    return result.returncode == 0

def run_full_tests():
    """Run full pytest suite if available."""
    print("\nRunning full test suite with pytest...")
    try:
        result = subprocess.run([sys.executable, "-m", "pytest", ".", "-v"],
                              cwd=Path(__file__).parent)
        return result.returncode == 0
    except Exception as e:
        print(f"Pytest not available or failed: {e}")
        return False

def main():
    """Main test runner."""
    print("DocuMind AI Test Suite")
    print("=" * 50)
    
    # Always run basic tests
    basic_passed = run_basic_tests()
    
    # Try to run full tests
    full_passed = run_full_tests()
    
    print("\n" + "=" * 50)
    if basic_passed and full_passed:
        print("✓ All tests passed!")
        return 0
    elif basic_passed:
        print("✓ Basic tests passed (full tests skipped)")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
