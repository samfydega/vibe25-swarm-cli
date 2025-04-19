"""
CLI implementation for give-my-resources
"""
import click
import webbrowser
import requests
import os
import inquirer
import shutil
import subprocess
import platform
import atexit
from typing import List, Dict, Optional
try:
    from pyngrok import ngrok, conf, exception as ngrok_exception
    NgrokTunnelType = ngrok.NgrokTunnel
except ImportError:
    ngrok = None
    ngrok_exception = None
    conf = None
    from typing import Any
    NgrokTunnelType = Any

from .config import (
    get_user_id, set_user_id,
    get_device_status, set_device_status,
    clear_user_data, clear_current_job,
    get_ngrok_token, set_ngrok_token,
    get_ngrok_id, set_ngrok_id,
    set_tunnel_url,
    API_BASE_URL, set_api_base_url
)
from .heartbeat import HeartbeatMonitor, LOCAL_PORT

WEB_APP_URL = "https://vibe25-resourcesharing-web-app.vercel.app/handler/sign-up"
API_BASE_URL = "http://localhost:8787"

monitor = HeartbeatMonitor()
ngrok_tunnel: Optional[NgrokTunnelType] = None

def cleanup_ngrok():
    global ngrok_tunnel
    if ngrok_tunnel:
        click.echo("\nShutting down ngrok tunnel...")
        try:
            ngrok.disconnect(ngrok_tunnel.public_url)
            click.echo("Ngrok tunnel closed.")
        except Exception as e:
            click.echo(f"Warning: Error closing ngrok tunnel: {e}", err=True)
        ngrok_tunnel = None

atexit.register(cleanup_ngrok)

