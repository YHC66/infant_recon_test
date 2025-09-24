#!/usr/bin/env python

# DESCRIPTION

"""
Module to verify FreeSurfer environment setup.

Checks on module import for the following:

    1. FREESURFER_HOME is set and valid
    2. SUBJECTS_DIR is set
    3. FreeSurfer license file exists

"""

# IMPORTS

import os
import re


# IMPLEMENTATION


def verify_freesurfer_environment():
    """
    Verify that the FreeSurfer environment is ready for use.

    Checks:
        1. FREESURFER_HOME must be set and point to an existing directory
        2. SUBJECTS_DIR must be set
        3. A FreeSurfer license file must exist in FREESURFER_HOME

    Raises:
        EnvironmentError: If any checks fail.

    """
    # Check FREESURFER_HOME is set and valid
    fs_home = os.environ.get("FREESURFER_HOME", None)
    if fs_home:
        # Check if path exists
        if not os.path.exists(fs_home):
            raise EnvironmentError(
                f"FREESURFER_HOME is set to '{fs_home}', "
                "but that path does not exist."
            )
    else:
        raise EnvironmentError(
            "FREESURFER_HOME environment variable is not set."
        )

    # Check SUBJECTS_DIR is set
    if "SUBJECTS_DIR" not in os.environ:
        raise EnvironmentError("SUBJECTS_DIR environment variable is not set.")

    return fs_home  # type: str


def verify_license(fs_home):
    """
    Check if a FreeSurfer license file exists in the FreeSurfer root directory.

    Raises:
        EnvironmentError:
            If no license file is found or if the license file is empty.

    """
    assert os.path.isdir(fs_home), "FREESURFER_HOME must be a directory"

    licence_file_pattern = re.compile(r"^\.*licen[sc]e(\.txt)?$")
    licence_files = [
        f for f in os.listdir(fs_home) if licence_file_pattern.match(f)
    ]
    if not licence_files:
        raise EnvironmentError(
            f"No FreeSurfer license file found in FREESURFER_HOME: "
            f"{fs_home}"
        )
    if not any(
        os.path.getsize(os.path.join(fs_home, f)) > 0 for f in licence_files
    ):
        raise EnvironmentError(
            f"FreeSurfer license file(s) found in FREESURFER_HOME: {fs_home}, but all are empty."
        )


# VERIFY ENVIRONMENT ON EXECUTION

if __name__ == "__main__":
    fs_home = verify_freesurfer_environment()
    verify_license(fs_home)
