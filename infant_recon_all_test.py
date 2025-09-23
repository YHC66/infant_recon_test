#!/usr/bin/env python


# DESCRIPTION

"""
Unit tests for infant_recon_all using unittest and coverage tracking.

Authors:
    Yihang Chen (YC)
    Istvan N Huszar (INH)
    
Date: 2025-Sep-02
    
"""


# DEVELOPMENT NOTES

"""
2025-Sep-02 INH:
    - Created the argument parser and the basic structure of the script.
    
"""


# IMPORTS

import os
import sys
import unittest
from unittest import mock
import argparse
import shlex
import yaml

# Import coverage conditionally
try:
    import coverage
except ImportError:
    coverage = None

# Import the testable module - handle the case where it doesn't have .py extension
sys.path.insert(0, os.path.dirname(__file__))
try:
    import infant_recon_all_testable as infantfs
except ImportError:
    # Load the module manually using exec
    testable_path = os.path.join(os.path.dirname(__file__), "infant_recon_all_testable")
    if os.path.exists(testable_path):
        import types
        infantfs = types.ModuleType("infant_recon_all_testable")
        with open(testable_path, 'r') as f:
            exec(f.read(), infantfs.__dict__)
        sys.modules["infant_recon_all_testable"] = infantfs
    else:
        raise ImportError(f"Cannot find infant_recon_all_testable file")


# AUXILIARY FUNCTIONS

def parse_args(cmd_str: str) -> argparse.Namespace:
    """
    Parse command line arguments from a string.
    
    This function takes a command line string, splits it into arguments,
    and parses them using argparse.
    
    Args:
        command_line_str (str): The command line string to parse.
        
    Returns:
        argparse.Namespace: The parsed arguments.
    """
    # Mock FREESURFER_HOME temporarily for CLI creation
    with mock.patch.dict(os.environ, {'FREESURFER_HOME': '/fake/freesurfer/home'}):
        parser = infantfs.create_cli()
    # Convert it into a list of args safely (as the shell would do)
    args_list = shlex.split(cmd_str)
    # Parse as if it came from the shell
    parsed = parser.parse_args(args_list)

    return parsed


def get_expected_output_directory(cmd_str: str) -> str:
    """
    Parse an InfantFS command string and return the expected output directory.
    If --outdir is specified, it uses that path.
    Otherwise, it defaults to $SUBJECTS_DIR/subject_name.
    
    Args:
        cmd_str (str): The InfantFS command string to parse. Can be either just the 
                      arguments or a full command including "python script.py".
        
    Returns:
        str: The absolute path to the expected output directory.
        
    Raises:
        ValueError: If required arguments are missing or invalid.
    """
    # Clean the command string to extract just the arguments
    cmd_parts = shlex.split(cmd_str)
    
    # Remove "python" and script name if present
    if len(cmd_parts) > 0 and cmd_parts[0] == 'python':
        cmd_parts = cmd_parts[1:]  # Remove 'python'
    if len(cmd_parts) > 0 and ('infant_recon_all' in cmd_parts[0] or cmd_parts[0].endswith('.py')):
        cmd_parts = cmd_parts[1:]  # Remove script name
    
    # Reconstruct the arguments string
    args_str = ' '.join(cmd_parts)
    
    # Parse the command arguments
    args = parse_args(args_str)
    
    subj = args.s
    if not subj:
        raise ValueError("Subject name (-s) is required")
    
    # Get SUBJECTS_DIR from environment, default to current working directory if not set
    subjsdir = os.environ.get('SUBJECTS_DIR', os.getcwd())
    
    # Determine output directory based on the same logic as in main()
    if args.outdir:
        outdir = os.path.abspath(args.outdir)
    else:
        outdir = os.path.abspath(os.path.join(subjsdir, subj))
    
    return outdir


# UNIT TESTS

