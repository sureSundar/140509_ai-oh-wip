"""Generate a .env file from .env.example if it doesn't exist."""
import os
import sys
from pathlib import Path

def generate_env():
    """Generate .env file if it doesn't exist."""
    env_path = Path(".env")
    example_path = Path(".env.example")
    
    if not example_path.exists():
        print("Error: .env.example file not found.", file=sys.stderr)
        sys.exit(1)
    
    if env_path.exists():
        print(".env file already exists. Skipping generation.")
        return
    
    try:
        with open(example_path, 'r') as example_file:
            with open(env_path, 'w') as env_file:
                env_file.write(example_file.read())
        print("Generated .env file from .env.example")
    except Exception as e:
        print(f"Error generating .env file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    generate_env()
