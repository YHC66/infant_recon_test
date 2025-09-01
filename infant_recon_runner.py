#!/usr/bin/env python3
"""
Infant FreeSurfer Command Runner and Output Validator

This script runs infant_recon_all commands and validates the expected output files exist.
Each command gets its own separate output directory to avoid conflicts.
"""
import os
import subprocess
import yaml
import json
import time
from datetime import datetime
from pathlib import Path
import tempfile
import shutil


class InfantReconRunner:
    """Runner for infant_recon_all commands with output validation."""
    
    def __init__(self, config_file='expected_outputs.yaml'):
        self.config_file = config_file
        self.expected_outputs = self.load_config()
        
    def load_config(self):
        """Load expected outputs configuration from YAML file."""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            print(f"Warning: Config file {self.config_file} not found. Using default configuration.")
            return self.get_default_config()
        except yaml.YAMLError as e:
            print(f"Error parsing YAML config: {e}")
            return self.get_default_config()
    
    def get_default_config(self):
        """Return default expected outputs configuration."""
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
            },
            'conditional_files': {
                'surface_processing': {
                    'condition': 'surfaces_generated',
                    'files': {
                        'surf': ['lh.pial', 'rh.pial', 'lh.sphere', 'rh.sphere']
                    }
                }
            }
        }
    
    def generate_unique_output_dir(self, base_command, base_output_dir=None):
        """Generate a unique output directory for each command."""
        # Create timestamp-based unique identifier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract subject name from command if possible
        try:
            parts = base_command.split()
            subject_idx = parts.index('-s') + 1
            subject_name = parts[subject_idx] if subject_idx < len(parts) else 'unknown'
        except (ValueError, IndexError):
            subject_name = 'unknown'
        
        # Create unique directory name
        unique_name = f"{subject_name}_{timestamp}"
        
        if base_output_dir:
            output_dir = os.path.join(base_output_dir, unique_name)
        else:
            # Use a default base directory
            output_dir = os.path.join(os.getcwd(), 'infant_recon_outputs', unique_name)
        
        return output_dir
    
    def modify_command_for_unique_output(self, command, unique_output_dir):
        """Modify the command to use the unique output directory."""
        # If command already has --outdir, replace it
        parts = command.split()
        
        if '--outdir' in parts:
            outdir_idx = parts.index('--outdir')
            if outdir_idx + 1 < len(parts):
                parts[outdir_idx + 1] = unique_output_dir
        else:
            # Add --outdir to the command
            parts.extend(['--outdir', unique_output_dir])
        
        return ' '.join(parts)
    
    def run_command(self, command_string, timeout=3600, working_dir=None):
        """
        Run infant_recon_all command with environment preservation.
        
        Args:
            command_string: The command to run as a string
            timeout: Timeout in seconds (default: 1 hour)
            working_dir: Working directory for command execution
            
        Returns:
            dict: Results including success status, output, timing, etc.
        """
        # Generate unique output directory
        unique_output_dir = self.generate_unique_output_dir(command_string)
        
        # Modify command to use unique output directory
        modified_command = self.modify_command_for_unique_output(command_string, unique_output_dir)
        
        print(f"🚀 Running command: {modified_command}")
        print(f"📁 Output directory: {unique_output_dir}")
        
        # Create output directory
        os.makedirs(unique_output_dir, exist_ok=True)
        
        # Copy environment and ensure FreeSurfer is set up
        env = os.environ.copy()
        
        # Set up FreeSurfer environment if not already set
        if 'FREESURFER_HOME' not in env or env['FREESURFER_HOME'] is None:
            freesurfer_home = '/Applications/freesurfer/8.1.0'
            env['FREESURFER_HOME'] = freesurfer_home
            env['FSFAST_HOME'] = f'{freesurfer_home}/fsfast'
            env['FSF_OUTPUT_FORMAT'] = 'nii.gz'
            env['SUBJECTS_DIR'] = f'{freesurfer_home}/subjects'
            env['MNI_DIR'] = f'{freesurfer_home}/mni'
            
            # Add FreeSurfer bin directory to PATH
            freesurfer_bin = f'{freesurfer_home}/bin'
            current_path = env.get('PATH', '')
            if freesurfer_bin not in current_path:
                env['PATH'] = f'{freesurfer_bin}:{current_path}'
        
        # Save command and environment to output directory
        try:
            # Save the exact command to txt file
            with open(os.path.join(unique_output_dir, "command.txt"), "w") as fp:
                fp.write(modified_command)
            
            # Save environment variables to YAML file
            with open(os.path.join(unique_output_dir, "environment.yml"), "w") as fp:
                yaml.safe_dump(dict(env), fp)
            
            print(f"📝 Saved command.txt and environment.yml to output directory")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not save command/environment files: {e}")
        
        # Record start time
        start_time = time.time()
        start_timestamp = datetime.now().isoformat()
        
        result = {
            'command': modified_command,
            'original_command': command_string,
            'output_directory': unique_output_dir,
            'start_time': start_timestamp,
            'success': False,
            'exit_code': None,
            'stdout': '',
            'stderr': '',
            'execution_time_seconds': 0,
            'timeout_occurred': False,
            'error_message': None
        }
        
        try:
            # Run the command
            process = subprocess.run(
                modified_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                cwd=working_dir
            )
            
            # Record results
            end_time = time.time()
            result.update({
                'success': (process.returncode == 0),
                'exit_code': process.returncode,
                'stdout': process.stdout,
                'stderr': process.stderr,
                'execution_time_seconds': end_time - start_time,
                'end_time': datetime.now().isoformat()
            })
            
            if process.returncode == 0:
                print(f"✅ Command completed successfully in {result['execution_time_seconds']:.1f} seconds")
            else:
                print(f"❌ Command failed with exit code {process.returncode}")
                result['error_message'] = f"Process exited with code {process.returncode}"
                
        except subprocess.TimeoutExpired:
            result.update({
                'timeout_occurred': True,
                'execution_time_seconds': timeout,
                'error_message': f"Command timed out after {timeout} seconds",
                'end_time': datetime.now().isoformat()
            })
            print(f"⏰ Command timed out after {timeout} seconds")
            
        except Exception as e:
            end_time = time.time()
            result.update({
                'execution_time_seconds': end_time - start_time,
                'error_message': str(e),
                'end_time': datetime.now().isoformat()
            })
            print(f"💥 Command failed with exception: {e}")
        
        return result
    
    def validate_outputs(self, output_dir, command_result=None):
        """
        Validate that expected output files exist in the output directory.
        
        Args:
            output_dir: Path to the output directory
            command_result: Optional command execution results for context
            
        Returns:
            dict: Validation results with missing/found files
        """
        print(f"🔍 Validating outputs in: {output_dir}")
        
        validation_result = {
            'output_directory': output_dir,
            'validation_timestamp': datetime.now().isoformat(),
            'directory_exists': os.path.isdir(output_dir),
            'required_directories': {'found': [], 'missing': []},
            'required_files': {'found': [], 'missing': []},
            'optional_files': {'found': [], 'missing': []},
            'unexpected_files': [],
            'total_required_files': 0,
            'total_found_required': 0,
            'validation_passed': False,
            'summary': {}
        }
        
        if not validation_result['directory_exists']:
            validation_result['summary'] = f"Output directory does not exist: {output_dir}"
            return validation_result
        
        # Check required directories
        for req_dir in self.expected_outputs.get('required_directories', []):
            dir_path = os.path.join(output_dir, req_dir)
            if os.path.isdir(dir_path):
                validation_result['required_directories']['found'].append(req_dir)
                print(f"  ✅ Directory found: {req_dir}")
            else:
                validation_result['required_directories']['missing'].append(req_dir)
                print(f"  ❌ Directory missing: {req_dir}")
        
        # Check required files
        required_files = self.expected_outputs.get('required_files', {})
        for directory, file_list in required_files.items():
            for file_name in file_list:
                validation_result['total_required_files'] += 1
                
                if directory == '.':
                    file_path = os.path.join(output_dir, file_name)
                else:
                    file_path = os.path.join(output_dir, directory, file_name)
                
                if os.path.isfile(file_path):
                    validation_result['required_files']['found'].append(f"{directory}/{file_name}")
                    validation_result['total_found_required'] += 1
                    print(f"  ✅ Required file found: {directory}/{file_name}")
                else:
                    validation_result['required_files']['missing'].append(f"{directory}/{file_name}")
                    print(f"  ❌ Required file missing: {directory}/{file_name}")
        
        # Check optional files (don't affect validation status)
        optional_files = self.expected_outputs.get('optional_files', {})
        for directory, file_list in optional_files.items():
            for file_name in file_list:
                if directory == '.':
                    file_path = os.path.join(output_dir, file_name)
                else:
                    file_path = os.path.join(output_dir, directory, file_name)
                
                if os.path.isfile(file_path):
                    validation_result['optional_files']['found'].append(f"{directory}/{file_name}")
                    print(f"  ℹ️  Optional file found: {directory}/{file_name}")
                else:
                    validation_result['optional_files']['missing'].append(f"{directory}/{file_name}")
        
        # Determine validation status
        validation_result['validation_passed'] = (
            len(validation_result['required_directories']['missing']) == 0 and
            len(validation_result['required_files']['missing']) == 0
        )
        
        # Generate summary
        found_req_files = validation_result['total_found_required']
        total_req_files = validation_result['total_required_files']
        validation_result['summary'] = (
            f"Found {found_req_files}/{total_req_files} required files, "
            f"{len(validation_result['required_directories']['found'])} directories"
        )
        
        if validation_result['validation_passed']:
            print(f"✅ Validation PASSED: {validation_result['summary']}")
        else:
            print(f"❌ Validation FAILED: {validation_result['summary']}")
            
        return validation_result
    
    def run_and_validate(self, command_string, timeout=3600, working_dir=None):
        """
        Run command and validate outputs in one operation.
        
        Args:
            command_string: Command to run
            timeout: Timeout in seconds
            working_dir: Working directory for execution
            
        Returns:
            dict: Combined execution and validation results
        """
        print(f"🧪 Running and validating infant_recon_all command")
        print(f"📝 Command: {command_string}")
        
        # Run the command
        exec_result = self.run_command(command_string, timeout=timeout, working_dir=working_dir)
        
        # Validate outputs (even if command failed, might be partial results)
        validation_result = self.validate_outputs(exec_result['output_directory'], exec_result)
        
        # Combine results
        combined_result = {
            'execution': exec_result,
            'validation': validation_result,
            'overall_success': exec_result['success'] and validation_result['validation_passed'],
            'test_timestamp': datetime.now().isoformat()
        }
        
        print(f"📊 Overall test result: {'PASSED' if combined_result['overall_success'] else 'FAILED'}")
        
        return combined_result
    
    def generate_report(self, results, output_file=None):
        """
        Generate a comprehensive test report.
        
        Args:
            results: Test results (single result dict or list of results)
            output_file: Optional file to save report to
            
        Returns:
            dict: Formatted report
        """
        if not isinstance(results, list):
            results = [results]
        
        report = {
            'report_timestamp': datetime.now().isoformat(),
            'total_tests': len(results),
            'passed_tests': sum(1 for r in results if r.get('overall_success', False)),
            'failed_tests': sum(1 for r in results if not r.get('overall_success', False)),
            'test_details': results
        }
        
        # Print summary
        print(f"\n📋 Test Report Summary")
        print(f"=" * 50)
        print(f"Total tests: {report['total_tests']}")
        print(f"Passed: {report['passed_tests']}")
        print(f"Failed: {report['failed_tests']}")
        print(f"Success rate: {report['passed_tests']/report['total_tests']*100:.1f}%")
        
        # Save to file if requested
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(report, f, indent=2, sort_keys=False)
                print(f"📄 Report saved to: {output_file}")
            except Exception as e:
                print(f"Warning: Could not save report to {output_file}: {e}")
        
        return report


def main():
    """Example usage of the InfantReconRunner."""
    runner = InfantReconRunner()
    
    # Example command - this is the working command provided
    # Use full path to infant_recon_all since it's not in PATH
    test_command = "/Users/cyh/Desktop/freesurfer/infant/infant_recon_all -s sub-01 --age 18 --inputfile /Users/cyh/freesurfer_proj/sub-01/anat/sub-01_T1w.nii.gz"
    
    print("🧪 Infant FreeSurfer Command Runner - Example Usage")
    print("=" * 60)
    
    # Run and validate
    result = runner.run_and_validate(test_command, timeout=3600)
    
    # Generate report
    report = runner.generate_report(result, output_file='test_report.json')
    
    return result


if __name__ == "__main__":
    main()