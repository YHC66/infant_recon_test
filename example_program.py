#!/usr/bin/env python

# DESCRIPTION

"""
Minimal example of how to set up unit tests with coverage tracking in Python.
This script includes a simple function `func` that we want to test.

"""

# This is a toy example function that we want to test.
def example_func(input):
    if isinstance(input, int):
        return input
    elif isinstance(input, dict):
        return NotImplementedError(
            "Suport for dict input not implemented yet.")
    else:
        raise ValueError("Input must be an integer")
    