# give-my-resources

A command-line interface tool for resource management.

## Installation

To install the package in development mode:

```bash
pip3 install -e .
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
- `--dev`: Use development API endpoint (localhost:8787) instead of production.

## Building the Executable (macOS)

To create a standalone executable bundle for macOS:

1.  **Install build dependencies:**
    ```bash
    pip3 install .[build]
    # or: pip3 install pyinstaller
    ```

2.  **Run PyInstaller:**
    From the project root directory:
    ```bash
    pyinstaller --name gmr --onefile --console src/give_my_resources/cli.py
    ```
    *   `--onefile`: Creates a single executable file in the `dist/` folder.
    *   `--onedir`: (Alternative) Creates a folder in `dist/` containing the executable and its dependencies. This can be easier to debug and sometimes starts faster.
    *   You may need additional options like `--hidden-import=module_name` if PyInstaller misses some dependencies, or `--add-binary` / `--add-data` if specific binaries (like `ngrok`) or data files aren't included automatically. See PyInstaller documentation for details.

3.  **Find the Executable:**
    The executable will be located at `dist/gmr` (if using `--onefile`) or `dist/gmr/gmr` (if using `--onedir`).

**Note:** Building with PyInstaller, especially with dependencies like `pyngrok` that manage external binaries, may require testing and adjustments to the build command to ensure everything is bundled correctly. Test the `--use-ngrok` flag specifically in the bundled application.