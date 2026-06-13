"""
Run all Swaya.me smoke tests against test.swaya.me.
Usage:
    cd scripts/smoke && python run_all.py
    python run_all.py --only smoke_login smoke_exam
Environment variables:
    SMOKE_BASE      — override base URL (default: https://test.swaya.me)
    SMOKE_EMAIL     — host login email (default: demo@swaya.me)
    SMOKE_PASSWORD  — host login password (default: Demo1234)
    SMOKE_QUIZ_ID   — quiz id for live quiz smoke test (default: 1003)
"""
import sys, importlib, time, argparse

SUITE = [
    "smoke_login",
    "smoke_live_quiz",
    "smoke_exam",
    "smoke_poll",
]


def main():
    parser = argparse.ArgumentParser(description="Swaya smoke test runner")
    parser.add_argument("--only", nargs="+", metavar="TEST", help="Run only these tests")
    args = parser.parse_args()

    tests = args.only if args.only else SUITE
    results = {}

    print(f"\n{'='*60}")
    print(f"  Swaya Smoke Suite — {len(tests)} test(s)")
    print(f"{'='*60}")

    for test_name in tests:
        print(f"\n▶  Running {test_name}...")
        start = time.time()
        try:
            mod = importlib.import_module(test_name)
            code = mod.run()
            elapsed = time.time() - start
            results[test_name] = ("PASS" if code == 0 else "FAIL", elapsed)
        except Exception as e:
            elapsed = time.time() - start
            results[test_name] = ("ERROR", elapsed)
            print(f"  💥 {test_name} raised: {e}")

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    passed = 0
    for name, (verdict, secs) in results.items():
        icon = "✅" if verdict == "PASS" else "❌"
        print(f"  {icon}  {name:<30} {verdict:<6}  {secs:.1f}s")
        if verdict == "PASS":
            passed += 1

    total = len(results)
    print(f"\n  {passed}/{total} passed")
    print(f"{'='*60}\n")

    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
