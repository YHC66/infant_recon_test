# helpers.py

# DESCRIPTION

"""
Helper functions for testing InfantFS.

The purpose of this module is to provide common utility functions for testing 
InfantFS, while keeping the test script focused on the actual test cases.

Authors:
    Yihang Chen (YC)
    Istvan N Huszar (INH) <ihuszar@mgh.harvard.edu>
    
Date: 23-Sep-2025

"""


# IMPORTS

import os
import shlex
import argparse


# FUNCTIONS


def extract_command_line_args(cmd_str: str) -> str:
    """
    Extract command line arguments from a full command string.

    Args:
        cmd_str (str):
            The full command string, which may include "python"
            and the script name.

    Returns:
        str:
            The command line arguments as a single string.

    """
    cmd_parts = shlex.split(cmd_str)

    # Remove "python" and script name if present
    if len(cmd_parts) > 0 and cmd_parts[0] == "python":
        cmd_parts = cmd_parts[1:]  # Remove 'python'
    if len(cmd_parts) > 0 and (
        "infant_recon_all" in cmd_parts[0].lower()
        or cmd_parts[0].lower().endswith(".py")
    ):
        cmd_parts = cmd_parts[1:]  # Remove script name

    # Reconstruct the arguments string
    args_str = " ".join(cmd_parts)

    return args_str


def get_expected_output_directory(cmd_str: str) -> str:
    """
    Parse an InfantFS command string and return the expected output directory.

    If --outdir is specified, it uses that path.
    Otherwise, it defaults to $SUBJECTS_DIR/subject_name.

    Args:
        cmd_str (str): The InfantFS command string to parse. Can be either just
        the arguments or a full command including "python script.py".

    Returns:
        str: The absolute path to the expected output directory.

    Raises:
        RuntimeError:
            If the command is missing necessary information
            to determine the output directory.
    """
    # Clean the command string to extract just the arguments
    args_str = extract_command_line_args(cmd_str)

    # Minimal parser for outdir and subject name
    minimal_parser = argparse.ArgumentParser()
    minimal_parser.add_argument("-s", "--s", type=str, help="Subject name")
    minimal_parser.add_argument("-o", "--outdir", help="Output directory")
    args, unknown = minimal_parser.parse_known_args(shlex.split(args_str))

    # Determine output directory based on the same logic as in infantfs.main()
    if args.outdir:
        outdir = os.path.abspath(args.outdir)

    else:
        # Get SUBJECTS_DIR from environment
        subjects_dir = os.environ.get("SUBJECTS_DIR")
        if subjects_dir is None:
            raise RuntimeError(
                "The output directory cannot be determined, because "
                "the --outdir argument is missing and"
                "the SUBJECTS_DIR environment variable is not set either."
            )
        subj = args.s
        if not subj:
            raise RuntimeError(
                "The output directory cannot be determined, because "
                "both the --outdir and --subject arguments are missing."
            )
        outdir = os.path.abspath(os.path.join(subjects_dir, subj))

    return outdir
