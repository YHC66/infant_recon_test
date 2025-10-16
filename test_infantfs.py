#!/usr/bin/env python

# IMPORTS

import os
import unittest
import shlex
import yaml


# LOCAL IMPORTS

import helpers
import infant_recon_all_testable as infantfs
from test_environment import verify_freesurfer_environment, verify_license

# Import coverage conditionally
try:
    import coverage
except ImportError:
    coverage = None


# AUXILIARY FUNCTIONS


def infantfs_parser(cmd_str):
    """
    Parse command-line arguments from a string using InfantFS's argument parser.

    Args:
        command_line_str (str): The command line string to parse.

    Returns:
        argparse.Namespace: The parsed arguments.
    """
    # Create parser using real FreeSurfer environment
    parser = infantfs.create_cli()
    # Convert it into a list of args safely (as the shell would do)
    args_list = shlex.split(cmd_str)
    # Parse as if it came from the shell
    parsed = parser.parse_args(args_list)

    return parsed  # type: argparse.Namespace


# UNIT TESTS


class TestOutputDirectoryTree(unittest.TestCase):
    """
    Test class for actual InfantFS execution with output validation.

    1. Define an InfantFS command in setUpClass (runs ONCE)
    2. Use get_expected_output_directory to determine where outputs should be
    3. Test for expected files and directories in that location

    """

    # Define constants for test data and output directories
    # These should be easy to change for different test setups (computers)

    # --- Yihang's setup (ACTIVE) --------------------------------------------
    # TODO: Configure these paths for your test setup via environment variables
    #       or a configuration file instead of hard-coding them here
    INPUT_FILE = os.getenv(
        "INFANTFS_TEST_INPUT",
        "/Users/cyh/Desktop/infant_recon_test/sub-01/anat/sub-01_T1w.nii.gz"
    )
    OUTPUT_DIR = os.getenv(
        "INFANTFS_TEST_OUTPUT",
        "/Users/cyh/Desktop/infant_recon_test/test_execution_output"
    )

    # --- Istvan's setup --------------------------------------------
    # INPUT_FILE = (
    #     "/autofs/vast/lzgroup/Users/IstvanHuszar/fitng/ds004776-download/"
    #     "sub-01/anat/sub-01_T1w.nii.gz"
    # )
    # OUTPUT_DIR = (
    #     "/autofs/vast/lzgroup/Users/IstvanHuszar/results/infantfs/full_run2"
    # )

    @classmethod
    def setUpClass(cls):
        """
        Set up test fixtures ONCE for the entire test class.

        This runs InfantFS only once, then all tests validate the same output.
        """
        print("=" * 60)
        print("Setting up InfantFS execution for all tests")
        print("=" * 60)

        # Define the InfantFS command string for testing
        cls.infantfs_command = (
            f"-s sub-01 "
            f"--age 18 "
            f"--inputfile {cls.INPUT_FILE} "
            f"--outdir {cls.OUTPUT_DIR} "
            f"--no-cleanup "
        )

        # Set the expected output directory
        # If this fails, no point in continuing...
        cls.expected_output_dir = helpers.get_expected_output_directory(
            cls.infantfs_command
        )

        # Ensure the output directory is clean before running tests
        # Requiring it to be empty is safer than deleting it outright
        if os.path.exists(cls.expected_output_dir):
            if not os.listdir(cls.expected_output_dir):
                raise RuntimeError(
                    f"Output directory is not empty: {cls.expected_output_dir}"
                )

        # Load expected outputs from YAML file
        # If it fails, no point in continuing...
        cls.expected_outputs = cls._load_expected_outputs_config()

        # Parse arguments that will be used to call InfantFS.main()
        cls.parsed_args = infantfs_parser(cls.infantfs_command)

        # Run InfantFS ONCE for all tests on the output directory tree
        # THIS IS LONG (~1 hour), so we do it only once
        try:
            cls._run_infantfs()
        except Exception as e:
            print(f"⚠️ InfantFS execution failed: {e}")
            print(
                f"Tests will check expected structure but may fail due to "
                "missing files"
            )
        print("=" * 60)

    @staticmethod
    def _load_expected_outputs_config():
        """
        Load expected outputs configuration from YAML file.
        """
        config_file_name = "expected_outputs.yaml"
        config_file = os.path.join(os.path.dirname(__file__), config_file_name)
        try:
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            raise RuntimeError(f"Error loading expected outputs from: {e}")

        return config  # type: dict

    @classmethod
    def _run_infantfs(cls):
        print(
            f" Starting InfantFS execution with command: "
            f"{cls.infantfs_command}"
        )
        print("  This may take ~1 hour")

        # Parse arguments and run InfantFS main function
        try:
            infantfs.main(cls.parsed_args)
        except SystemExit as exc:
            # Catch the sys.exit() call from infantfs.main()'s pipline handler.
            # This is to avoid exiting from the setUpClass method
            # before the tests can run.            
            if exc.code != 0:
                raise RuntimeError(
                    f"InfantFS exited with non-zero code: {exc.code}")

        print(f"✅ InfantFS execution completed successfully")
        print(" All tests will now validate this output")

    # --------------------------- Test methods ------------------------------ #

    def test_command_parsing(self):
        """Test that our command parsing works correctly."""
        self.assertEqual(self.parsed_args.s, "sub-01")
        self.assertEqual(self.parsed_args.age, 18)
        self.assertTrue(hasattr(self.parsed_args, "no_cleanup"))
        self.assertTrue(self.parsed_args.no_cleanup)

    def test_input_file_exists(self):
        """Test that the input file specified in command exists."""
        input_file = self.parsed_args.inputfile
        self.assertTrue(
            os.path.exists(input_file), f"Input file should exist: {input_file}"
        )
        self.assertTrue(
            input_file.endswith(".nii.gz"), "Input file should be a NIfTI file"
        )

    def test_output_directory_exists(self):
        """Test that the output directory exists."""
        self.assertTrue(
            os.path.exists(self.expected_output_dir),
            f"Output directory should exist: {self.expected_output_dir}",
        )

    def test_subdirs_exist(self):
        """Test that all required subdirectories exist in output directory."""
        required_dirs = self.expected_outputs.get("required_directories", [])
        for dir_name in required_dirs:
            dir_path = os.path.join(self.expected_output_dir, dir_name)
            with self.subTest(directory=dir_name):
                self.assertTrue(
                    os.path.isdir(dir_path),
                    f"Required subdirectory missing: {dir_name} at {dir_path}",
                )

    def test_mri_subdir_files(self):
        """Test that all required MRI files exist in mri subdirectory."""
        mri_files = self.expected_outputs["required_files"]["mri"]
        mri_dir = os.path.join(self.expected_output_dir, "mri")

        for file_name in mri_files:
            file_path = os.path.join(mri_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required MRI file missing: {file_name} at {file_path}",
                )

    def test_mri_transforms_subdir_files(self):
        """Test that all required transform files exist in mri/transforms subdirectory."""
        transform_files = self.expected_outputs["required_files"][
            "mri/transforms"
        ]
        transforms_dir = os.path.join(
            self.expected_output_dir, "mri", "transforms"
        )

        for file_name in transform_files:
            file_path = os.path.join(transforms_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required transform file missing: "
                    f"{file_name} at {file_path}",
                )

    def test_surf_subdir_files(self):
        """Test that all required surface files exist in surf subdirectory."""
        surf_files = self.expected_outputs["required_files"]["surf"]
        surf_dir = os.path.join(self.expected_output_dir, "surf")

        for file_name in surf_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required surface file missing: "
                    f"{file_name} at {file_path}",
                )

    def test_label_subdir_files(self):
        """Test that all required label files exist in label subdirectory."""
        label_files = self.expected_outputs["required_files"]["label"]
        label_dir = os.path.join(self.expected_output_dir, "label")

        for file_name in label_files:
            file_path = os.path.join(label_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required label file missing: "
                    f"{file_name} at {file_path}",
                )

    def test_log_subdir_files(self):
        """Test that all required log files exist in log subdirectory."""
        log_files = self.expected_outputs["required_files"]["log"]
        log_dir = os.path.join(self.expected_output_dir, "log")

        for file_name in log_files:
            file_path = os.path.join(log_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required log file missing: {file_name} at {file_path}",
                )

    def test_stats_subdir_files(self):
        """Test that all required stats files exist in stats subdirectory."""
        stats_files = self.expected_outputs["required_files"]["stats"]
        stats_dir = os.path.join(self.expected_output_dir, "stats")

        for file_name in stats_files:
            file_path = os.path.join(stats_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required stats file missing: {file_name} at {file_path}",
                )

    def test_root_directory_files(self):
        """Test that all required files exist in root output directory."""
        root_files = self.expected_outputs["required_files"]["."]

        for file_name in root_files:
            file_path = os.path.join(self.expected_output_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(
                    os.path.isfile(file_path),
                    f"Required root file missing: {file_name} at {file_path}",
                )

    # TODO: Some outputs are missing from your expected_outputs.yaml
    # Run infantfs to see what's missing, add them to the yaml file,
    # and complete the missing tests here.


# TODO: Implement further test classes to increase code coverage
# Write new classes to test "graceful failures". A graceful failure is when
# the program detects that it can't run (e.g., missing input file, invalid
# age, etc.) and raises an exception or exits cleanly instead of crashing.
# Look at the implementation of infant_recon_all_testable.py, see where these
# if statements are, and construct commands that would make the program fail
# at these points.


if __name__ == "__main__":

    # Verify FreeSurfer environment before running tests
    fs_home = verify_freesurfer_environment()
    verify_license(fs_home)

    # Try to use coverage if available, otherwise run tests without it
    if coverage:
        try:
            # Start coverage tracking
            cov = coverage.Coverage()
            cov.start()
            coverage_available = True
        except Exception as e:
            print(f"Coverage initialization failed: {e}")
            coverage_available = False
    else:
        print(
            "Coverage module not available, running tests without coverage tracking."
        )
        coverage_available = False

    # Run all tests
    try:
        unittest.main(verbosity=2, exit=False)
    except Exception as e:
        print(f"Test execution failed: {e}")

    if coverage_available:
        # Stop coverage tracking and generate report
        cov.stop()
        cov.save()

        # Generate HTML report
        html_report_dir = os.path.join(
            os.path.dirname(__file__), "htmlcov_quick"
        )
        cov.html_report(directory=html_report_dir)

        print(
            f"Look at the HTML coverage report generated at: "
            f"{html_report_dir}/index.html"
        )

    print("Done.")
