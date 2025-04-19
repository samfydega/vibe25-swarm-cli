"""
Heartbeat monitoring for give-my-resources
"""
import random
import psutil
import requests
import threading
import time
from typing import Optional, Dict
from .config import (
    get_user_id, get_device_status, 
    get_current_job, set_current_job, clear_current_job,
    get_tunnel_url,
    API_BASE_URL # Import API URL config
)
from .executor import execute_code, update_job_status

# Define the local port ngrok will forward to
LOCAL_PORT = 9000

class HeartbeatMonitor:
    def __init__(self):
        # Initialize status from config
        self.status = "ACTIVE" if get_device_status() else "INACTIVE"
        self.running = False
        self.thread: Optional[threading.Thread] = None
        # Initialize current_job from config
        self.current_job: Optional[Dict] = get_current_job()
        # Add execution thread
        self.execution_thread: Optional[threading.Thread] = None
        
    def get_metrics(self):
        """Collect system metrics"""
        vm = psutil.virtual_memory()
        # Update status based on both device status and current job
        if self.current_job:
            self.status = "BUSY"  # If we have a job, we're busy regardless of device status
        else:
            self.status = "ACTIVE" if get_device_status() else "INACTIVE"
            
        # Get the public tunnel URL from config, fallback to local URL if not set yet
        tunnel_url = get_tunnel_url() or f"http://localhost:{LOCAL_PORT}"
            
        return {
            "user_id": get_user_id() or "",  # Ensure not None
            "url": tunnel_url, # Use the public tunnel URL
            "cpu_cores": psutil.cpu_count(logical=False) or 1,  # Physical cores, fallback to 1
            "cpu_load": psutil.cpu_percent(interval=None),  # Already returns percentage
            "ram_total": int(vm.total / (1024 * 1024)),  # Convert to MB
            "ram_used": int(vm.used / (1024 * 1024)),  # Convert to MB
            "disk_free": int(psutil.disk_usage('/').free / (1024 * 1024)),  # Convert to MB
            "status": self.status
        }
    
    def send_heartbeat(self):
        """Send heartbeat to server"""
        try:
            metrics = self.get_metrics()
            response = requests.post(
                f"{API_BASE_URL}/heartbeat", # Use configured API URL
                json=metrics,
                timeout=5  # Add timeout
            )
            response.raise_for_status()
        except requests.RequestException:
            # Silently continue on error - don't disrupt the UI
            pass
    
    def execute_job(self, job_data: Dict):
        """Execute the job in a separate thread"""
        stdout, stderr = execute_code(job_data)
        success = update_job_status(job_data['id'], stdout, stderr)
        
        if success:
            # Clear the job data after successful update
            self.current_job = None
            clear_current_job()
    
    def check_for_jobs(self):
        """Check for any queued jobs for this device"""
        try:
            user_id = get_user_id()
            if not user_id:
                return
                
            response = requests.get(
                f"{API_BASE_URL}/check-for-jobs/{user_id}", # Use configured API URL
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            if data.get('job'):
                # Store the job data both in memory and config
                self.current_job = {
                    'id': data['job']['id'],
                    'lang': data['job']['lang'],
                    'code': data['job']['code'],
                    'filename': data['job']['filename']
                }
                set_current_job(self.current_job)
                
                # Start execution in a separate thread
                if not self.execution_thread or not self.execution_thread.is_alive():
                    self.execution_thread = threading.Thread(
                        target=self.execute_job,
                        args=(self.current_job,),
                        daemon=True
                    )
                    self.execution_thread.start()
            else:
                self.current_job = None
                clear_current_job()
                
        except requests.RequestException:
            # Silently continue on error - don't disrupt the UI
            pass
    
    def heartbeat_loop(self):
        """Main heartbeat and job checking loop"""
        while self.running:
            self.send_heartbeat()
            self.check_for_jobs()  # Check for jobs in the same interval
            time.sleep(20)  # Wait for 20 seconds
    
    def start(self):
        """Start the heartbeat monitor"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
            self.thread.start()
            # Send initial heartbeat and check for jobs
            self.send_heartbeat()
            self.check_for_jobs()
    
    def stop(self):
        """Stop the heartbeat monitor"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None
        # Wait for any executing job to finish
        if self.execution_thread and self.execution_thread.is_alive():
            self.execution_thread.join(timeout=1)
    
    def set_status(self, status: str):
        """Update the status"""
        self.status = status