def fetch_resources() -> List[Dict]:
    try:
        response = requests.get(f"{API_BASE_URL}/devices", timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return []

def fetch_budget_info(user_id: Optional[str]) -> Optional[Dict]:
    """Fetch budget information from the API"""
    if not user_id:
        return None
    try:
        url = f"{API_BASE_URL}/get-budget/{user_id}"
        response = requests.get(url, timeout=5)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        # Check if the response is valid JSON
        try:
            data = response.json()
        except requests.exceptions.JSONDecodeError:
            click.echo(f"Error: Invalid JSON response received from {url}", err=True)
            return None

        # Validate expected keys and types
        if isinstance(data, dict) and \
           'spent_cents' in data and isinstance(data['spent_cents'], int) and \
           'earned_cents' in data and isinstance(data['earned_cents'], int):
            return data
        else:
            click.echo(f"Error: Unexpected data format received from {url}. Expected 'spent_cents' and 'earned_cents' as integers.", err=True)
            return None

    except requests.exceptions.RequestException as e:
        click.echo(f"Error fetching budget info: {e}", err=True)
        return None
    except Exception as e: # Catch any other unexpected errors
        click.echo(f"An unexpected error occurred while fetching budget: {e}", err=True)
        return None

def get_script_files() -> List[str]:
    current_dir = os.getcwd()
    files = []
    for file in os.listdir(current_dir):
        if file.endswith(('.py', '.js')):
            files.append(file)
    return sorted(files)

def count_file_lines(filepath: str) -> int:
    try:
        with open(filepath, 'r') as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def calculate_price(num_lines: int) -> float:
    return num_lines / 100

def create_job_flow(selected_resource: Dict):
    click.clear()
    click.echo(f"\nCreating new job for resource: {selected_resource['url']}")
    
    script_files = get_script_files()
    if not script_files:
        click.echo(f"\nThere are no .py or .js scripts in this directory ({os.getcwd()})")
        click.pause()
        return
    
    click.echo("\nAvailable script files:")
    
    questions = [
        inquirer.List('script',
                     message="Select a script file",
                     choices=script_files,
                     carousel=True)
    ]
    
    try:
        answers = inquirer.prompt(questions)
        if not answers:
            click.echo("\nOperation cancelled")
            click.pause()
            return
            
        selected_file = answers['script']
        
        num_lines = count_file_lines(selected_file)
        price = calculate_price(num_lines)
        
        click.echo(f"\nScript: {selected_file}")
        click.echo(f"Lines of code: {num_lines}")
        click.echo(f"Estimated price: ${price:.6f}")
        
        if click.confirm("\nWould you like to create this job?"):
            try:
                with open(selected_file, 'r') as f:
                    code = f.read()
                
                lang = 'python' if selected_file.endswith('.py') else 'javascript'
                
                device_id = selected_resource['user_id']
                
                job_data = {
                    'requester': get_user_id(),
                    'device_id': device_id,
                    'filename': selected_file,
                    'lang': lang,
                    'code': code,
                    'cost_usd': price
                }
                
                response = requests.post(
                    f"{API_BASE_URL}/submit-job",
                    json=job_data,
                    timeout=5
                )
                
                if response.status_code == 200:
                    click.echo("\nJob created successfully!")
                else:
                    click.echo("\nError: Please try again later.")
            except IOError:
                click.echo("\nError: Could not read the selected file.")
        
        click.pause()
        
    except (KeyboardInterrupt, EOFError):
        click.echo("\nOperation cancelled")
        click.pause()

def display_resources():
    resources = fetch_resources()
    
    if not resources:
        click.echo("\nNo resources available.")
        return
        
    click.clear()
    click.echo("\nAvailable Resources:")
    click.echo("-" * 80)
    
    choices = []
    for resource in resources:
        ram_used_gb = resource['ram_used'] / 1024
        ram_total_gb = resource['ram_total'] / 1024
        disk_free_gb = resource['disk_free'] / 1024
        
        resource_str = (
            f"ID: {resource['user_id']} - "
            f"URL: {resource['url']} - "
            f"CPU: {resource['cpu_cores']} cores ({resource['cpu_load']:.1f}%) - "
            f"RAM: {ram_used_gb:.1f}/{ram_total_gb:.1f} GB - "
            f"Disk: {disk_free_gb:.1f} GB free"
        )
        choices.append((resource_str, resource))
    
    choices.append(("Back to menu", "back"))
    
    questions = [
        inquirer.List('resource',
                     message="Select a resource to create a job (use arrow keys)",
                     choices=choices,
                     carousel=True)
    ]
    
    try:
        answers = inquirer.prompt(questions)
        if answers and answers['resource'] != "back":
            create_job_flow(answers['resource'])
    except (KeyboardInterrupt, EOFError):
        pass

def display_jobs():
    user_id = get_user_id()
    try:
        response = requests.get(f"{API_BASE_URL}/jobs/{user_id}", timeout=5)
        response.raise_for_status()
        jobs = response.json()

        if not jobs:
            click.echo("\nNo jobs found.")
            click.pause()
            return

        click.echo("\nYour Jobs:")
        click.echo("-" * 80)

        choices = []
        for job in jobs:
            job_str = (
                f"ID: {job['id']} - "
                f"File: {job['filename']} - "
                f"Lang: {job['lang']} - "
                f"Status: {job['status']}"
            )
            if job['status'] == 'FINISHED':
                choices.append((job_str, job))
            else:
                choices.append((f"{job_str} (in progress)", None))

        choices.append(("Back to menu", "back"))

        questions = [
            inquirer.List('job',
                         message="Select a finished job to view output (use arrow keys)",
                         choices=choices,
                         carousel=True)
        ]

        try:
            answers = inquirer.prompt(questions)
            if answers:
                selected_job_data = answers['job']
                if selected_job_data == "back":
                    return
                if selected_job_data is None:
                    click.echo("\nCannot view output for jobs that are not finished.")
                    click.pause()
                    return

                click.clear()
                click.echo("\nJob Output:")
                click.echo("-" * 80)
                click.echo("\nStandard Output:")
                stdout = selected_job_data.get('stdout') or selected_job_data.get('stdoutt') or 'No output'
                click.echo(stdout)
                click.echo("\nStandard Error:")
                click.echo(selected_job_data.get('stderr', 'No errors') or 'No errors')
                click.echo("\nPress any key to go back...")
                click.pause()

        except (KeyboardInterrupt, EOFError):
            click.echo("\nOperation cancelled.")
            pass
        except Exception as e:
            click.echo(f"\nAn error occurred while displaying job details: {e}")
            click.pause()

    except requests.exceptions.RequestException as e:
        click.echo(f"\nError fetching jobs: {e}", err=True)
        click.pause()
    except Exception as e: # Catch any other unexpected errors during job fetching/processing
        click.echo(f"\nAn unexpected error occurred while fetching jobs: {e}", err=True)
        click.pause()

def show_main_menu():
    monitor.start()
    user_id = get_user_id() # Get user_id once
    budget_info = fetch_budget_info(user_id) # Fetch budget info once on startup

    try:
        while True:
            click.clear()
            click.echo("\n=== Give My Permission ===\n")
            click.echo("Share your device's power, run code remotely.\n")

            # Display Budget Info if available
            if budget_info:
                try:
                    # Ensure keys exist and are integers before calculation
                    earned_cents = budget_info.get('earned_cents', 0)
                    spent_cents = budget_info.get('spent_cents', 0)
                    if not (isinstance(earned_cents, int) and isinstance(spent_cents, int)):
                         click.echo("Error: Invalid budget data types.", err=True)
                         # Optionally reset budget_info to prevent repeated errors
                         # budget_info = None
                    else:
                        # Convert cents to dollars for display
                        balance_dollars = (earned_cents + spent_cents) / 100.0
                        # The earnings calculation seems specific, apply conversion here too
                        earnings_dollars = (earned_cents - 1000) / 100.0 
                        click.echo(click.style(f"Balance: ${balance_dollars:.2f}", fg='green'))
                        click.echo(f"Earnings: ${earnings_dollars:.2f}")
                        click.echo() # Add a blank line for spacing
                except Exception as e:
                     # Catch potential calculation errors, though type checks should prevent most
                     click.echo(f"Error displaying budget: {e}", err=True)
                     # budget_info = None # Prevent repeated errors

            device_status = get_device_status()
            status_emoji = "🟢" if device_status else "🔴"

            if monitor.current_job:
                click.echo(f"\n📋 Job running on device: {monitor.current_job['filename']}\n")

            choices = [
                ("View Resources", "1"),
                ("View Jobs", "2"),
                (f"{'Disable' if device_status else 'Enable'} Your Device [{status_emoji}]", "3"),
                ("Exit", "4")
            ]
            
            questions = [
                inquirer.List('choice',
                            message="Select an option",
                            choices=choices,
                            carousel=True)
            ]
            
            try:
                answers = inquirer.prompt(questions)
                if not answers:
                    break
                    
                choice = answers['choice']
                
                if choice == "1":
                    monitor.set_status("BUSY")
                    click.clear()
                    display_resources()
                    monitor.set_status("ACTIVE" if device_status else "INACTIVE")
                elif choice == "2":
                    monitor.set_status("BUSY")
                    click.clear()
                    display_jobs()
                    monitor.set_status("ACTIVE" if device_status else "INACTIVE")
                elif choice == "3":
                    new_status = not device_status
                    set_device_status(new_status)
                    monitor.set_status("ACTIVE" if new_status else "INACTIVE")
                elif choice == "4":
                    break
                    
            except (KeyboardInterrupt, EOFError):
                break
                
    finally:
        monitor.stop()

@click.group(invoke_without_command=True)
@click.pass_context
@click.option('--hardreset', is_flag=True, help='Reset all user data and restart signup flow')
@click.option('--deletejob', is_flag=True, help='Delete any queued job data from the device')
@click.option('--use-ngrok', is_flag=True, help='Use ngrok to expose the local server publicly')
@click.option('--dev', is_flag=True, default=False, help='Use development API endpoint (localhost:8787)')
def main(ctx, hardreset, deletejob, use_ngrok, dev):
    global ngrok_tunnel
    
    # Set API Base URL based on --dev flag
    if dev:
        set_api_base_url("http://localhost:8787")
        click.echo(f"Using development API: {API_BASE_URL}")
    else:
        # The default is already set in config.py, but we can echo it for clarity
        click.echo(f"Using production API: {API_BASE_URL}")

    if use_ngrok and ngrok is None:
        click.echo("Error: The 'pyngrok' library is required for --use-ngrok but not installed.", err=True)
        click.echo("Please install it using: pip install pyngrok", err=True)
        return

    if ctx.invoked_subcommand is None:
        user_id = None
        if hardreset:
            if click.confirm('This will delete all your local user data. Are you sure?'):
                click.echo('Clearing all user data...')
                clear_user_data()
                click.echo('Data cleared. Starting fresh signup flow.')
                user_id = None
            else:
                click.echo('Operation cancelled.')
                return
        elif deletejob:
            monitor.current_job = None
            clear_current_job()
            click.echo('Cleared any queued job data from the device.')
            set_tunnel_url("") 
            return
        else:
            user_id = get_user_id()

        # --- Ngrok Installation Check (only if --use-ngrok) ---
        if use_ngrok and not shutil.which('ngrok'):
            click.echo("Ngrok executable not found in PATH.")
            system = platform.system()
            if system == "Linux" or system == "Darwin":
                install_command = (
                    "curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.zip -o ngrok.zip && "
                    "unzip -o ngrok.zip && sudo mv ngrok /usr/local/bin"
                )
                click.echo("This tool requires ngrok for secure connections when using --use-ngrok.")
                click.echo("The following command will be run to install it:")
                click.echo(f"  {install_command}")
                click.echo("Note: This requires curl, unzip, and sudo privileges.")
                
                if click.confirm("Do you want to attempt installation now?", default=True):
                    click.echo("Attempting to install ngrok...")
                    try:
                        result = subprocess.run(install_command, shell=True, check=True, capture_output=True, text=True)
                        click.echo("Ngrok installation successful!")
                        if os.path.exists("ngrok.zip"):
                            os.remove("ngrok.zip")
                    except subprocess.CalledProcessError as e:
                        click.echo(f"Error during ngrok installation: {e}", err=True)
                        click.echo(f"Stderr: {e.stderr}", err=True)
                        click.echo("Please install ngrok manually from https://ngrok.com/download and ensure it's in your PATH.", err=True)
                        return
                    except FileNotFoundError:
                         click.echo("Error: 'curl' or 'unzip' command not found. Please install them and try again, or install ngrok manually.", err=True)
                         return
                    except Exception as e:
                        click.echo(f"An unexpected error occurred during installation: {e}", err=True)
                        click.echo("Please install ngrok manually from https://ngrok.com/download and ensure it's in your PATH.", err=True)
                        return
                else:
                    click.echo("Installation cancelled. Ngrok is required for --use-ngrok.")
                    return
            else:
                click.echo(f"Automatic installation not supported for your OS ({system}).")
                click.echo("Please install ngrok manually from https://ngrok.com/download and ensure it's in your PATH.")
                return
        # --- End Ngrok Installation Check ---

        if not user_id:
            click.echo("You need to sign up first!")
            click.echo(f"Opening browser to sign up. If it doesn't open automatically, please visit:\n{WEB_APP_URL}")
            webbrowser.open(WEB_APP_URL)
            
            user_id_input = click.prompt("Please enter your user ID from the web app", type=str)
            set_user_id(user_id_input)
            user_id = user_id_input
            click.echo("User ID stored successfully!")

        ngrok_configured = False
        ngrok_token = None
        
        # --- Ngrok Configuration and Tunnel Start (only if --use-ngrok) ---
        if use_ngrok and user_id:
            ngrok_token = get_ngrok_token()
            ngrok_id = get_ngrok_id() # Keep ngrok_id fetching for potential future use

            if not ngrok_token:
                click.echo("Setting up secure connection details (ngrok)...")
                try:
                    response = requests.post(
                        f"{API_BASE_URL}/get-ngrok-access",
                        json={'user_id': user_id},
                        timeout=10
                    )
                    response.raise_for_status()

                    if response.status_code == 200:
                        data = response.json()
                        new_token = data.get('token')
                        new_id = data.get('id') # Keep getting ID

                        if new_token:
                            set_ngrok_token(new_token)
                            if new_id: # Store ID if received
                                set_ngrok_id(new_id)
                            ngrok_token = new_token
                            click.echo("Ngrok authtoken configured successfully.")
                            ngrok_configured = True
                        else:
                            click.echo("Error: Received incomplete ngrok details from server.")
                            return # Exit if ngrok setup fails when requested
                    else:
                        click.echo(f"Error: Failed to get ngrok details (Status: {response.status_code}).")
                        return # Exit if ngrok setup fails when requested
                except requests.exceptions.RequestException as e:
                    click.echo(f"Error: Could not connect to server to get ngrok details: {e}")
                    return # Exit if ngrok setup fails when requested
                except Exception as e:
                    click.echo(f"An unexpected error occurred during ngrok setup: {e}")
                    return # Exit if ngrok setup fails when requested
            else:
                ngrok_configured = True # Already have a token

            if ngrok_configured and shutil.which('ngrok'):
                click.echo(f"Starting ngrok tunnel for http://localhost:{LOCAL_PORT}...")
                try:
                    conf.get_default().auth_token = ngrok_token
                    ngrok_tunnel = ngrok.connect(LOCAL_PORT, "http")
                    public_url = ngrok_tunnel.public_url

                    # Prefer HTTPS tunnel if available
                    https_tunnel = None
                    for tunnel in ngrok.get_tunnels():
                        if tunnel.proto == "https" and tunnel.config['addr'] == f"http://localhost:{LOCAL_PORT}":
                            https_tunnel = tunnel
                            break
                    
                    if https_tunnel:
                        public_url = https_tunnel.public_url
                        click.echo(f"Ngrok HTTPS tunnel established: {public_url}")
                        set_tunnel_url(public_url) # Set URL only on success
                    elif public_url.startswith("http://"): # Fallback to HTTP if no HTTPS found
                        click.echo(f"Warning: Could not find HTTPS ngrok tunnel. Using HTTP: {public_url}")
                        set_tunnel_url(public_url) # Set URL only on success
                    else: # Should not happen if connect succeeded, but handle defensively
                         click.echo(f"Ngrok tunnel established but URL format unexpected: {public_url}")
                         set_tunnel_url(public_url) # Set URL only on success

                except ngrok_exception.PyngrokNgrokError as e:
                    error_str = str(e)
                    if "CERTIFICATE_VERIFY_FAILED" in error_str or "[SSL" in error_str:
                        click.echo("---------------------------------------------------------", err=True)
                        click.echo("ERROR: Failed to download/verify ngrok due to SSL issue.", err=True)
                        click.echo(f"Details: {error_str}", err=True)
                        click.echo("\nThis is often caused by outdated or misconfigured SSL certificates", err=True)
                        click.echo("in your Python environment or operating system.", err=True)
                        click.echo("\nPossible solutions:", err=True)
                        click.echo("1. If on macOS, try running 'Install Certificates.command' in your Python installation directory.", err=True)
                        click.echo("   (Often found in /Applications/Python 3.x/)", err=True)
                        click.echo("2. Ensure your system's root certificates are up to date.", err=True)
                        click.echo("3. Manually download ngrok from https://ngrok.com/download,", err=True)
                        click.echo("   unzip it, and place the 'ngrok' executable in a directory", err=True)
                        click.echo("   listed in your system's PATH environment variable.", err=True)
                        click.echo("   This bypasses the automatic download.", err=True)
                        click.echo("---------------------------------------------------------", err=True)
                    else:
                        click.echo(f"Error starting ngrok tunnel: {e}", err=True)
                        click.echo("Please ensure ngrok is configured correctly and your authtoken is valid.")
                    
                    cleanup_ngrok() # Attempt cleanup even on error
                    return # Exit if ngrok tunnel fails when requested
                except Exception as e:
                    click.echo(f"An unexpected error occurred while starting ngrok: {e}", err=True)
                    cleanup_ngrok() # Attempt cleanup even on error
                    return # Exit if ngrok tunnel fails when requested
            elif not ngrok_configured:
                click.echo("Ngrok setup incomplete, cannot start tunnel.", err=True)
                return # Exit if ngrok setup fails when requested
            elif not shutil.which('ngrok'):
                 click.echo("Ngrok executable not found, cannot start tunnel.", err=True)
                 return # Exit if ngrok executable missing when requested
        # --- End Ngrok Configuration and Tunnel Start ---

        # Proceed to main menu if:
        # 1. Ngrok was requested AND the tunnel started successfully (ngrok_tunnel is not None)
        # 2. Ngrok was NOT requested
        if (use_ngrok and ngrok_tunnel) or (not use_ngrok):
             if not use_ngrok:
                 click.echo("Skipping ngrok setup as --use-ngrok flag was not provided.")
                 # Ensure tunnel URL is cleared if not using ngrok
                 set_tunnel_url("") 
             show_main_menu()
        elif use_ngrok and not ngrok_tunnel:
             # This case should ideally be caught by the return statements above,
             # but added for robustness.
             click.echo("Failed to initialize ngrok tunnel as requested. Exiting.", err=True)
        # else: # This case (not use_ngrok and ngrok_tunnel exists) shouldn't happen
        #     pass 

@main.command()
def hello():
    click.echo("Hello from give-my-resources!")