#!/usr/bin/env python3
"""
TRACE E2E Test Suite Runner.
Executes the opaque-box end-to-end testing tiers for Project TRACE:
- Tier 1: Feature Coverage (F01 - F29, 145+ tests)
- Tier 2: Boundary & Corner Cases (F01 - F29, 145+ tests)
- Tier 3: Cross-Feature Interactions (12 tests)
- Tier 4: Real-World Forensics Scenarios (6 tests)

CLI Options:
  --tier <1,2,3,4,all>   Specify which tiers to run (comma-separated or 'all')
  --json                 Output structured JSON test execution report
  --verbose, -v          Verbose test execution logs
  --output, -o <path>    Write JSON report to specified file

Exit Code Protocol:
  0: All executed tests passed successfully (100% pass rate)
  1: One or more test failures occurred, or invalid CLI arguments
"""

import sys
import os
import argparse
import json
import time
from datetime import datetime, timezone
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TESTS_DIR)

TIER_CONFIG = {
    1: {
        "id": 1,
        "name": "Tier 1: Feature Coverage (F01 - F29)",
        "file": os.path.join(TESTS_DIR, "test_tier1_features.py"),
        "min_expected": 145,
    },
    2: {
        "id": 2,
        "name": "Tier 2: Boundary & Corner Cases (F01 - F29)",
        "file": os.path.join(TESTS_DIR, "test_tier2_boundaries.py"),
        "min_expected": 145,
    },
    3: {
        "id": 3,
        "name": "Tier 3: Cross-Feature Interactions",
        "file": os.path.join(TESTS_DIR, "test_tier3_combinations.py"),
        "min_expected": 10,
    },
    4: {
        "id": 4,
        "name": "Tier 4: Real-World Forensics Scenarios",
        "file": os.path.join(TESTS_DIR, "test_tier4_scenarios.py"),
        "min_expected": 5,
    },
}


