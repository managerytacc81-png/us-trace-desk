"""
Test Suite: CLI Invocations and Argument Parsing.
"""
import sys
from pathlib import Path
from unittest.mock import patch
from trace_desk.cli import main


def test_cli_demo_invocation(tmp_path):
    demo_out = tmp_path / "demo_test_out"
    test_args = ["trace-desk", "demo", "--out", str(demo_out)]
    with patch.object(sys, "argv", test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert demo_out.exists()
    assert (demo_out / "DEMO-CLEAN-CFM56_EXCEPTION_REPORT.json").exists()
    assert (demo_out / "DEMO-CLEAN-CFM56_EXCEPTION_REPORT.pdf").exists()


def test_cli_audit_json_invocation(tmp_path):
    # Create sample package JSON
    from trace_desk.cli import create_demo_clean_package
    pkg = create_demo_clean_package()
    pkg_json = tmp_path / "pkg.json"
    pkg_json.write_text(pkg.model_dump_json(indent=2), encoding="utf-8")

    audit_out = tmp_path / "audit_test_out"
    test_args = ["trace-desk", "audit", str(pkg_json), "--out", str(audit_out)]
    with patch.object(sys, "argv", test_args):
        try:
            main()
        except SystemExit as e:
            assert e.code == 0

    assert audit_out.exists()
    assert (audit_out / f"{pkg.package_id}_EXCEPTION_REPORT.json").exists()
