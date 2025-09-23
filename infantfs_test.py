# IMPORTS

import os
import sys
import unittest
import argparse
import shlex
import yaml
import shutil

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
    # Create parser using real FreeSurfer environment
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
    
    1. Define an InfantFS command in setUpClass (runs ONCE)
    2. Use get_expected_output_directory to determine where outputs should be
    3. Test for expected files and directories in that location
    """
    
    @classmethod
    def _setup_freesurfer_environment(cls):
        """Set up FreeSurfer environment variables for InfantFS execution."""
        # Set up FreeSurfer environment - use the actual installation path
        freesurfer_home = '/Applications/freesurfer/8.1.0'
        if not os.path.exists(freesurfer_home):
            raise RuntimeError(f"FreeSurfer not found at {freesurfer_home}")
        
        print(f"Setting up FreeSurfer environment: {freesurfer_home}")
        os.environ['FREESURFER_HOME'] = freesurfer_home
        
        # Add FreeSurfer bin to PATH
        freesurfer_bin = f'{freesurfer_home}/bin'
        current_path = os.environ.get('PATH', '')
        if freesurfer_bin not in current_path:
            os.environ['PATH'] = f'{freesurfer_bin}:{current_path}'
        
        # Set additional FreeSurfer environment variables
        os.environ['FSFAST_HOME'] = f'{freesurfer_home}/fsfast'
        os.environ['FSF_OUTPUT_FORMAT'] = 'nii.gz'
        os.environ['MNI_DIR'] = f'{freesurfer_home}/mni'
        
        print(f"✅ FreeSurfer environment configured successfully")

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
        cls.infantfs_command = '-s sub-01 --age 18 --inputfile /Users/cyh/Desktop/infant_recon_test/sub-01/anat/sub-01_T1w.nii.gz --no-cleanup --outdir /Users/cyh/Desktop/infant_recon_test/test_execution_output'
        
        # Set up FreeSurfer environment
        cls._setup_freesurfer_environment()
        
        # Set up environment for consistent testing
        os.environ['SUBJECTS_DIR'] = '/Users/cyh/Desktop/infant_recon_test/test_subjects'
        
        # Parse the arguments for additional test information
        cls.parsed_args = parse_args(cls.infantfs_command)
        
        # Set the expected output directory
        cls.expected_output_dir = '/Users/cyh/Desktop/infant_recon_test/test_execution_output'
        
        # Clear output directory before running
        if os.path.exists(cls.expected_output_dir):
            print(f"Clearing existing output directory: {cls.expected_output_dir}")
            shutil.rmtree(cls.expected_output_dir)
        
        # Create fresh output directory
        os.makedirs(cls.expected_output_dir, exist_ok=True)
        print(f"Created fresh output directory: {cls.expected_output_dir}")
        
        # Run InfantFS ONCE to create files for ALL tests
        try:
            print(f" Starting InfantFS execution with command: {cls.infantfs_command}")
            print("  This will take ~1 hour")
            
            # Parse arguments and run InfantFS main function
            infantfs.main(cls.parsed_args)
            
            print(f"✅ InfantFS execution completed successfully")
            print(" All tests will now validate this output")
            cls.infantfs_execution_successful = True
            
        except Exception as e:
            print(f"⚠️ InfantFS execution failed: {e}")
            print(f"Tests will check expected structure but may fail due to missing files")
            cls.infantfs_execution_successful = False
        
        print("=" * 60)
    
    def setUp(self):
        """
        Set up test fixtures before each individual test method.
        
        Now it just sets instance variables - InfantFS execution happens once in setUpClass.
        """
        # Copy class variables to instance variables for test access
        self.infantfs_command = self.__class__.infantfs_command
        self.parsed_args = self.__class__.parsed_args
        self.expected_output_dir = self.__class__.expected_output_dir
        self.infantfs_execution_successful = self.__class__.infantfs_execution_successful
    
    
    # def load_expected_outputs_config(self):
    #     """Load expected outputs configuration from YAML file, like infant_recon_runner.py"""
    #     config_file = 'expected_outputs.yaml'
    #     try:
    #         with open(config_file, 'r') as f:
    #             config = yaml.safe_load(f)
    #         return config
    #     except FileNotFoundError:
    #         # Fallback to default config like infant_recon_runner.py does
    #         return self.get_default_expected_outputs()
    #     except yaml.YAMLError:
    #         return self.get_default_expected_outputs()
    
    # def get_default_expected_outputs(self):
    #     """Return default expected outputs configuration (from infant_recon_runner.py)"""
    #     return {
    #         'required_directories': ['mri', 'surf', 'label', 'stats', 'log'],
    #         'required_files': {
    #             'mri': ['norm.mgz', 'aseg.mgz', 'brain.mgz', 'brainmask.mgz', 'norm.nii.gz', 'aseg.nii.gz'],
    #             'surf': ['lh.white', 'rh.white', 'lh.orig', 'rh.orig'],
    #             'label': [],  # May be empty for some runs
    #             'stats': [],  # May be empty if --no-stats is used
    #             'log': ['recon.log'],
    #             '.': ['mprage.nii.gz']  # Files in root of output directory
    #         },
    #         'optional_files': {
    #             'mri': ['filled.mgz', 'wm.mgz', 'brain.finalsurfs.mgz'],
    #             'surf': ['lh.area', 'rh.area', 'lh.curv', 'rh.curv', 'lh.inflated', 'rh.inflated'],
    #             'work': []  # Work directory files (if --no-cleanup not used)
    #         }
    #     }
    
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

    def test_output_directory_exists(self):
        """Test that the output directory exists."""
        self.assertTrue(os.path.exists(self.expected_output_dir),
                       f"Output directory should exist: {self.expected_output_dir}")
    
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
                'label': [],  
                'stats': [], 
                'log': ['recon.log'],
                '.': ['mprage.nii.gz'] 
            }
        }

    def test_subdirs_exist(self):
        """Test that all required subdirectories exist in output directory."""
        expected_outputs = self.load_expected_outputs_config()
        required_dirs = expected_outputs.get('required_directories', [])
        
        for dir_name in required_dirs:
            dir_path = os.path.join(self.expected_output_dir, dir_name)
            with self.subTest(directory=dir_name):
                self.assertTrue(os.path.isdir(dir_path),
                               f"Required subdirectory missing: {dir_name} at {dir_path}")

    def test_mri_subdir_files(self):
        """Test that all required MRI files exist in mri subdirectory."""
        expected_outputs = self.load_expected_outputs_config()
        mri_files = expected_outputs.get('required_files', {}).get('mri', [])
        mri_dir = os.path.join(self.expected_output_dir, 'mri')
        
        for file_name in mri_files:
            file_path = os.path.join(mri_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Required MRI file missing: {file_name} at {file_path}")

    def test_mri_transforms_subdir_files(self):
        """Test that all required transform files exist in mri/transforms subdirectory."""
        expected_outputs = self.load_expected_outputs_config()
        transform_files = expected_outputs.get('required_files', {}).get('mri/transforms', [])
        transforms_dir = os.path.join(self.expected_output_dir, 'mri', 'transforms')
        
        for file_name in transform_files:
            file_path = os.path.join(transforms_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Required transform file missing: {file_name} at {file_path}")

    def test_surf_subdir_files(self):
        """Test that all required surface files exist in surf subdirectory."""
        expected_outputs = self.load_expected_outputs_config()
        surf_files = expected_outputs.get('required_files', {}).get('surf', [])
        surf_dir = os.path.join(self.expected_output_dir, 'surf')
        
        for file_name in surf_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Required surface file missing: {file_name} at {file_path}")

    def test_surf_left_hemisphere_files(self):
        """Test that left hemisphere surface files exist in surf subdirectory."""
        lh_files = ['lh.orig', 'lh.white', 'lh.inflated', 'lh.area', 'lh.curv']
        surf_dir = os.path.join(self.expected_output_dir, 'surf')
        
        for file_name in lh_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Left hemisphere surface file missing: {file_name} at {file_path}")

    def test_surf_right_hemisphere_files(self):
        """Test that right hemisphere surface files exist in surf subdirectory."""
        rh_files = ['rh.orig', 'rh.white', 'rh.area', 'rh.curv']
        surf_dir = os.path.join(self.expected_output_dir, 'surf')
        
        for file_name in rh_files:
            file_path = os.path.join(surf_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Right hemisphere surface file missing: {file_name} at {file_path}")

    def test_label_subdir_files(self):
        """Test that all required label files exist in label subdirectory."""
        expected_outputs = self.load_expected_outputs_config()
        label_files = expected_outputs.get('required_files', {}).get('label', [])
        label_dir = os.path.join(self.expected_output_dir, 'label')
        
        for file_name in label_files:
            file_path = os.path.join(label_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Required label file missing: {file_name} at {file_path}")

    def test_log_subdir_files(self):
        """Test that all required log files exist in log subdirectory."""
        expected_outputs = self.load_expected_outputs_config()
        log_files = expected_outputs.get('required_files', {}).get('log', [])
        log_dir = os.path.join(self.expected_output_dir, 'log')
        
        for file_name in log_files:
            file_path = os.path.join(log_dir, file_name)
            with self.subTest(file=file_name):
                self.assertTrue(os.path.isfile(file_path),
                               f"Required log file missing: {file_name} at {file_path}")

    def test_stats_subdir_files(self):
        """Test that statistics files exist in stats subdirectory (if --no-stats not used)."""
        stats_files = ['aseg.stats']  # Basic stats files that should exist
        stats_dir = os.path.join(self.expected_output_dir, 'stats')
        
        # Only test if stats directory exists 
        if os.path.isdir(stats_dir):
            for file_name in stats_files:
                file_path = os.path.join(stats_dir, file_name)
                with self.subTest(file=file_name):
                    self.assertTrue(os.path.isfile(file_path),
                                   f"Expected stats file missing: {file_name} at {file_path}")


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
        unittest.main(verbosity=2, exit=False)
    except Exception as e:
        print(f"Test execution failed: {e}")

    if coverage_available:
        # Stop coverage tracking and generate report
        cov.stop()
        cov.save()

        # Generate HTML report
        html_report_dir = os.path.join(os.path.dirname(__file__), 'htmlcov_quick')    
        cov.html_report(directory=html_report_dir)
        
        print(
            f"Look at the HTML coverage report generated at: "
            f"{html_report_dir}/index.html"
        )
    
    print("Done.")