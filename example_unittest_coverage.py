#!/usr/bin/env python

# DESCRIPTION

"""
Minimal example of how to set up unit tests with coverage tracking in Python.

Author: Istvan N Huszar (INH) <ihuszar@mgh.harvard.edu>
Date: 2025-Sep-02

"""


# IMPORTS

import os
import coverage
import unittest


# --------------------- Program code that we want to test -------------------- #

# Normally this would be in a separate file, but for demonstration purposes, 
# we'll include a toy example here.

from example_program import example_func as func
    
    
# -------------------------------- Unit tests -------------------------------- #

# If all these tests pass, we can guarantee that our program will perform as 
# expected as long as the inputs are of the types we have tested.

# Test cases should be systematic, and organised into classes. Each class may 
# implement multiple methods, each of which tests a specific aspect of the test 
# category.

# In the example below, we have one class that tests the func function with
# different input types.


class TestFuncWithDifferentInputTypes(unittest.TestCase):
    """
    Test cases for the func function with different input types.
    
    Each method tests a specific input type and checks for the expected output
    or exception.
    
    Note: The name of the methods should start with 'test_' to be recognized by
    the unittest framework.
    """
    
    def setUp(self):
        """
        Set up any state specific to the execution of the given class of tests.
        This method is called before each test method.
        
        """
        # For this simple example, we don't have any setup steps.
        # Normally, you might initialize variables or objects' state here.
        print("setUp runs before each test")
        
    # Expectation
    def test_input_is_positive_integer(self):
        """
        Test that func returns the same integer when an integer is passed.
        """
        self.assertEqual(func(1), 1)
        
    # Expected Failure
    def test_input_is_char(self):
        """
        Test that func raises a ValueError when a letter is passed.
        """
        with self.assertRaises(ValueError):
            func("a")
            
    # Feature not yet implemented
    @unittest.skip("Skipping this test for demonstration purposes")
    def test_input_is_dict(self):
        """
        In the future, we want the function to return the keys of the dict, 
        so we wrote this test for it. However, this functionality isn't implemented yet, so let's skip the test for now.
        """
        self.assertEqual(func(dict(a=1)), "a")
        
    def tearDown(self):
        # Clean up after each test method.
        print("tearDown runs after each test")

    @classmethod
    def tearDownClass(cls):
        # Normally, if we have objects that we define in this script, and the 
        # test methods interact with them, we can use this function to reset 
        # the object's state before running a new class of tests.
        print("tearDownClass runs once after all tests")


# ---------------------------- Run the test suite ---------------------------- #

# We let the unittest module handle the test running, and we also add coverage 
# tracking around it.

if __name__ == '__main__':
    
    # Start coverage tracking
    cov = coverage.Coverage()
    cov.start()

    # Run all tests
    try:
        unittest.main(verbosity=2)
    except:  # catch-all except clause
        pass

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
