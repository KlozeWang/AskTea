#!/usr/bin/env python3
"""
Generate SSH config entry for Azure ML job SSH connection.

Usage:
    python gen_azureml_ssh_config.py "az ml job connect-ssh --name <job_name> --node-index 0 --private-key-file-path <filepath> --workspace-name <ws> --resource-group <rg> --subscription <sub>"

Or run interactively:
    python gen_azureml_ssh_config.py
"""

import subprocess
import re
import sys
import os
from pathlib import Path


DEFAULT_KEY_PATH = "/home/shaohanh/.ssh/id_rsa_msra"


def parse_ssh_command(verbose_output: str) -> dict | None:
    """Extract SSH connection info from az ml job connect-ssh verbose output."""

    # Look for the ssh_command line
    # Example: ssh_command: ssh -v -o ProxyCommand="..." azureuser@wss://... -i /path/to/key
    match = re.search(r'ssh_command:\s*(.+)', verbose_output)
    if not match:
        print("Error: Could not find ssh_command in output")
        return None

    ssh_command = match.group(1).strip()

    # Extract ProxyCommand
    proxy_match = re.search(r'ProxyCommand="([^"]+)"', ssh_command)
    if not proxy_match:
        print("Error: Could not find ProxyCommand")
        return None
    proxy_command = proxy_match.group(1).strip()

    # Extract user@host
    user_host_match = re.search(r'(\w+)@(wss://[^\s]+)', ssh_command)
    if not user_host_match:
        print("Error: Could not find user@host")
        return None
    user = user_host_match.group(1)
    hostname = user_host_match.group(2)

    # Extract identity file
    identity_match = re.search(r'-i\s+(\S+)', ssh_command)
    identity_file = identity_match.group(1) if identity_match else DEFAULT_KEY_PATH

    # Extract job name from the wss URL for the Host alias
    # wss://ssh-16965hf7edgyzmtyhgeswmhv4kesmgaw4rzltgwy57wnz7okxzc.eastus.nodes.azureml.ms
    job_id_match = re.search(r'wss://ssh-([a-z0-9]+)\.', hostname)
    job_id_short = job_id_match.group(1)[:12] if job_id_match else "azureml"

    return {
        "host_alias": f"azureml-{job_id_short}",
        "hostname": hostname,
        "user": user,
        "identity_file": identity_file,
        "proxy_command": proxy_command,
    }


def generate_ssh_config(info: dict) -> str:
    """Generate SSH config entry from parsed info."""
    config = f"""Host {info['host_alias']}
    HostName {info['hostname']}
    User {info['user']}
    IdentityFile {info['identity_file']}
    ProxyCommand {info['proxy_command']}
    StrictHostKeyChecking no
    UserKnownHostsFile /dev/null
"""
    return config


def run_az_command(command: str, key_path: str) -> str | None:
    """Run az ml job connect-ssh command with --verbose and capture output."""

    # Replace <filepath> placeholder with actual key path
    command = command.replace("<filepath>", key_path)

    # Add --verbose if not present
    if "--verbose" not in command:
        command = command + " --verbose"

    print(f"Running: {command}\n")

    try:
        # Run the command and capture both stdout and stderr
        # Use input="y\n" to automatically answer 'y' to prompts (e.g., websockets install)
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
            input="y\n",
        )

        # Combine stdout and stderr as verbose output goes to stderr
        output = result.stdout + result.stderr
        return output

    except subprocess.TimeoutExpired:
        print("Error: Command timed out")
        return None
    except Exception as e:
        print(f"Error running command: {e}")
        return None


def main():
    # Get command from argument or prompt
    if len(sys.argv) > 1:
        command = " ".join(sys.argv[1:])
    else:
        print("Enter the az ml job connect-ssh command (with <filepath> as placeholder for key path):")
        print("Example: az ml job connect-ssh --name olive_peach_k8hkc21k8z --node-index 0 --private-key-file-path <filepath> --workspace-name Workspace_NLC --resource-group DNN --subscription 90b9bfec-2ded-494a-9ccc-b584c55f454f")
        print()
        command = input("> ").strip()

    if not command:
        print("No command provided")
        sys.exit(1)

    # Get key path
    key_path = os.environ.get("AZUREML_SSH_KEY", DEFAULT_KEY_PATH)
    print(f"Using SSH key: {key_path}")
    print()

    # Run the command
    output = run_az_command(command, key_path)
    if not output:
        sys.exit(1)

    # Parse the output
    info = parse_ssh_command(output)
    if not info:
        print("\nFull output for debugging:")
        print("-" * 50)
        print(output)
        sys.exit(1)

    # Generate SSH config
    ssh_config = generate_ssh_config(info)

    print("=" * 60)
    print("Generated SSH Config Entry:")
    print("=" * 60)
    print(ssh_config)
    print("=" * 60)

    # Provide instructions
    print(f"""
Instructions:
1. Add the above config to ~/.ssh/config

2. Connect via terminal:
   ssh {info['host_alias']}

3. Connect via VS Code:
   - Press Cmd+Shift+P (Mac) or Ctrl+Shift+P (Windows/Linux)
   - Type: Remote-SSH: Connect to Host...
   - Select: {info['host_alias']}

Note: The WebSocket URL is temporary. If the job restarts or you get
disconnected, run this script again to get the new URL.
""")

    # Allow user to customize host name
    custom_host = input(f"\nEnter custom Host name (or press Enter to use '{info['host_alias']}'): ").strip()
    if custom_host:
        info['host_alias'] = custom_host
        ssh_config = generate_ssh_config(info)
        print("\nUpdated SSH Config Entry:")
        print("=" * 60)
        print(ssh_config)
        print("=" * 60)

    # Optionally append to SSH config
    ssh_config_path = Path.home() / ".ssh" / "config"
    response = input(f"Add to {ssh_config_path}? [y/N]: ").strip().lower()
    if response == 'y':
        # Check if this host already exists
        if ssh_config_path.exists():
            existing_config = ssh_config_path.read_text()
            if info['host_alias'] in existing_config:
                print(f"Warning: Host '{info['host_alias']}' already exists in config.")
                overwrite = input("Remove old entry and add new one? [y/N]: ").strip().lower()
                if overwrite == 'y':
                    # Remove old entry
                    lines = existing_config.split('\n')
                    new_lines = []
                    skip = False
                    for line in lines:
                        if line.strip().startswith(f"Host {info['host_alias']}"):
                            skip = True
                        elif skip and line.strip().startswith("Host "):
                            skip = False
                        if not skip:
                            new_lines.append(line)
                    ssh_config_path.write_text('\n'.join(new_lines))
                else:
                    print("Skipped.")
                    return

        # Insert at the beginning of the config file
        existing_content = ssh_config_path.read_text() if ssh_config_path.exists() else ""
        ssh_config_path.write_text(ssh_config + "\n" + existing_content)
        print(f"Inserted at the beginning of {ssh_config_path}")


if __name__ == "__main__":
    main()
