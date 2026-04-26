#!/usr/bin/env python3
"""Master script to run the complete DocuMind AI test suite."""

import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent


def run_step(name: str, script: str, args: list = None) -> bool:
    """Run a test step and return success status."""
    print("\n" + "=" * 70)
    print(f"STEP: {name}")
    print("=" * 70)
    
    cmd = [sys.executable, str(TEST_DIR / script)]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(cmd, cwd=str(TEST_DIR), check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"❌ Step failed with exit code {e.returncode}")
        return False
    except Exception as e:
        print(f"❌ Step failed: {e}")
        return False


def main():
    """Run the full test suite."""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           DOCUMIND AI COMPREHENSIVE TEST SUITE                       ║
║                                                                      ║
║  This will:                                                          ║
║  1. Generate 25 diverse test PDFs                                    ║
║  2. Upload them all to the backend                                   ║
║  3. Collect detailed metrics                                         ║
║  4. Generate visual reports with tables and graphs                   ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Check prerequisites
    print("Checking prerequisites...")
    
    # Check if backend is running
    import urllib.request
    try:
        urllib.request.urlopen("http://localhost:8000/health", timeout=2)
        print("✅ Backend is running on http://localhost:8000")
    except:
        print("❌ Backend is not running!")
        print("   Please start it first:")
        print("   cd backend && uvicorn api.main:app --reload")
        return 1
    
    steps = [
        ("Generate 25 Test PDFs", "generate_test_pdfs.py", []),
        ("Run Batch Upload Tests", "run_batch_tests.py", []),
        ("Generate Reports", "generate_report.py", []),
    ]
    
    for i, (name, script, args) in enumerate(steps, 1):
        print(f"\n\n📌 Step {i}/{len(steps)}: {name}")
        if not run_step(name, script, args):
            print(f"\n❌ Test suite failed at step {i}")
            return 1
    
    # Final summary
    print("\n\n" + "=" * 70)
    print("✅ TEST SUITE COMPLETED SUCCESSFULLY")
    print("=" * 70)
    print(f"\n📁 Generated files in: {TEST_DIR}")
    print(f"   - PDFs:         {TEST_DIR}/pdfs/")
    print(f"   - Results JSON: {TEST_DIR}/test_results.json")
    print(f"   - HTML Report:  {TEST_DIR}/report/report.html")
    print(f"   - Markdown:     {TEST_DIR}/report/table.md")
    print("\n🚀 Next steps:")
    print("   1. Open test_results.json for raw data")
    print("   2. Open report/report.html in browser for visualizations")
    print("   3. Copy report/table.md for documentation")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
