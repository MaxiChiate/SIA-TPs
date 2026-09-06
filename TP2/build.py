"""Compile the native scoring kernel (``rust/``) into the active virtualenv.

Usage:
    python build.py [--profile release|parallel] [--jobs N] [--check]

Wraps ``maturin develop`` because two things about this build fail quietly:

- **``--release`` is not optional.** A debug build of this kernel is slower
  than the pure-Python implementation it replaced, and nothing warns you: the
  run just crawls. ``release`` is the default here and ``dev`` is not offered.
- **It has to run from ``rust/``.** Cargo looks for ``.cargo/config.toml``
  upward from its working directory, not from the manifest, so
  ``maturin develop -m rust/Cargo.toml`` silently drops ``target-cpu``. This
  script always chdirs into ``rust/`` first.

Afterwards it imports the freshly built extension in a subprocess (the parent
may already hold a stale one) and prints what it actually got, so a build that
lost its SIMD flags or landed on the wrong schema version says so here rather
than halfway through a four-hour run.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

TP2 = Path(__file__).resolve().parent
RUST = TP2 / "rust"

CHECK_SNIPPET = """
import triangles_native as native
print(f"build_info      {native.build_info()}")
print(f"schema_version  {native.schema_version()}")
print(f"module          {native.__file__}")
"""


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--profile", choices=("release", "parallel"), default="release",
        help="release: fat LTO, fastest binary (default). parallel: ThinLTO "
             "across 16 units, ~1.5x faster to compile, slightly slower binary "
             "- for iterating on the kernel, not for benchmarking it.",
    )
    parser.add_argument(
        "--jobs", type=int, default=None,
        help="cargo build jobs (default: one per logical CPU)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="skip compiling; just report the extension already installed",
    )
    return parser.parse_args(argv)


def _maturin() -> str:
    """Prefer the maturin next to this interpreter, so the build lands in the
    same environment the run will import from."""
    candidate = Path(sys.executable).parent / "maturin"
    return str(candidate) if candidate.is_file() else "maturin"


def _environment(jobs: int | None) -> dict[str, str]:
    env = dict(os.environ)
    # ``maturin develop`` installs into VIRTUAL_ENV. Running the venv's python
    # directly (../.venv/bin/python build.py) does not set it, so derive it
    # rather than making activation a precondition.
    if "VIRTUAL_ENV" not in env and sys.prefix != sys.base_prefix:
        env["VIRTUAL_ENV"] = sys.prefix
    if jobs is not None:
        env["CARGO_BUILD_JOBS"] = str(jobs)
    return env


def _report() -> int:
    """Import the extension in a clean interpreter and print what it is."""
    result = subprocess.run(
        [sys.executable, "-c", CHECK_SNIPPET], capture_output=True, text=True
    )
    if result.returncode != 0:
        print(result.stderr.strip(), file=sys.stderr)
        print("\nthe extension is not importable; build it with: python build.py",
              file=sys.stderr)
        return 1
    print(result.stdout, end="")
    if "release" not in result.stdout:
        print("\nWARNING: this is not a release build - runs will be far slower",
              file=sys.stderr)
    if "avx2" not in result.stdout:
        print("\nWARNING: no avx2 in build_info - rust/.cargo/config.toml's "
              "target-cpu did not apply (was maturin run from rust/?)",
              file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if args.check:
        return _report()

    command = [_maturin(), "develop", "--profile", args.profile]
    print(f"$ cd {RUST} && {' '.join(command)}")
    result = subprocess.run(command, cwd=RUST, env=_environment(args.jobs))
    if result.returncode != 0:
        return result.returncode

    print()
    return _report()


if __name__ == "__main__":
    raise SystemExit(main())
