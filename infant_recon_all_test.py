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


# UNIT TESTS

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