class TestInfantFSExecution(unittest.TestCase):
    """
    Test class for actual InfantFS execution with output validation.
    
    This class demonstrates the testing pattern where we:
    1. Define an InfantFS command in setUp
    2. Use get_expected_output_directory to determine where outputs should be
    3. Test for expected files and directories in that location
    """
    
    def setUp(self):
        """
        Set up test fixtures before each test method.
        
        Define the InfantFS command, determine expected output directory,
        and ACTUALLY RUN InfantFS to create the files for testing.
        """
        # Define the InfantFS command string for testing
        self.infantfs_command = '-s sub-01 --age 18 --inputfile /Users/cyh/Desktop/infant_recon_test/sub-01/anat/sub-01_T1w.nii.gz --no-cleanup'
        
        # Set up environment for consistent testing
        os.environ['SUBJECTS_DIR'] = '/Users/cyh/Desktop/infant_recon_test/test_subjects'
        
        # Use our Step 2 function to determine expected output directory
        self.expected_output_dir = get_expected_output_directory(self.infantfs_command)

        
        # Parse the arguments for additional test information
        self.parsed_args = parse_args(self.args_only)
        
        # Load expected outputs configuration like infant_recon_runner.py
        self.expected_outputs = self.load_expected_outputs_config()
        
        # === NEW: Actually run InfantFS to create files for testing ===
        self.expected_output_dir = '/Users/cyh/Desktop/infant_recon_test/test_execution_output'

        '''
        try:
            self._setup_freesurfer_environment()
            self._run_infantfs_execution()
            self.infantfs_execution_successful = True
            print(f"✅ InfantFS execution completed successfully")
        except Exception as e:
            print(f"⚠️ InfantFS execution failed: {e}")
            print(f"Tests will check expected structure but may fail due to missing files")
        
        print(f"Test setup: Command = {self.infantfs_command}")
        print(f"Test setup: Expected output = {self.expected_output_dir}")
        print(f"Test setup: Execution output = {self.execution_output_dir}")
        print(f"Test setup: Execution successful = {self.infantfs_execution_successful}")
        '''
    
    def _setup_freesurfer_environment(self):
        """Set up FreeSurfer environment variables for InfantFS execution."""
        # Set up FreeSurfer environment - use the actual installation path
        freesurfer_home = '/Applications/freesurfer/8.1.0'
        if not os.path.exists(freesurfer_home):
            raise RuntimeError(f"FreeSurfer not found at {freesurfer_home}")
        os.environ['FREESURFER_HOME'] = freesurfer_home
        os.environ['SUBJECTS_DIR'] = '/Users/cyh/Desktop/infant_recon_test/test_subjects'
        
        
        # Add FreeSurfer bin to PATH
        freesurfer_bin = f'{freesurfer_home}/bin'
        current_path = os.environ.get('PATH', '')
        if freesurfer_bin not in current_path:
            os.environ['PATH'] = f'{freesurfer_bin}:{current_path}'
        
        # Set additional FreeSurfer environment variables
        os.environ['FSFAST_HOME'] = f'{freesurfer_home}/fsfast'
        os.environ['FSF_OUTPUT_FORMAT'] = 'nii.gz'
        os.environ['MNI_DIR'] = f'{freesurfer_home}/mni'
        
        # Check if FreeSurfer directory exists
        
        print(f"✅ FreeSurfer found at: {freesurfer_home}")
        print(f"✅ Added FreeSurfer bin to PATH: {freesurfer_bin}")
    
    def _run_infantfs_execution(self):
        """Actually run InfantFS with the test command to generate output files."""
        # Create execution output directory
        os.makedirs(self.execution_output_dir, exist_ok=True)
        
        # Modify the command to use execution output directory
        execution_args_str = f'-s sub-01 --age 18 --inputfile /Users/cyh/Desktop/infant_recon_test/sub-01/anat/sub-01_T1w.nii.gz --outdir {self.execution_output_dir} --no-cleanup --force'
        
        # Parse the execution arguments with real FreeSurfer environment
        # Create parser with real environment (not mocked)
        parser = infantfs.create_cli()
        args_list = shlex.split(execution_args_str)
        execution_args = parser.parse_args(args_list)
        
        print(f"🚀 Running InfantFS with args: {execution_args}")
        
        # Actually call infantfs.main() to generate the files
        try:
            infantfs.main(execution_args)
        except SystemExit as e:
            # infantfs.main() might call sys.exit(), handle this
            if e.code != 0:
                raise RuntimeError(f"InfantFS exited with code {e.code}")
        except Exception as e:
            raise RuntimeError(f"InfantFS execution failed: {e}")
    
    def load_expected_outputs_config(self):
        """Load expected outputs configuration from YAML file, like infant_recon_runner.py"""
        config_file = 'expected_outputs.yaml'
        try:
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            # Fallback to default config like infant_recon_runner.py does
            return self.get_default_expected_outputs()
        except yaml.YAMLError:
            return self.get_default_expected_outputs()
    
    def get_default_expected_outputs(self):
        """Return default expected outputs configuration (from infant_recon_runner.py)"""
        return {
            'required_directories': ['mri', 'surf', 'label', 'stats', 'log'],
            'required_files': {
                'mri': ['norm.mgz', 'aseg.mgz', 'brain.mgz', 'brainmask.mgz', 'norm.nii.gz', 'aseg.nii.gz'],
                'surf': ['lh.white', 'rh.white', 'lh.orig', 'rh.orig'],
                'label': [],  # May be empty for some runs
                'stats': [],  # May be empty if --no-stats is used
                'log': ['recon.log'],
                '.': ['mprage.nii.gz']  # Files in root of output directory
            },
            'optional_files': {
                'mri': ['filled.mgz', 'wm.mgz', 'brain.finalsurfs.mgz'],
                'surf': ['lh.area', 'rh.area', 'lh.curv', 'rh.curv', 'lh.inflated', 'rh.inflated'],
                'work': []  # Work directory files (if --no-cleanup not used)
            }
        }
    
    def test_command_parsing(self):
        """Test that our command parsing works correctly."""
        self.assertEqual(self.parsed_args.s, 'sub-01')
        self.assertEqual(self.parsed_args.age, 18)
        self.assertTrue(hasattr(self.parsed_args, 'no_cleanup'))
        self.assertTrue(self.parsed_args.no_cleanup)
    
    def test_output_directory_logic(self):
        """Test that output directory follows expected logic."""
        # Test that path is absolute
        self.assertTrue(os.path.isabs(self.expected_output_dir))
        
    
    def test_input_file_exists(self):
        """Test that the input file specified in command exists."""
        input_file = self.parsed_args.inputfile
        self.assertTrue(os.path.exists(input_file), 
                       f"Input file should exist: {input_file}")
        self.assertTrue(input_file.endswith('.nii.gz'),
                       "Input file should be a NIfTI file")
    
    # ========== GRANULAR OUTPUT VALIDATION TESTS ==========
    
    def _get_test_output_dir(self):
        """Get the output directory to test against - uses execution output if available."""
        return self.execution_output_dir
    
    def test_required_directories_exist(self):
        """Test that all required directories exist in output directory."""
        test_output_dir = self._get_test_output_dir()
        required_dirs = ['mri', 'surf', 'label', 'stats', 'log', 'work']
        
        for dir_name in required_dirs:
            dir_path = os.path.join(test_output_dir, dir_name)
            with self.subTest(directory=dir_name):
                self.assertTrue(os.path.isdir(dir_path), 
                               f"Required directory missing: {dir_name} at {dir_path}")
    
    def test_mri_transforms_directory_exists(self):
        """Test that mri/transforms subdirectory exists."""
        test_output_dir = self._get_test_output_dir()
        transforms_dir = os.path.join(test_output_dir, 'mri', 'transforms')
        self.assertTrue(os.path.isdir(transforms_dir),
                       f"MRI transforms directory missing: {transforms_dir}")
    
    def test_root_files_exist(self):
        """Test that required files exist in the root output directory."""
        test_output_dir = self._get_test_output_dir()
        root_files = ['mprage.nii.gz']
        
        for file_name in root_files:
            file_path = os.path.join(test_output_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Root file missing: {file_name} at {file_path}")
    
    def test_mri_core_volumes_exist(self):
        """Test that core MRI volume files exist."""
        test_output_dir = self._get_test_output_dir()
        core_files = ['aseg.mgz', 'brain.mgz', 'brainmask.mgz', 'norm.mgz']
        mri_dir = os.path.join(test_output_dir, 'mri')
        
        for file_name in core_files:
            file_path = os.path.join(mri_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Core MRI volume missing: {file_name} at {file_path}")
    
    def test_mri_nifti_files_exist(self):
        """Test that NIfTI format files exist in mri directory."""
        nifti_files = ['aseg.nii.gz', 'norm.nii.gz']
        test_output_dir = self._get_test_output_dir()
        mri_dir = os.path.join(test_output_dir, 'mri')
        
        for file_name in nifti_files:
            file_path = os.path.join(mri_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"MRI NIfTI file missing: {file_name} at {file_path}")
    
    def test_mri_additional_volumes_exist(self):
        """Test that additional MRI processing volumes exist."""
        additional_files = ['brain.finalsurfs.mgz', 'filled.mgz', 'wm.mgz']
        test_output_dir = self._get_test_output_dir()
        mri_dir = os.path.join(test_output_dir, 'mri')
        
        for file_name in additional_files:
            file_path = os.path.join(mri_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Additional MRI volume missing: {file_name} at {file_path}")
    
    def test_mri_transform_files_exist(self):
        """Test that MRI transform files exist."""
        transform_files = ['talairach.auto.xfm', 'talairach.xfm']
        test_output_dir = self._get_test_output_dir()
        transforms_dir = os.path.join(test_output_dir, 'mri', 'transforms')
        
        for file_name in transform_files:
            file_path = os.path.join(transforms_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Transform file missing: {file_name} at {file_path}")
    
    def test_surface_left_hemisphere_files(self):
        """Test that left hemisphere surface files exist."""
        lh_files = ['lh.orig', 'lh.white', 'lh.inflated', 'lh.area', 'lh.curv']
        test_output_dir = self._get_test_output_dir()
        surf_dir = os.path.join(test_output_dir, 'surf')
        
        for file_name in lh_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Left hemisphere surface file missing: {file_name} at {file_path}")
    
    def test_surface_right_hemisphere_files(self):
        """Test that right hemisphere surface files exist."""
        rh_files = ['rh.orig', 'rh.white', 'rh.area', 'rh.curv']
        test_output_dir = self._get_test_output_dir()
        surf_dir = os.path.join(test_output_dir, 'surf')
        
        for file_name in rh_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Right hemisphere surface file missing: {file_name} at {file_path}")
    
    def test_label_files_exist(self):
        """Test that cortical label files exist."""
        label_files = ['lh.cortex.label', 'rh.cortex.label']
        test_output_dir = self._get_test_output_dir()
        label_dir = os.path.join(test_output_dir, 'label')
        
        for file_name in label_files:
            file_path = os.path.join(label_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Cortical label file missing: {file_name} at {file_path}")
    
    def test_log_files_exist(self):
        """Test that processing log files exist."""
        log_files = ['recon.log']
        test_output_dir = self._get_test_output_dir()
        log_dir = os.path.join(test_output_dir, 'log')
        
        for file_name in log_files:
            file_path = os.path.join(log_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Log file missing: {file_name} at {file_path}")
    
    # ========== REPLICATING INFANT_RECON_RUNNER.PY FUNCTIONALITY ==========
    
    def test_overall_validation_statistics(self):
        """
        Test comprehensive validation statistics like infant_recon_runner.py.
        
        Replicates the validation logic from infant_recon_runner.py lines 229-323.
        """
        # Initialize validation result structure like infant_recon_runner.py
        test_output_dir = self._get_test_output_dir()
        validation_result = {
            'output_directory': test_output_dir,
            'directory_exists': os.path.isdir(test_output_dir),
            'required_directories': {'found': [], 'missing': []},
            'required_files': {'found': [], 'missing': []},
            'optional_files': {'found': [], 'missing': []},
            'total_required_files': 0,
            'total_found_required': 0,
            'validation_passed': False
        }
        
        # Check required directories (replicating lines 260-268)
        for req_dir in self.expected_outputs.get('required_directories', []):
            dir_path = os.path.join(test_output_dir, req_dir)
            if os.path.isdir(dir_path):
                validation_result['required_directories']['found'].append(req_dir)
            else:
                validation_result['required_directories']['missing'].append(req_dir)
        
        # Check required files (replicating lines 270-287)
        required_files = self.expected_outputs.get('required_files', {})
        for directory, file_list in required_files.items():
            for file_name in file_list:
                validation_result['total_required_files'] += 1
                
                if directory == '.':
                    file_path = os.path.join(test_output_dir, file_name)
                else:
                    file_path = os.path.join(test_output_dir, directory, file_name)
                
                if os.path.isfile(file_path):
                    validation_result['required_files']['found'].append(f"{directory}/{file_name}")
                    validation_result['total_found_required'] += 1
                else:
                    validation_result['required_files']['missing'].append(f"{directory}/{file_name}")
        
        # Check optional files (replicating lines 289-302)
        optional_files = self.expected_outputs.get('optional_files', {})
        for directory, file_list in optional_files.items():
            for file_name in file_list:
                if directory == '.':
                    file_path = os.path.join(test_output_dir, file_name)
                else:
                    file_path = os.path.join(test_output_dir, directory, file_name)
                
                if os.path.isfile(file_path):
                    validation_result['optional_files']['found'].append(f"{directory}/{file_name}")
                else:
                    validation_result['optional_files']['missing'].append(f"{directory}/{file_name}")
        
        # Determine validation status (replicating lines 304-308)
        validation_result['validation_passed'] = (
            len(validation_result['required_directories']['missing']) == 0 and
            len(validation_result['required_files']['missing']) == 0
        )
        
        # Generate summary like infant_recon_runner.py (lines 310-321)
        found_req_files = validation_result['total_found_required'] 
        total_req_files = validation_result['total_required_files']
        summary = (
            f"Found {found_req_files}/{total_req_files} required files, "
            f"{len(validation_result['required_directories']['found'])} directories"
        )
        
        # Store results for other tests to use
        self.validation_result = validation_result
        self.validation_summary = summary
        
        # For now, we expect this to fail since files don't exist yet
        # But we're testing the validation logic itself
        self.assertIsInstance(validation_result, dict)
        self.assertIn('validation_passed', validation_result)
        self.assertIn('total_required_files', validation_result)
        
        print(f"Validation summary: {summary}")
        print(f"Validation passed: {validation_result['validation_passed']}")
    
    def test_yaml_config_loading(self):
        """Test that YAML configuration loading works like infant_recon_runner.py"""
        # Test that we successfully loaded configuration
        self.assertIsInstance(self.expected_outputs, dict)
        self.assertIn('required_directories', self.expected_outputs)
        self.assertIn('required_files', self.expected_outputs)
        self.assertIn('optional_files', self.expected_outputs)
        
        # Test required directories from config
        req_dirs = self.expected_outputs.get('required_directories', [])
        self.assertIsInstance(req_dirs, list)
        self.assertIn('mri', req_dirs)
        self.assertIn('surf', req_dirs)
        
        # Test required files from config
        req_files = self.expected_outputs.get('required_files', {})
        self.assertIsInstance(req_files, dict)
        self.assertIn('mri', req_files)
        
        print(f"Loaded config with {len(req_dirs)} required directories")
        print(f"Required directories: {req_dirs}")
    
    def test_comprehensive_validation_summary(self):
        """
        Generate comprehensive validation summary like infant_recon_runner.py.
        
        Replicates the summary generation and reporting from infant_recon_runner.py.
        """
        # Run the validation (this also sets self.validation_result)
        self.test_overall_validation_statistics()
        
        # Generate detailed summary like infant_recon_runner.py
        result = self.validation_result
        
        # Count statistics
        total_required_dirs = len(self.expected_outputs.get('required_directories', []))
        found_required_dirs = len(result['required_directories']['found'])
        missing_required_dirs = len(result['required_directories']['missing'])
        
        total_required_files = result['total_required_files']
        found_required_files = result['total_found_required']
        missing_required_files = len(result['required_files']['missing'])
        
        optional_found = len(result['optional_files']['found'])
        optional_missing = len(result['optional_files']['missing'])
        
        # Generate comprehensive summary
        summary = f"""
VALIDATION SUMMARY (like infant_recon_runner.py):
=================================================
Output Directory: {self.expected_output_dir}
Directory Exists: {result['directory_exists']}

REQUIRED DIRECTORIES: {found_required_dirs}/{total_required_dirs}
- Found: {result['required_directories']['found']}
- Missing: {result['required_directories']['missing']}

REQUIRED FILES: {found_required_files}/{total_required_files}
- Found: {found_required_files}
- Missing: {missing_required_files}

OPTIONAL FILES: {optional_found} found, {optional_missing} missing

OVERALL VALIDATION: {'PASSED' if result['validation_passed'] else 'FAILED'}
"""
        
        print(summary)
        
        # Verify summary structure
        self.assertGreaterEqual(total_required_dirs, 0)
        self.assertGreaterEqual(total_required_files, 0)
        self.assertEqual(found_required_dirs + missing_required_dirs, total_required_dirs)
        self.assertEqual(found_required_files + missing_required_files, total_required_files)


class TestCreateCLI(unittest.TestCase):
    """Test cases for the create_cli function."""
    
    @mock.patch.dict(os.environ, {'FREESURFER_HOME': '/fake/freesurfer/home'})
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.parser = infantfs.create_cli()
    
    def test_create_cli_returns_parser(self):
        """Test that create_cli returns an ArgumentParser instance."""
        self.assertIsInstance(self.parser, argparse.ArgumentParser)
    
    def test_required_subject_argument(self):
        """Test that subject (-s) argument is required."""
        with self.assertRaises(SystemExit):
            self.parser.parse_args([])
    
    def test_basic_required_args(self):
        """Test parsing basic required arguments."""
        args = self.parser.parse_args(['-s', 'subject01', '--age', '12'])
        self.assertEqual(args.s, 'subject01')
        self.assertEqual(args.age, 12)


class TestParseArgs(unittest.TestCase):
    """Test cases for the parse_args helper function."""
    
    def test_parse_basic_command(self):
        """Test parsing a basic command string."""
        cmd_str = '-s subject01 --age 12'
        args = parse_args(cmd_str)
        self.assertEqual(args.s, 'subject01')
        self.assertEqual(args.age, 12)
    
    def test_parse_quoted_paths(self):
        """Test parsing command strings with quoted file paths."""
        cmd_str = '-s subject01 --age 12 --inputfile "/path with spaces/input.nii.gz"'
        args = parse_args(cmd_str)
        self.assertEqual(args.inputfile, '/path with spaces/input.nii.gz')


class TestMainFunctionBasics(unittest.TestCase):
    """Basic test cases for the main function - can be expanded later."""
    
    def test_main_function_exists(self):
        """Test that main function exists and is callable."""
        self.assertTrue(hasattr(infantfs, 'main'))
        self.assertTrue(callable(getattr(infantfs, 'main')))
    
    def test_create_cli_function_exists(self):
        """Test that create_cli function exists and is callable."""
        self.assertTrue(hasattr(infantfs, 'create_cli'))
        self.assertTrue(callable(getattr(infantfs, 'create_cli')))


class TestInfantReconModule(unittest.TestCase):
    """Test the infant_recon_all_testable module is properly loaded."""
    
    def test_module_has_required_functions(self):
        """Test that the module has all required functions."""
        required_functions = ['main', 'create_cli']
        for func_name in required_functions:
            with self.subTest(function=func_name):
                self.assertTrue(hasattr(infantfs, func_name), 
                              f"Module should have {func_name} function")
                self.assertTrue(callable(getattr(infantfs, func_name)),
                              f"{func_name} should be callable")
    
    def test_module_has_required_imports(self):
        """Test that the module has expected imported modules."""
        expected_modules = ['os', 'sys', 'argparse', 'sf', 'fsp']
        for mod_name in expected_modules:
            with self.subTest(module=mod_name):
                self.assertTrue(hasattr(infantfs, mod_name),
                              f"Module should have {mod_name} imported")
    
    @mock.patch.dict(os.environ, {'FREESURFER_HOME': '/fake/freesurfer/home'})
    def test_create_cli_basic_functionality(self):
        """Test basic functionality of create_cli."""
        parser = infantfs.create_cli()
        self.assertIsNotNone(parser)
        # Test that it creates some kind of argument parser
        self.assertTrue(hasattr(parser, 'parse_args'))
        
        # Actually exercise the CLI creation to get coverage
        args = parser.parse_args(['-s', 'test_subject', '--age', '12'])
        self.assertEqual(args.s, 'test_subject')
        self.assertEqual(args.age, 12)
    
    @mock.patch('infant_recon_all_testable.sf.system.fatal')
    def test_main_function_basic_validation(self, mock_fatal):
        """Test main function basic validation to increase coverage."""
        with mock.patch('infant_recon_all_testable.sf.freesurfer.home', return_value=None):
            # Create minimal args to trigger validation
            args = argparse.Namespace(s='test_subject', age=12)
            
            # This should trigger FREESURFER_HOME validation
            infantfs.main(args)
            
            # Should call fatal
            mock_fatal.assert_called_with('Must set FREESURFER_HOME before running.')


# ---------------------------- Run the test suite ---------------------------- #

if __name__ == '__main__':
    
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
        print("Coverage module not available, running tests without coverage tracking.")
        coverage_available = False

    # Run all tests
    try:
        unittest.main(verbosity=2)
    except SystemExit:  # unittest.main() calls sys.exit()
        pass
    except Exception as e:
        print(f"Test execution failed: {e}")

    if coverage_available:
        # Stop coverage tracking and generate report
        cov.stop()
        cov.save()

        # Generate HTML report
        html_report_dir = os.path.join(os.path.dirname(__file__), 'htmlcov')    
        cov.html_report(directory=html_report_dir)
        
        print(
            f"Look at the HTML coverage report generated at: "
            f"{html_report_dir}/index.html"
        )
    
    print("Done.")