class E2ETestPlugin:
    """Pytest plugin to capture individual test outcomes and metrics."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.skipped = []
        self.errors = []
        self.test_details = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            duration = getattr(report, "duration", 0.0)
            node_id = report.nodeid
            if report.passed:
                self.passed.append(node_id)
                self.test_details.append({
                    "node_id": node_id,
                    "outcome": "passed",
                    "duration_seconds": round(duration, 4),
                    "error": None
                })
            elif report.failed:
                err_msg = str(report.longrepr) if report.longrepr else "Test assertion failed"
                self.failed.append(node_id)
                self.test_details.append({
                    "node_id": node_id,
                    "outcome": "failed",
                    "duration_seconds": round(duration, 4),
                    "error": err_msg
                })
            elif report.skipped:
                self.skipped.append(node_id)
                self.test_details.append({
                    "node_id": node_id,
                    "outcome": "skipped",
                    "duration_seconds": round(duration, 4),
                    "error": None
                })
        elif report.failed and report.when in ("setup", "teardown"):
            err_msg = str(report.longrepr) if report.longrepr else "Setup/Teardown failed"
            self.errors.append(report.nodeid)
            self.test_details.append({
                "node_id": report.nodeid,
                "outcome": "error",
                "duration_seconds": 0.0,
                "error": err_msg
            })


def parse_tiers(tier_arg: str):
    if not tier_arg or tier_arg.strip().lower() == "all":
        return [1, 2, 3, 4]
    tokens = [t.strip() for t in tier_arg.split(",") if t.strip()]
    tiers = []
    for t in tokens:
        try:
            val = int(t)
            if val not in TIER_CONFIG:
                raise ValueError(f"Unknown tier: {val}. Valid tiers are 1, 2, 3, 4.")
            if val not in tiers:
                tiers.append(val)
        except ValueError as err:
            if "Unknown tier" in str(err):
                raise
            raise ValueError(f"Invalid tier argument: '{t}'. Must be integer 1, 2, 3, 4 or 'all'.")
    tiers.sort()
    return tiers


def run_tier(tier_num: int, verbose: bool = False, suppress_output: bool = False):
    config = TIER_CONFIG[tier_num]
    test_file = config["file"]
    plugin = E2ETestPlugin()

    pytest_args = [
        "-q",
        test_file,
    ]
    if verbose and not suppress_output:
        pytest_args.append("-v")

    start_time = time.perf_counter()
    if suppress_output:
        import io
        import contextlib
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            exit_code = pytest.main(pytest_args, plugins=[plugin])
    else:
        exit_code = pytest.main(pytest_args, plugins=[plugin])
    duration = time.perf_counter() - start_time

    return {
        "tier_id": tier_num,
        "name": config["name"],
        "file": os.path.relpath(test_file, PROJECT_ROOT),
        "total": len(plugin.passed) + len(plugin.failed) + len(plugin.skipped) + len(plugin.errors),
        "passed": len(plugin.passed),
        "failed": len(plugin.failed) + len(plugin.errors),
        "skipped": len(plugin.skipped),
        "duration_seconds": round(duration, 3),
        "exit_code": int(exit_code),
        "details": plugin.test_details,
    }


def main():
    parser = argparse.ArgumentParser(
        description="TRACE Opaque-Box E2E Test Suite Runner"
    )
    parser.add_argument(
        "--tier",
        type=str,
        default="all",
        help="Comma-separated tier numbers (e.g. 1,2 or 1,2,3,4 or all). Default: all",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON test execution report",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose test reporting",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Write JSON execution report to file",
    )

    args = parser.parse_args()

    try:
        tiers_to_run = parse_tiers(args.tier)
    except ValueError as err:
        if args.json:
            print(json.dumps({"error": str(err), "status": "ERROR"}))
        else:
            print(f"\033[91m[ERROR] {err}\033[0m")
        sys.exit(1)

    overall_start = time.perf_counter()
    tier_results = {}
    any_failures = False

    if not args.json:
        print("\033[1;32m" + "=" * 78)
        print("  TRACE · चेहरा → सबूत · OPAQUE-BOX E2E TEST SUITE RUNNER")
        print("  Goa Forensics Provenance & Smart Contract Acceptance")
        print("=" * 78 + "\033[0m")
        print(f"  Tiers Scheduled: {tiers_to_run}")
        print(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print("-" * 78)

    for tier_num in tiers_to_run:
        cfg = TIER_CONFIG[tier_num]
        if not args.json:
            print(f"\n\033[1;33m▶ Executing {cfg['name']}...\033[0m")

        res = run_tier(tier_num, verbose=args.verbose, suppress_output=args.json)
        tier_results[f"tier_{tier_num}"] = res

        if res["failed"] > 0 or res["exit_code"] != 0:
            any_failures = True
            if not args.json:
                print(f"  \033[91m✖ {cfg['name']} FAILED ({res['failed']} failures, {res['passed']} passed)\033[0m")
        else:
            if not args.json:
                print(f"  \033[92m✔ {cfg['name']} PASSED (100% - {res['passed']}/{res['total']} passed in {res['duration_seconds']}s)\033[0m")

    total_duration = round(time.perf_counter() - overall_start, 3)
    total_tests = sum(r["total"] for r in tier_results.values())
    total_passed = sum(r["passed"] for r in tier_results.values())
    total_failed = sum(r["failed"] for r in tier_results.values())
    total_skipped = sum(r["skipped"] for r in tier_results.values())
    pass_rate = round((total_passed / total_tests * 100.0) if total_tests > 0 else 0.0, 2)

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "PASSED" if not any_failures else "FAILED",
        "tiers_executed": tiers_to_run,
        "summary": {
            "total": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "pass_rate_percent": pass_rate,
            "duration_seconds": total_duration,
        },
        "tier_breakdown": {
            k: {
                "name": v["name"],
                "file": v["file"],
                "total": v["total"],
                "passed": v["passed"],
                "failed": v["failed"],
                "skipped": v["skipped"],
                "duration_seconds": v["duration_seconds"],
            }
            for k, v in tier_results.items()
        },
    }

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            if not args.json:
                print(f"\n[REPORT] Saved JSON execution report to: {args.output}")
        except Exception as err:
            if not args.json:
                print(f"\n\033[91m[WARNING] Failed to write report file: {err}\033[0m")

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print("\n" + "=" * 78)
        print("  FINAL E2E EXECUTION SUMMARY")
        print("=" * 78)
        for k, v in tier_results.items():
            status_symbol = "\033[92m✔\033[0m" if v["failed"] == 0 else "\033[91m✖\033[0m"
            print(f"  {status_symbol} {v['name']:<45} {v['passed']:>3}/{v['total']:<3} passed ({v['duration_seconds']}s)")
        print("-" * 78)
        print(f"  TOTAL TESTS: {total_tests} | PASSED: {total_passed} | FAILED: {total_failed} | TIME: {total_duration}s")
        if not any_failures:
            print(f"\033[1;92m  VERDICT: 100% PASSED — READY FOR ARCHIVAL PRODUCTION NOTARIZATION\033[0m")
        else:
            print(f"\033[1;91m  VERDICT: REGRESSIONS DETECTED — {total_failed} TESTS FAILED\033[0m")
        print("=" * 78 + "\n")

    sys.exit(0 if not any_failures else 1)


if __name__ == "__main__":
    main()
