#/usr/bin/env python

# DESCRIPTION

"""
Unit tests for infant_recon_runner using unittest and mocks.
This script was generated with ChatGPT 5 from the original implemenentation of 
"infant_recon_runner.py" by Yihang Chen.

Date: 2025-Sep-02

Authors:
    Istvan N Huszar (INH)
    Yinhang Chen (YC)

"""

# DEVELOPMENT NOTES

"""

2025-Sep-02 INH:
    - Created by ChatGPT 5 based on infant_recon_runner.py
    - Untested so far, but should be a good starting point.

"""


# IMPORTS

import os
import sys
import json
import tempfile
import shutil
import unittest
from unittest import mock
from pathlib import Path

# Ensure we can import the module under test whether tests are run from repo root or tests folder
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

# Import after path adjustment
import infant_recon_runner  # noqa: E402


# IMPLEMENTATION

class TestInfantReconRunner(unittest.TestCase):
    """Unit tests for InfantReconRunner using unittest and mocks.

    These tests avoid invoking the actual infant_recon_all binary by mocking
    subprocess.run and working within temporary directories.
    """

    def setUp(self):
        # Create a temporary workspace per test
        self.tmpdir = tempfile.mkdtemp(prefix="infant_recon_test_")
        self.addCleanup(lambda: shutil.rmtree(self.tmpdir, ignore_errors=True))

        # Instantiate runner with in-memory default config, then override expectations
        self.runner = infant_recon_runner.InfantReconRunner()
        self.runner.expected_outputs = {
            "required_files": {
                ".": ["mprage.nii.gz"],
                "mri": ["brainmask.mgz"],
            },
            "optional_files": {
                "mri": ["wm.mgz"],
            },
            "conditional_files": {},
        }

    # ---------------------------
    # Helper utilities
    # ---------------------------
    def _make_output_tree(self, outdir: Path, required=True, optional=False):
        """Create a fake output tree for validation tests."""
        outdir.mkdir(parents=True, exist_ok=True)
        if required:
            (outdir / "mprage.nii.gz").write_text("dummy")
            (outdir / "mri").mkdir(exist_ok=True)
            (outdir / "mri" / "brainmask.mgz").write_text("dummy")
        if optional:
            (outdir / "mri" / "wm.mgz").write_text("dummy")

    # ---------------------------
    # Tests for command rewriting & output dir generation
    # ---------------------------
    def test_modify_command_for_unique_output_adds_flag(self):
        cmd = "infant_recon_all -s sub-01 -all"
        unique = str(Path(self.tmpdir) / "out1")
        new_cmd = self.runner.modify_command_for_unique_output(cmd, unique)
        self.assertIn("--outdir", new_cmd)
        self.assertIn(unique, new_cmd)

    def test_modify_command_for_unique_output_replaces_existing(self):
        cmd = "infant_recon_all -s sub-01 --outdir SOMEWHERE -all"
        unique = str(Path(self.tmpdir) / "out2")
        new_cmd = self.runner.modify_command_for_unique_output(cmd, unique)
        self.assertIn(f"--outdir {unique}", new_cmd)
        self.assertNotIn("SOMEWHERE", new_cmd)

    # ---------------------------
    # Tests for run_command with mocks
    # ---------------------------
    @mock.patch("subprocess.run")
    def test_run_command_success(self, mock_run):
        completed = mock.Mock()
        completed.returncode = 0
        completed.stdout = "OK"
        completed.stderr = ""
        mock_run.return_value = completed

        cmd = "infant_recon_all -s sub-01 -all"
        result = self.runner.run_command(cmd, timeout=10, working_dir=self.tmpdir)

        self.assertTrue(result["success"])  # exit code 0
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("--outdir", result["command"])  # command was augmented
        self.assertTrue(Path(result["output_directory"]).exists())
        mock_run.assert_called_once()

    @mock.patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="infant_recon_all", timeout=1))
    def test_run_command_timeout(self, mock_run):
        cmd = "infant_recon_all -s sub-01 -all"
        result = self.runner.run_command(cmd, timeout=1, working_dir=self.tmpdir)
        self.assertFalse(result["success"])  # timeouts are failures
        self.assertTrue(result["timeout_occurred"])  # explicit flag
        self.assertIsNone(result["exit_code"])  # no exit code on timeout
        self.assertIn("timed out", result["error_message"].lower())

    @mock.patch("subprocess.run")
    def test_run_command_nonzero_exit(self, mock_run):
        completed = mock.Mock()
        completed.returncode = 2
        completed.stdout = ""
        completed.stderr = "failure"
        mock_run.return_value = completed

        cmd = "infant_recon_all -s sub-01 -all"
        result = self.runner.run_command(cmd, timeout=10, working_dir=self.tmpdir)

        self.assertFalse(result["success"])  # non-zero exit
        self.assertEqual(result["exit_code"], 2)
        self.assertIn("failure", result["stderr"])  # bubbled up stderr

    # ---------------------------
    # Tests for validate_outputs
    # ---------------------------
    def test_validate_outputs_pass(self):
        # Arrange: construct an output dir with all required and optional files
        outdir = Path(self.tmpdir) / "sub-01_out"
        self._make_output_tree(outdir, required=True, optional=True)

        # Act
        validation = self.runner.validate_outputs(str(outdir))

        # Assert
        self.assertTrue(validation["validation_passed"])
        self.assertEqual(sorted(validation["required_files"]["missing"]), [])
        self.assertCountEqual(validation["required_files"]["found"], [
            "./mprage.nii.gz", "mri/brainmask.mgz"
        ])
        # Optional files discovered but do not affect pass/fail
        self.assertIn("mri/wm.mgz", validation["optional_files"]["found"])  

    def test_validate_outputs_fail_missing_required(self):
        outdir = Path(self.tmpdir) / "sub-01_out"
        # Only create the root required file; omit mri/brainmask.mgz
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / "mprage.nii.gz").write_text("dummy")

        validation = self.runner.validate_outputs(str(outdir))
        self.assertFalse(validation["validation_passed"])  # missing file => fail
        self.assertIn("mri/brainmask.mgz", validation["required_files"]["missing"]) 

    # ---------------------------
    # Integration: run_and_validate + report
    # ---------------------------
    @mock.patch("subprocess.run")
    def test_run_and_validate_success_and_report(self, mock_run):
        completed = mock.Mock()
        completed.returncode = 0
        completed.stdout = "OK"
        completed.stderr = ""
        mock_run.return_value = completed

        # Run and then simulate creating the outputs so validation passes
        cmd = "infant_recon_all -s sub-01 -all"
        combined = self.runner.run_and_validate(cmd, timeout=10, working_dir=self.tmpdir)

        # Create the expected tree inside the directory chosen by the runner
        outdir = Path(combined["execution"]["output_directory"]) 
        self._make_output_tree(outdir, required=True, optional=True)

        # Re-run validation explicitly to reflect created files
        validation = self.runner.validate_outputs(str(outdir))
        self.assertTrue(validation["validation_passed"])  

        # Generate a report and check structure
        report = self.runner.generate_report({
            "execution": combined["execution"],
            "validation": validation,
            "overall_success": True,
            "test_timestamp": "2025-01-01T00:00:00"
        })
        self.assertEqual(report["total_tests"], 1)
        self.assertEqual(report["passed_tests"], 1)
        self.assertIn("summary", report)

    # ---------------------------
    # Smoke test for unique directory naming (subject included)
    # ---------------------------
    def test_generate_unique_output_dir_includes_subject(self):
        cmd = "infant_recon_all -s sub-XYZ -all"
        unique = self.runner.generate_unique_output_dir(cmd, base_output_dir=self.tmpdir)
        self.assertIn("sub-XYZ", Path(unique).name)
        self.assertTrue(unique.startswith(self.tmpdir))


if __name__ == "__main__":
    unittest.main(verbosity=2)
