"""Run every self-test: `uv run python run_tests.py`

One command runs all three suites:
    parser -- pure logic (parsing, filtering, quadrants, Focus ranking)
    order  -- ordering layer (drop semantics, precision, persistence)
    writer -- the part that mutates data (most expensive failure, densest assertions)

With pytest installed, `uv run pytest` works too (every function is named test_*).
"""

import sys

import test_order
import test_parser
import test_writer

MODULES = (test_parser, test_order, test_writer)


def main() -> int:
    total = passed = 0
    failed: list[str] = []

    for mod in MODULES:
        name = mod.__name__.removeprefix("test_")
        print(f"\n=== {name} ===")
        for fn in mod.TESTS:
            total += 1
            try:
                fn()
                passed += 1
                print(f"  ok   {fn.__name__}")
            except Exception as exc:  # noqa: BLE001
                failed.append(f"{name}.{fn.__name__}")
                print(f"  FAIL {fn.__name__}: {type(exc).__name__}: {exc}")

    print(f"\n{passed}/{total} passed")
    if failed:
        print("failed:\n  " + "\n  ".join(failed))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
