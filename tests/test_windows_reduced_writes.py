#!/usr/bin/env python3
"""Opt-in reduced-guarantee vault writes on native Windows.

Runs only on native Windows (POSIX uses descriptor confinement and is covered
by the other suites).  Verifies the gate, init, transaction apply/recover,
lock contention, capture, and the safe process probe.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import claude_obsidian.cli as cli_module
from claude_obsidian import winfd
from claude_obsidian.transaction import (
    BUNDLE_SCHEMA,
    MutationLock,
    TransactionConflict,
    apply_bundle,
    inspect_bundle,
    recover_incomplete,
)

GENERATED_AT = "2026-10-05T00:00:00Z"


@contextlib.contextmanager
def reduced(enabled: bool = True):
    saved = os.environ.get(winfd.ENV_FLAG)
    if enabled:
        os.environ[winfd.ENV_FLAG] = "1"
    else:
        os.environ.pop(winfd.ENV_FLAG, None)
    try:
        yield
    finally:
        if saved is None:
            os.environ.pop(winfd.ENV_FLAG, None)
        else:
            os.environ[winfd.ENV_FLAG] = saved


def run_cli(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        rc = cli_module.main(list(argv))
    return rc, out.getvalue(), err.getvalue()


def init_vault(root: Path) -> Path:
    vault = root / "vault"
    args = ["init", str(vault), "--generated-at", GENERATED_AT, "--operation-id", "init-r"]
    rc, out, err = run_cli(*args)
    assert rc == 0, err
    digest = json.loads(out)["approved_plan_sha256"]
    rc, out, err = run_cli(*args, "--approved-plan-sha256", digest, "--apply")
    assert rc == 0, err
    return vault


def page_bundle(operation_id: str, path: str) -> dict:
    return {
        "schema": BUNDLE_SCHEMA,
        "operation_id": operation_id,
        "operation_type": "generic",
        "expected_hashes": {path: None},
        "writes": [
            {
                "path": path,
                "mode": "create",
                "content": "---\ntype: concept\ntitle: A\nstatus: seed\n"
                "created: 2026-10-05\nupdated: 2026-10-05\ntags:\n  - concept\n---\n\n"
                "# A\n\nSee [[index]].\n",
            }
        ],
    }


def test_gate_off_still_refuses() -> None:
    with tempfile.TemporaryDirectory() as td, reduced(False):
        destination = Path(td) / "vault"
        rc, _out, err = run_cli(
            "init", str(destination), "--generated-at", GENERATED_AT,
            "--operation-id", "x", "--apply", "--approved-plan-sha256", "0" * 64,
        )
        assert rc == 2 and err.startswith("ERR UNSUPPORTED_PLATFORM:"), err
        assert "CLAUDE_OBSIDIAN_ALLOW_REDUCED_WRITES" in err
        assert not destination.exists()


def test_init_apply_lint_clean() -> None:
    with tempfile.TemporaryDirectory() as td, reduced():
        vault = init_vault(Path(td))
        assert (vault / "wiki" / "index.md").is_file()
        rc, out, err = run_cli("lint", "--vault", str(vault))
        assert rc == 0, err
        assert json.loads(out)["summary"]["issues_found"] == 0


def test_transaction_apply_then_recover_noop() -> None:
    with tempfile.TemporaryDirectory() as td, reduced():
        vault = init_vault(Path(td))
        bundle = page_bundle("t-one", "wiki/concepts/A.md")
        plan = inspect_bundle(vault, bundle)
        result = apply_bundle(
            vault, bundle, approved_plan_sha256=plan["approval_sha256"]
        )
        assert result["status"] == "complete"
        assert (vault / "wiki" / "concepts" / "A.md").read_bytes().startswith(b"---\n")
        assert not (vault / ".vault-meta" / "mutation.lock").exists()
        report = recover_incomplete(vault)
        assert not report


def test_lock_contention() -> None:
    with tempfile.TemporaryDirectory() as td, reduced():
        vault = init_vault(Path(td))
        with MutationLock(vault):
            try:
                with MutationLock(vault, timeout=0.2):
                    raise AssertionError("second lock must not be granted")
            except TransactionConflict as exc:
                assert exc.code == "LOCK_TIMEOUT"
        with MutationLock(vault, timeout=0.2):
            pass


def test_failed_apply_rolls_back() -> None:
    with tempfile.TemporaryDirectory() as td, reduced():
        vault = init_vault(Path(td))
        bundle = page_bundle("t-fail", "wiki/concepts/B.md")
        plan = inspect_bundle(vault, bundle)
        try:
            apply_bundle(
                vault, bundle, approved_plan_sha256=plan["approval_sha256"],
                fail_after=1,
            )
            raise AssertionError("injected failure expected")
        except RuntimeError:
            pass
        assert not (vault / "wiki" / "concepts" / "B.md").exists()
        assert not (vault / ".vault-meta" / "mutation.lock").exists()


def test_capture_apply() -> None:
    with tempfile.TemporaryDirectory() as td, reduced():
        vault = init_vault(Path(td))
        (vault / "inbox" / "note.txt").write_text("hello\n", encoding="utf-8")
        args = ["capture", "apply", "--vault", str(vault), "--generated-at",
                GENERATED_AT, "--operation-id", "cap-1"]
        rc, out, err = run_cli(*args)
        assert rc == 0, err
        digest = json.loads(out)["approved_plan_sha256"]
        rc, out, err = run_cli(*args, "--approved-plan-sha256", digest, "--apply")
        assert rc == 0, err
        captured = [p for p in (vault / ".raw").rglob("*") if p.is_file()]
        assert len(captured) >= 2, captured


def test_process_probe_never_kills() -> None:
    assert winfd._kill(os.getpid(), 0) is None
    try:
        winfd._kill(0x7FFFFFF0, 0)
        raise AssertionError("missing pid must raise")
    except ProcessLookupError:
        pass


def main() -> int:
    if os.name != "nt":
        print("skip: native-Windows reduced-write tests")
        return 0
    tests = [value for key, value in sorted(globals().items()) if key.startswith("test_")]
    for test in tests:
        test()
        print(f"ok {test.__name__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
