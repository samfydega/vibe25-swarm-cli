"""
Safe code execution and job result handling
"""
import os
import sys
import tempfile
import subprocess
import requests
from typing import Dict, Tuple
from pathlib import Path
from .config import API_BASE_URL # Import API URL config

def execute_code(job_data: Dict) -> Tuple[str, str]:
    """
    Safely execute the provided code in a temporary file and return stdout/stderr
    
    Args:
        job_data: Dictionary containing job information including code, filename, and language
        
    Returns:
        Tuple of (stdout, stderr) from the execution
    """
    # Create a temporary directory that will be automatically cleaned up
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create the temporary file with the correct extension
        file_path = Path(temp_dir) / job_data['filename']
        
        try:
            # Write the code to the temporary file
            with open(file_path, 'w') as f:
                f.write(job_data['code'])
            
            # Execute the code based on the language
            if job_data['lang'] == 'python':
                # Use sys.executable to ensure we use the correct Python interpreter
                process = subprocess.Popen(
                    [sys.executable, str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            elif job_data['lang'] == 'javascript':
                # Assuming 'node' is available in the PATH
                process = subprocess.Popen(
                    ['node', str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
            else:
                return "", f"Unsupported language: {job_data['lang']}"
            
            # Wait for the process to complete with a timeout
            try:
                stdout, stderr = process.communicate(timeout=30)  # 30 second timeout
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                stderr += "\nExecution timed out after 30 seconds"
                
            return stdout, stderr
            
        except Exception as e:
            return "", f"Error executing code: {str(e)}"

def update_job_status(job_id: str, stdout: str, stderr: str) -> bool:
    """
    Send job execution results back to the API
    
    Args:
        job_id: The ID of the job that was executed
        stdout: Standard output from the execution
        stderr: Standard error from the execution
        
    Returns:
        bool: True if the update was successful, False otherwise
    """
    try:
        response = requests.post(
            f"{API_BASE_URL}/update-job", # Use configured API URL
            json={
                'job_id': job_id,
                'stdout': stdout,
                'stderr': stderr
            },
            timeout=5
        )
        return response.status_code == 200
    except requests.RequestException:
        return False