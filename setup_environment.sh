#!/bin/bash

# =============================================================================
# InfantFS Testing Environment Setup Script
# =============================================================================
# This script sets up the complete environment for running InfantFS tests.
#
# Usage:
#   source setup_environment.sh
#
# What it does:
#   1. Activates the fsenv conda environment (Python 3.8.13)
#   2. Sources FreeSurfer environment variables
#   3. Sets SUBJECTS_DIR to the test directory
#   4. Verifies the environment is correctly configured
# =============================================================================

echo "=========================================="
echo "Setting up InfantFS Testing Environment"
echo "=========================================="

# Source bash profile to get FreeSurfer environment
# On macOS, .bash_profile is used instead of .bashrc for login shells
if [ -f ~/.bash_profile ]; then
    source ~/.bash_profile
else
    source ~/.bashrc
fi

# Activate conda environment
echo "→ Activating fsenv conda environment..."
conda activate fsenv

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1)
echo "✓ Python: $PYTHON_VERSION"

# Verify FreeSurfer
if [ -z "$FREESURFER_HOME" ]; then
    echo "✗ ERROR: FREESURFER_HOME is not set!"
    echo "  Please check your ~/.bashrc configuration"
    return 1
fi
echo "✓ FreeSurfer: $FREESURFER_HOME"

# Verify SUBJECTS_DIR
if [ -z "$SUBJECTS_DIR" ]; then
    echo "✗ ERROR: SUBJECTS_DIR is not set!"
    return 1
fi
echo "✓ SUBJECTS_DIR: $SUBJECTS_DIR"

# Create SUBJECTS_DIR if it doesn't exist
if [ ! -d "$SUBJECTS_DIR" ]; then
    echo "→ Creating SUBJECTS_DIR directory..."
    mkdir -p "$SUBJECTS_DIR"
fi

# Verify license
LICENSE_FILE="$FREESURFER_HOME/license.txt"
if [ ! -f "$LICENSE_FILE" ]; then
    echo "✗ ERROR: FreeSurfer license file not found at $LICENSE_FILE"
    return 1
fi
echo "✓ License: $LICENSE_FILE"

# Verify infant model
INFANT_MODEL="$FREESURFER_HOME/average/synthstrip_skullstripping/infant_synthstrip_01012025.pt"
if [ ! -f "$INFANT_MODEL" ]; then
    echo "✗ ERROR: Infant SynthStrip model not found at $INFANT_MODEL"
    return 1
fi
echo "✓ Infant Model: $(basename $INFANT_MODEL)"

echo ""
echo "=========================================="
echo "✓ Environment setup complete!"
echo "=========================================="
echo ""
echo "You can now run:"
echo "  python test_infantfs.py           # Run all tests"
echo "  python test_environment.py        # Verify FreeSurfer setup"
echo "  python infant_recon_all_testable.py --help  # See InfantFS options"
echo ""
