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

import argparse
import shlex


# IMPORTS FROM THE INFANT FREESURFER MODULE

import infant_recon_all_testable as infantfs


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
    # Use the argument parser of the Infant FreeSurfer module
    parser = infantfs.create_cli()
    # Convert it into a list of args safely (as the shell would do)
    args_list = shlex.split(cmd_str)
    # Parse as if it came from the shell
    parsed = parser.parse_args(args_list)

    return parsed


# UNIT TESTS

"""
Based on the example, please complete the unit tests for infant_recon_all here.

You can use the argument parser defined above to call the main function of 
infant_recon_all_testable with different arguments, and check the expected 
outcomes.
"""
