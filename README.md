# give-my-resources

A command-line interface tool for resource management.

## Installation

To install the package in development mode:

```bash
pip install -e .
```

## Usage

After installation, you can use the CLI by running:

```bash
gmr hello
```

## Commands

- `hello`: Test command that prints a greeting

## Flags

- `--hardreset`: Reset all user data and restart signup flow
- `--deletejob`: Delete any queued job data from the device (useful for debugging)
- `--use-ngrok`: Use ngrok to expose the local heartbeat server publicly. Requires ngrok to be installed and configured (either automatically or manually). If not set, the device will not be publicly discoverable for receiving jobs.