"""
Configuration management for give-my-resources
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path.home() / '.give-my-resources'
CONFIG_FILE = CONFIG_DIR / 'config.json'

# Default API Base URL (Production)
API_BASE_URL = "https://vibe25-worker.pumpkin-executables.workers.dev/"

def set_api_base_url(url: str):
    """Set the API base URL globally"""
    global API_BASE_URL
    API_BASE_URL = url

def ensure_config_dir():
    """Ensure the config directory exists"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

def get_user_id():
    """Get the stored user ID if it exists"""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
            return config.get('user_id')
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def set_user_id(user_id: str):
    """Store the user ID"""
    ensure_config_dir()
    config = get_config() or {}
    config['user_id'] = user_id
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_config():
    """Get the full config if it exists"""
    if not CONFIG_FILE.exists():
        return None
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None

def get_refresh_token():
    """Get the stored refresh token if it exists"""
    config = get_config()
    return config.get('refresh_token') if config else None

def set_refresh_token(refresh_token: str):
    """Store the refresh token"""
    ensure_config_dir()
    config = get_config() or {}
    config['refresh_token'] = refresh_token
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_device_status():
    """Get the device status (enabled/disabled)"""
    config = get_config()
    return config.get('device_enabled', False) if config else False

def set_device_status(enabled: bool):
    """Store the device status"""
    ensure_config_dir()
    config = get_config() or {}
    config['device_enabled'] = enabled
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_current_job():
    """Get the stored current job if it exists"""
    config = get_config()
    return config.get('current_job') if config else None

def set_current_job(job_data: dict):
    """Store the current job data"""
    ensure_config_dir()
    config = get_config() or {}
    config['current_job'] = job_data
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def clear_current_job():
    """Clear the current job data"""
    ensure_config_dir()
    config = get_config() or {}
    if 'current_job' in config:
        del config['current_job']
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_ngrok_token():
    """Get the stored ngrok token if it exists"""
    config = get_config()
    return config.get('ngrok_token') if config else None

def set_ngrok_token(token: str):
    """Store the ngrok token"""
    ensure_config_dir()
    config = get_config() or {}
    config['ngrok_token'] = token
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_ngrok_id():
    """Get the stored ngrok ID if it exists"""
    config = get_config()
    return config.get('ngrok_id') if config else None

def set_ngrok_id(ngrok_id: str):
    """Store the ngrok ID"""
    ensure_config_dir()
    config = get_config() or {}
    config['ngrok_id'] = ngrok_id
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def get_tunnel_url():
    """Get the stored ngrok tunnel URL if it exists"""
    config = get_config()
    return config.get('tunnel_url') if config else None

def set_tunnel_url(url: str):
    """Store the ngrok tunnel URL"""
    ensure_config_dir()
    config = get_config() or {}
    config['tunnel_url'] = url
    
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f)

def clear_user_data():
    """Clear all user data from config file"""
    if CONFIG_FILE.exists():
        try:
            os.remove(CONFIG_FILE)
        except OSError:
            pass
    ensure_config_dir()
    with open(CONFIG_FILE, 'w') as f:
        json.dump({}, f)