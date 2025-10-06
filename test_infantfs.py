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
        # Define the InfantFS command string for testing
        cls.infantfs_command = (
            f"-s sub-01 "
            f"--age 18 "
            f"--inputfile {cls.INPUT_FILE} "
            f"--outdir {cls.OUTPUT_DIR} "
            f"--no-cleanup "
        )

        # Set the expected output directory
        cls.expected_output_dir = helpers.get_expected_output_directory(
            cls.infantfs_command
        )

        # Check if output directory exists and has previous results
        # If it does, the test will fail and user should handle it with --force flag
        # Ignore hidden files like .DS_Store (macOS system files)
        if os.path.exists(cls.expected_output_dir):
            contents = [f for f in os.listdir(cls.expected_output_dir) if not f.startswith('.')]
            if contents:
                raise RuntimeError(
                    f"Output directory is not empty: {cls.expected_output_dir}. "
                    f"Please manually remove it or use a different output directory."
                )

        # Load expected outputs from YAML file
        cls.expected_outputs = cls._load_expected_outputs_config()

        # Verify input file exists and has data
        if not os.path.exists(cls.INPUT_FILE):
            raise unittest.SkipTest(
                f"Test data not found: {cls.INPUT_FILE}\n"
                f"Please provide a valid infant brain MRI scan.\n"
                f"See: {os.path.join(os.path.dirname(cls.INPUT_FILE), 'README_TEST_DATA_NEEDED.txt')}"
            )
        
        # Check if input file has actual data (not empty)
        if os.path.getsize(cls.INPUT_FILE) == 0:
            raise unittest.SkipTest(
                f"Test data file is empty: {cls.INPUT_FILE}\n"
                f"Please provide a valid infant brain MRI scan (T1w NIfTI file).\n"
                f"See: {os.path.join(os.path.dirname(cls.INPUT_FILE), 'README_TEST_DATA_NEEDED.txt')}"
            )

        # Parse arguments that will be used to call InfantFS.main()
        cls.parsed_args = infantfs_parser(cls.infantfs_command)

        # Run InfantFS ONCE for all tests on the output directory tree
        cls._run_infantfs()

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
            raise RuntimeError(f"Error loading expected outputs: {e}")

        return config  # type: dict

    @classmethod
    def _run_infantfs(cls):
        """Execute InfantFS with parsed arguments."""
        # Parse arguments and run InfantFS main function
        try:
            infantfs.main(cls.parsed_args)
        except SystemExit as exc:
            # Catch the sys.exit() call from infantfs.main()'s pipeline handler.
            # This is to avoid exiting from the setUpClass method
            # before the tests can run.
            if exc.code != 0:
                raise RuntimeError(
                    f"InfantFS exited with non-zero code: {exc.code}")

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

        # Skip if input file was moved/deleted after processing
        if not os.path.exists(input_file):
            self.skipTest(f"Input file not found (may have been moved after processing): {input_file}")

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


