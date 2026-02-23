#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def write_receipt(batch: str, oracles: list[str], passed: bool) -> None:
    cache_dir = Path(".cache")
    cache_dir.mkdir(exist_ok=True)
    receipt_path = cache_dir / "verify-last.txt"
    ts = dt.datetime.now(dt.timezone.utc).isoformat()
    receipt_path.write_text(
        "\n".join(
            [
                f"BATCH={batch}",
                f"ORACLES_RUN={','.join(oracles)}",
                f"VERIFY_{'PASS' if passed else 'FAIL'}",
                f"TIMESTAMP={ts}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--receipt", default="UNSPECIFIED")
    args = parser.parse_args()

    oracles: list[str] = []
    all_ok = True

    compile_target = "kcp" if Path("kcp").exists() else "."
    compile_cmd = [sys.executable, "-m", "compileall", compile_target]
    oracles.append("compileall")
    rc, out, err = run(compile_cmd)
    print(f"$ {' '.join(compile_cmd)}")
    if out:
        print(out, end="")
    if err:
        print(err, end="", file=sys.stderr)
    if rc != 0:
        all_ok = False

    has_tests = Path("tests").exists() and any(Path("tests").glob("test*.py"))
    if has_tests and not args.fast:
        test_cmd = [sys.executable, "-m", "unittest", "discover", "-s", "tests"]
        oracles.append("unittest")
        rc, out, err = run(test_cmd)
        print(f"$ {' '.join(test_cmd)}")
        if out:
            print(out, end="")
        if err:
            print(err, end="", file=sys.stderr)
        if rc != 0:
            all_ok = False

    write_receipt(args.receipt, oracles, all_ok)
    print(f"VERIFY_RESULT={'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