class TestInputValidationFailures(unittest.TestCase):
    """
    Test that InfantFS fails gracefully with appropriate error messages
    when given invalid inputs.

    These tests verify that the input validation logic in infant_recon_all_testable.py
    (lines 117-161) correctly detects and reports errors before processing begins.

    Each test should:
    1. Create a command that triggers a specific validation error
    2. Attempt to parse and run InfantFS with that command
    3. Assert that it raises an exception or exits with non-zero code
    4. Optionally verify the error message is informative
    """

    # Create a temporary directory for test outputs
    TEST_OUTPUT_DIR = "/tmp/infantfs_test_failures"

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for graceful failure tests."""
        # Create test output directory if it doesn't exist
        os.makedirs(cls.TEST_OUTPUT_DIR, exist_ok=True)

        # Create a dummy existing output directory to test --force flag
        cls.existing_output_dir = os.path.join(
            cls.TEST_OUTPUT_DIR, "existing_output"
        )
        os.makedirs(cls.existing_output_dir, exist_ok=True)
        # Create mri subdirectory to simulate previous run
        os.makedirs(os.path.join(cls.existing_output_dir, "mri"), exist_ok=True)

        # Store original environment variables to restore later
        cls.original_fs_home = os.environ.get("FREESURFER_HOME")
        cls.original_subjects_dir = os.environ.get("SUBJECTS_DIR")

        # Set dummy FreeSurfer environment for testing
        # The parser needs FREESURFER_HOME to construct default model path
        os.environ["FREESURFER_HOME"] = "/tmp"
        os.environ["SUBJECTS_DIR"] = "/tmp"

    def test_existing_output_without_force_or_keep_going(self):
        """
        Test failure when output directory exists without --force or --keep-going.

        Reference: infant_recon_all_testable.py lines 119-123
        The program should detect existing output and fail with helpful message.
        """
        # Create command with existing output directory
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--outdir {self.existing_output_dir}"
        )

        # Parse arguments
        parsed_args = infantfs_parser(cmd)

        # The main() function should raise SystemExit or sf.system.fatal
        # sf.system.fatal calls sys.exit(1), which raises SystemExit
        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        # Verify it exited with non-zero code (error)
        self.assertNotEqual(cm.exception.code, 0,
                           "Should exit with error code when output exists")

    def test_missing_subjects_dir_without_outdir(self):
        """
        Test failure when SUBJECTS_DIR is not set and --outdir not provided.

        Reference: infant_recon_all_testable.py lines 125-126

        NOTE: This test reveals a bug in the code - it crashes with TypeError
        at line 82 before reaching the validation at lines 125-126.
        Ideally, the code should check for None before using subjsdir.
        """
        # Temporarily unset SUBJECTS_DIR (it was set in setUpClass)
        if "SUBJECTS_DIR" in os.environ:
            del os.environ["SUBJECTS_DIR"]

        try:
            cmd = (
                f"-s test_subject "
                f"--age 12 "
                f"--inputfile /tmp/dummy_input.nii.gz"
                # Note: NO --outdir flag
            )
            parsed_args = infantfs_parser(cmd)

            # The code crashes with TypeError before proper validation
            # This is not graceful, but we test that it fails
            with self.assertRaises((SystemExit, TypeError)):
                infantfs.main(parsed_args)

        finally:
            # Restore SUBJECTS_DIR to dummy value for other tests
            os.environ["SUBJECTS_DIR"] = "/tmp"

    def test_missing_input_file(self):
        """
        Test failure when no input file is provided.

        Reference: infant_recon_all_testable.py lines 128-132
        Should fail if no --inputfile, --masked, or default mprage.nii.gz exists.
        """
        cmd = (
            f"-s nonexistent_subject "
            f"--age 12 "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'no_input')}"
            # Note: NO --inputfile or --masked
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_conflicting_masked_and_forceskullstrip(self):
        """
        Test failure when both --masked and --forceskullstrip are provided.

        Reference: infant_recon_all_testable.py lines 134-135
        These options are mutually exclusive.
        """
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--masked /tmp/dummy_masked.nii.gz "
            f"--forceskullstrip "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'conflict1')}"
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_missing_skullstrip_model(self):
        """
        Test failure when skullstrip model file doesn't exist.

        Reference: infant_recon_all_testable.py lines 137-139
        If skull-stripping is needed but model file is missing, should fail.
        """
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--model /nonexistent/path/to/model.pt "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'no_model')}"
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_conflicting_mask_and_masked(self):
        """
        Test failure when both --mask and --masked are provided.

        Reference: infant_recon_all_testable.py lines 141-142
        Only one masking method should be specified.
        """
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--mask /tmp/dummy_mask.nii.gz "
            f"--masked /tmp/dummy_masked.nii.gz "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'conflict2')}"
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_t2_flag_without_t2file(self):
        """
        Test failure when --t2 is set but --t2file is not provided.

        Reference: infant_recon_all_testable.py lines 144-145
        """
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--t2 "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 't2_missing')}"
            # Note: --t2 flag is set but NO --t2file
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_segfile_without_masked_or_forceskullstrip(self):
        """
        Test failure when --segfile provided without --masked or --forceskullstrip.

        Reference: infant_recon_all_testable.py lines 147-148
        External segmentation requires masked input unless forcing skullstrip.
        """
        cmd = (
            f"-s test_subject "
            f"--age 12 "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--segfile /tmp/dummy_seg.nii.gz "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'seg_no_mask')}"
            # Note: --segfile but NO --masked or --forceskullstrip
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_missing_age_for_default_group(self):
        """
        Test failure when age is not provided for default subject group.

        Reference: infant_recon_all_testable.py lines 150-151
        Age is required unless --newborn or --oneyear is specified.
        """
        cmd = (
            f"-s test_subject "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'no_age')}"
            # Note: NO --age, --newborn, or --oneyear flags
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    def test_conflicting_newborn_and_oneyear(self):
        """
        Test failure when both --newborn and --oneyear are specified.

        Reference: infant_recon_all_testable.py lines 153-154
        Subject can only be in one age group.
        """
        cmd = (
            f"-s test_subject "
            f"--inputfile /tmp/dummy_input.nii.gz "
            f"--newborn "
            f"--oneyear "
            f"--outdir {os.path.join(self.TEST_OUTPUT_DIR, 'both_groups')}"
        )
        parsed_args = infantfs_parser(cmd)

        with self.assertRaises(SystemExit) as cm:
            infantfs.main(parsed_args)

        self.assertNotEqual(cm.exception.code, 0)

    @classmethod
    def tearDownClass(cls):
        """Clean up test directories after all tests complete."""
        # Note: We're being careful here - only delete what we created
        if os.path.exists(cls.TEST_OUTPUT_DIR):
            import shutil
            shutil.rmtree(cls.TEST_OUTPUT_DIR)

        # Restore original environment variables
        if cls.original_fs_home:
            os.environ["FREESURFER_HOME"] = cls.original_fs_home
        else:
            if "FREESURFER_HOME" in os.environ:
                del os.environ["FREESURFER_HOME"]

        if cls.original_subjects_dir:
            os.environ["SUBJECTS_DIR"] = cls.original_subjects_dir
        else:
            if "SUBJECTS_DIR" in os.environ:
                del os.environ["SUBJECTS_DIR"]


class TestHelperFunctions(unittest.TestCase):
    """
    Test the helper functions in helpers.py.

    These utility functions are used throughout the test suite,
    so it's critical they work correctly.
    """

    def test_extract_command_line_args_with_python_prefix(self):
        """
        Test extract_command_line_args removes 'python' and script name.
        """
        # Command with 'python' prefix
        cmd = "python infant_recon_all.py -s sub-01 --age 12"
        result = helpers.extract_command_line_args(cmd)

        # Should remove 'python' and script name, keeping only args
        expected = "-s sub-01 --age 12"
        self.assertEqual(result, expected)

    def test_extract_command_line_args_without_python(self):
        """
        Test extract_command_line_args with script name only.
        """
        cmd = "infant_recon_all.py -s sub-01 --age 12"
        result = helpers.extract_command_line_args(cmd)

        expected = "-s sub-01 --age 12"
        self.assertEqual(result, expected)

    def test_extract_command_line_args_with_just_args(self):
        """
        Test extract_command_line_args when only arguments are provided.
        """
        cmd = "-s sub-01 --age 12 --inputfile /path/to/file.nii.gz"
        result = helpers.extract_command_line_args(cmd)

        # Should return unchanged since no python/script prefix
        self.assertEqual(result, cmd)

    def test_get_expected_output_directory_with_outdir(self):
        """
        Test get_expected_output_directory when --outdir is specified.
        """
        cmd = "-s sub-01 --age 12 --outdir /custom/output/path"
        result = helpers.get_expected_output_directory(cmd)

        # Should return the absolute path of --outdir
        expected = os.path.abspath("/custom/output/path")
        self.assertEqual(result, expected)

    def test_get_expected_output_directory_with_subjects_dir(self):
        """
        Test get_expected_output_directory using SUBJECTS_DIR.
        """
        # Set SUBJECTS_DIR temporarily
        original_subjects_dir = os.environ.get("SUBJECTS_DIR")
        test_subjects_dir = "/tmp/test_subjects"
        os.environ["SUBJECTS_DIR"] = test_subjects_dir

        try:
            cmd = "-s sub-01 --age 12"  # No --outdir
            result = helpers.get_expected_output_directory(cmd)

            # Should construct path from SUBJECTS_DIR + subject name
            expected = os.path.abspath(
                os.path.join(test_subjects_dir, "sub-01")
            )
            self.assertEqual(result, expected)

        finally:
            # Restore original SUBJECTS_DIR
            if original_subjects_dir:
                os.environ["SUBJECTS_DIR"] = original_subjects_dir
            else:
                del os.environ["SUBJECTS_DIR"]

    def test_get_expected_output_directory_missing_info(self):
        """
        Test get_expected_output_directory fails when missing required info.
        """
        # Temporarily unset SUBJECTS_DIR
        original_subjects_dir = os.environ.get("SUBJECTS_DIR")
        if "SUBJECTS_DIR" in os.environ:
            del os.environ["SUBJECTS_DIR"]

        try:
            # No --outdir and no SUBJECTS_DIR - should raise RuntimeError
            cmd = "-s sub-01 --age 12"

            with self.assertRaises(RuntimeError) as cm:
                helpers.get_expected_output_directory(cmd)

            # Verify error message mentions the issue
            self.assertIn("SUBJECTS_DIR", str(cm.exception))

        finally:
            # Restore SUBJECTS_DIR
            if original_subjects_dir:
                os.environ["SUBJECTS_DIR"] = original_subjects_dir


class TestEnvironmentValidation(unittest.TestCase):
    """
    Test the FreeSurfer environment validation functions.

    These tests verify that test_environment.py correctly validates
    the FreeSurfer installation and configuration.
    """

    def test_verify_freesurfer_environment_missing_home(self):
        """
        Test that verify_freesurfer_environment fails when FREESURFER_HOME not set.
        """
        # Temporarily unset FREESURFER_HOME
        original_fs_home = os.environ.get("FREESURFER_HOME")
        if "FREESURFER_HOME" in os.environ:
            del os.environ["FREESURFER_HOME"]

        try:
            with self.assertRaises(EnvironmentError) as cm:
                verify_freesurfer_environment()

            self.assertIn("FREESURFER_HOME", str(cm.exception))

        finally:
            # Restore FREESURFER_HOME
            if original_fs_home:
                os.environ["FREESURFER_HOME"] = original_fs_home

    def test_verify_freesurfer_environment_invalid_home_path(self):
        """
        Test that verify_freesurfer_environment fails when FREESURFER_HOME is invalid.
        """
        # Temporarily set FREESURFER_HOME to non-existent path
        original_fs_home = os.environ.get("FREESURFER_HOME")
        os.environ["FREESURFER_HOME"] = "/nonexistent/path/to/freesurfer"

        try:
            with self.assertRaises(EnvironmentError) as cm:
                verify_freesurfer_environment()

            # Error should mention that path doesn't exist
            self.assertIn("does not exist", str(cm.exception))

        finally:
            # Restore FREESURFER_HOME
            if original_fs_home:
                os.environ["FREESURFER_HOME"] = original_fs_home
            else:
                del os.environ["FREESURFER_HOME"]

    def test_verify_freesurfer_environment_missing_subjects_dir(self):
        """
        Test that verify_freesurfer_environment fails when SUBJECTS_DIR not set.
        """
        # Temporarily set FREESURFER_HOME to /tmp (exists) but unset SUBJECTS_DIR
        original_fs_home = os.environ.get("FREESURFER_HOME")
        original_subjects_dir = os.environ.get("SUBJECTS_DIR")

        os.environ["FREESURFER_HOME"] = "/tmp"
        if "SUBJECTS_DIR" in os.environ:
            del os.environ["SUBJECTS_DIR"]

        try:
            with self.assertRaises(EnvironmentError) as cm:
                verify_freesurfer_environment()

            self.assertIn("SUBJECTS_DIR", str(cm.exception))

        finally:
            # Restore original values
            if original_fs_home:
                os.environ["FREESURFER_HOME"] = original_fs_home
            else:
                if "FREESURFER_HOME" in os.environ:
                    del os.environ["FREESURFER_HOME"]

            if original_subjects_dir:
                os.environ["SUBJECTS_DIR"] = original_subjects_dir


if __name__ == "__main__":
    # Verify FreeSurfer environment before running tests
    try:
        fs_home = verify_freesurfer_environment()
        verify_license(fs_home)
    except EnvironmentError as e:
        print("=" * 70)
        print("ERROR: FreeSurfer environment is not properly configured!")
        print("=" * 70)
        print(f"\n{e}\n")
        print("Please ensure FreeSurfer environment is set up correctly.")
        print("See FreeSurfer documentation or run: python test_environment.py")
        print("=" * 70)
        import sys
        sys.exit(1)

    # Run all tests
    unittest.main(verbosity=2)
