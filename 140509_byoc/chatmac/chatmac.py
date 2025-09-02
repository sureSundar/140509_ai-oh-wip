#!/usr/bin/env python3
"""
ChatMac - Cross-Platform AI Chat to OS Command Interface
Supports Mac, Ubuntu Linux, Windows 11 with layered AI services (Claude -> OpenAI -> Ollama)
"""

import os
import sys
import json
import platform
import subprocess
import requests
import readline
from typing import Dict, List, Tuple, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class AIProvider:
    """Base class for AI providers"""
    def __init__(self, name: str):
        self.name = name
        self.available = False
        self.timeout = 5
    
    def query(self, prompt: str) -> Optional[str]:
        """Override in subclasses"""
        return None

class ClaudeAI(AIProvider):
    def __init__(self):
        super().__init__("Claude")
        self.api_key = os.getenv('ANTHROPIC_API_KEY')
        self.available = self._check_availability()
    
    def _check_availability(self):
        # Just check if API key exists and has correct format
        return bool(self.api_key and self.api_key.startswith('sk-ant'))
    
    def query(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 200,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()['content'][0]['text'].strip()
            else:
                print(f"Claude API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"Claude error: {e}")
        return None

class OpenAI(AIProvider):
    def __init__(self):
        super().__init__("OpenAI")
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.available = self._check_availability()
    
    def _check_availability(self):
        # Just check if API key exists and has correct format
        return bool(self.api_key and self.api_key.startswith('sk-'))
    
    def query(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
        
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 200,
                    "temperature": 0.1
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['message']['content'].strip()
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                
        except Exception as e:
            print(f"OpenAI error: {e}")
        return None

class OllamaAI(AIProvider):
    def __init__(self):
        super().__init__("Ollama")
        self.base_url = os.getenv('OLLAMA_BASE_URL', "http://localhost:11434")
        self.model = os.getenv('OLLAMA_MODEL', "llama3.1")
        self.available = self._check_availability()
    
    def _check_availability(self):
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def query(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
        
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                },
                timeout=3
            )
            
            if response.status_code == 200:
                return response.json()["response"].strip()
                
        except Exception as e:
            print(f"Ollama error: {e}")
        return None

class CrossPlatformCommands:
    """Cross-platform command mappings"""
    
    def __init__(self):
        self.platform = self._detect_platform()
        self.commands = self._load_command_mappings()
    
    def _detect_platform(self) -> str:
        """Detect the operating system"""
        system = platform.system().lower()
        if system == "darwin":
            return "mac"
        elif system == "linux":
            # Check if it's Ubuntu
            try:
                with open('/etc/os-release', 'r') as f:
                    content = f.read()
                    if 'ubuntu' in content.lower():
                        return "ubuntu"
                    else:
                        return "linux"
            except:
                return "linux"
        elif system == "windows":
            return "windows"
        else:
            return "unknown"
    
    def _load_command_mappings(self) -> Dict:
        """Load platform-specific command mappings"""
        return {
            "mac": {
                "list_files": "ls -la",
                "current_directory": "pwd",
                "change_directory": "cd {path}",
                "create_directory": "mkdir {name}",
                "remove_file": "rm {file}",
                "copy_file": "cp {src} {dst}",
                "move_file": "mv {src} {dst}",
                "find_file": "find {path} -name '{pattern}'",
                "disk_usage": "df -h",
                "memory_usage": "top -l 1 | head -20",
                "process_list": "ps aux",
                "kill_process": "kill {pid}",
                "network_info": "ifconfig",
                "system_info": "uname -a",
                "open_application": "open -a '{app}'",
                "show_hidden_files": "ls -la",
                "compress_files": "tar -czf {archive}.tar.gz {files}",
                "extract_archive": "tar -xzf {archive}",
                "text_editor": "nano {file}",
                "file_permissions": "chmod {mode} {file}",
                "search_text": "grep -r '{pattern}' {path}",
                "download_file": "curl -O {url}",
                "system_update": "brew update && brew upgrade"
            },
            "ubuntu": {
                "list_files": "ls -la",
                "current_directory": "pwd",
                "change_directory": "cd {path}",
                "create_directory": "mkdir {name}",
                "remove_file": "rm {file}",
                "copy_file": "cp {src} {dst}",
                "move_file": "mv {src} {dst}",
                "find_file": "find {path} -name '{pattern}'",
                "disk_usage": "df -h",
                "memory_usage": "free -h && top -bn1 | head -20",
                "process_list": "ps aux",
                "kill_process": "kill {pid}",
                "network_info": "ip addr show",
                "system_info": "uname -a",
                "open_application": "{app}",
                "show_hidden_files": "ls -la",
                "compress_files": "tar -czf {archive}.tar.gz {files}",
                "extract_archive": "tar -xzf {archive}",
                "text_editor": "nano {file}",
                "file_permissions": "chmod {mode} {file}",
                "search_text": "grep -r '{pattern}' {path}",
                "download_file": "wget {url}",
                "system_update": "sudo apt update && sudo apt upgrade",
                "install_package": "sudo apt install {package}",
                "service_status": "systemctl status {service}",
                "start_service": "sudo systemctl start {service}",
                "stop_service": "sudo systemctl stop {service}"
            },
            "windows": {
                "list_files": "dir",
                "current_directory": "cd",
                "change_directory": "cd {path}",
                "create_directory": "mkdir {name}",
                "remove_file": "del {file}",
                "copy_file": "copy {src} {dst}",
                "move_file": "move {src} {dst}",
                "find_file": "dir {path}\\{pattern} /s",
                "disk_usage": "wmic logicaldisk get size,freespace,caption",
                "memory_usage": "tasklist /fo table",
                "process_list": "tasklist",
                "kill_process": "taskkill /pid {pid} /f",
                "network_info": "ipconfig /all",
                "system_info": "systeminfo",
                "open_application": "start {app}",
                "show_hidden_files": "dir /ah",
                "compress_files": "powershell Compress-Archive {files} {archive}.zip",
                "extract_archive": "powershell Expand-Archive {archive}",
                "text_editor": "notepad {file}",
                "file_permissions": "icacls {file}",
                "search_text": "findstr /r /s '{pattern}' {path}",
                "download_file": "powershell Invoke-WebRequest {url} -OutFile {filename}",
                "system_update": "powershell Get-WindowsUpdate"
            }
        }
    
    def get_command_template(self, action: str) -> Optional[str]:
        """Get command template for the current platform"""
        return self.commands.get(self.platform, {}).get(action)

class LayeredAI:
    """Layered AI service with fallback chain: Claude -> OpenAI -> Ollama"""
    
    def __init__(self):
        self.claude = ClaudeAI()
        self.openai = OpenAI()
        self.ollama = OllamaAI()
        self.providers = [self.claude, self.openai, self.ollama]
        self.active_provider = None
        
        # Initialize the first available provider
        for provider in self.providers:
            if provider.available:
                self.active_provider = provider
                break
    
    def query(self, prompt: str) -> Tuple[Optional[str], str]:
        """Query AI providers in order until one succeeds"""
        for provider in self.providers:
            if provider.available:
                try:
                    print(f"🤖 Trying {provider.name}...")
                    response = provider.query(prompt)
                    if response:
                        self.active_provider = provider
                        return response, provider.name
                except Exception as e:
                    print(f"❌ {provider.name} failed: {e}")
                    continue
        
        return None, "None"

class ChatMac:
    """Main ChatMac interface"""
    
    def __init__(self):
        self.ai = LayeredAI()
        self.platform_commands = CrossPlatformCommands()
        self.conversation_history = []
        self.command_history = []
        
        # Setup readline for command history
        self._setup_readline()
        
        print(f"🖥️  ChatMac initialized for {self.platform_commands.platform.upper()}")
        print(f"🤖 Available AI services:")
        for provider in self.ai.providers:
            status = "✅" if provider.available else "❌"
            print(f"   {status} {provider.name}")
    
    def _setup_readline(self):
        """Setup readline for command history and arrow key navigation"""
        try:
            # Enable tab completion
            readline.parse_and_bind('tab: complete')
            # Enable history navigation with arrow keys
            readline.parse_and_bind('set editing-mode emacs')
            readline.parse_and_bind('"\e[A": history-search-backward')
            readline.parse_and_bind('"\e[B": history-search-forward')
            
            # Load history from file if it exists
            history_file = os.path.expanduser("~/.chatmac_history")
            if os.path.exists(history_file):
                readline.read_history_file(history_file)
                
        except Exception as e:
            print(f"Warning: Could not setup command history: {e}")
    
    def _save_history(self):
        """Save command history to file"""
        try:
            history_file = os.path.expanduser("~/.chatmac_history")
            readline.write_history_file(history_file)
        except:
            pass
    
    def create_prompt(self, user_input: str) -> str:
        """Create AI prompt for command generation"""
        platform_name = {
            "mac": "macOS",
            "ubuntu": "Ubuntu Linux", 
            "windows": "Windows 11",
            "linux": "Linux"
        }.get(self.platform_commands.platform, "Unknown OS")
        
        return f"""You are an AI assistant that converts natural language requests to {platform_name} terminal/command-line commands.

Current OS: {platform_name}
User Request: {user_input}

Your task:
1. Analyze the user's request
2. If you need more information, ask a follow-up question
3. If you have enough information, generate the appropriate terminal command
4. Respond in JSON format with keys: "terminal_command", "followup", "explanation"

Rules:
- "terminal_command": The exact command to run (empty string if you need more info)
- "followup": Question to ask user if you need clarification (empty string if command is ready)
- "explanation": Brief explanation of what the command does
- Generate commands that work on {platform_name}
- Ensure commands are safe and don't perform destructive actions without confirmation
- For file paths, use appropriate separators for the OS

Example responses:
{{"terminal_command": "ls -la", "followup": "", "explanation": "Lists all files and directories with details"}}
{{"terminal_command": "", "followup": "Which directory would you like to list files from?", "explanation": "Need directory path to proceed"}}

Respond only with valid JSON."""

    def execute_command(self, command: str, auto_confirm: bool = False) -> str:
        """Execute terminal command safely with user confirmation"""
        if not command.strip():
            return "No command to execute."
        
        # Safety check for destructive commands
        dangerous_commands = ['rm -rf /', 'del /s /q', 'format', 'fdisk', 'mkfs']
        if any(dangerous in command.lower() for dangerous in dangerous_commands):
            return "❌ Dangerous command detected. Execution blocked for safety."
        
        # Show command and ask for confirmation
        if not auto_confirm:
            print(f"\n🔧 Command to execute: {command}")
            try:
                confirm = input("❓ Execute this command? [Y/n]: ").strip().lower()
                if confirm not in ['', 'y', 'yes']:
                    return "❌ Command execution cancelled by user."
            except KeyboardInterrupt:
                return "❌ Command execution cancelled."
        
        try:
            print(f"🔧 Executing: {command}")
            
            # Execute command based on platform
            if self.platform_commands.platform == "windows":
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd())
            else:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, cwd=os.getcwd())
            
            if result.returncode == 0:
                output = result.stdout.strip()
                return f"✅ Command executed successfully:\n{output}" if output else "✅ Command executed successfully (no output)"
            else:
                error = result.stderr.strip()
                return f"❌ Error occurred:\n{error}" if error else f"❌ Command failed with return code {result.returncode}"
                
        except Exception as e:
            return f"❌ Exception occurred: {str(e)}"
    
    def process_user_input(self, user_input: str) -> str:
        """Process user input and generate response"""
        if user_input.lower().strip() in ['exit', 'quit', 'bye', 'goodbye']:
            return "Goodbye! 👋"
        
        # Create AI prompt
        prompt = self.create_prompt(user_input)
        
        # Query AI
        response, provider_used = self.ai.query(prompt)
        
        if not response:
            return "❌ No AI services available. Please check your configuration."
        
        try:
            # Parse JSON response
            ai_response = json.loads(response)
            
            terminal_command = ai_response.get("terminal_command", "").strip()
            followup = ai_response.get("followup", "").strip()
            explanation = ai_response.get("explanation", "").strip()
            
            result_parts = []
            
            if explanation:
                result_parts.append(f"💡 {explanation}")
            
            if terminal_command:
                # Execute the command
                execution_result = self.execute_command(terminal_command)
                result_parts.append(execution_result)
            
            if followup:
                result_parts.append(f"❓ {followup}")
            
            # Add provider info
            result_parts.append(f"(via {provider_used})")
            
            return "\n\n".join(result_parts)
            
        except json.JSONDecodeError:
            # If JSON parsing fails, treat as direct command or explanation
            return f"🤖 {provider_used}: {response}"
        except Exception as e:
            return f"❌ Error processing AI response: {str(e)}\nRaw response: {response}"
    
    def start_chat(self):
        """Start the interactive chat loop"""
        print("\n" + "="*60)
        print("🚀 Welcome to ChatMac - AI-Powered Cross-Platform Terminal Assistant!")
        print(f"📱 Running on: {self.platform_commands.platform.upper()}")
        print("💬 Type your requests in natural language")
        print("🔧 I'll convert them to terminal commands and execute them")
        print("🔼🔽 Use ↑/↓ arrow keys to navigate command history")
        print("❌ Type 'exit', 'quit', or 'bye' to quit")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("🗣️  You: ").strip()
                if not user_input:
                    continue
                
                # Add to readline history for arrow key navigation
                readline.add_history(user_input)
                self.command_history.append(user_input)
                
                response = self.process_user_input(user_input)
                print(f"🤖 ChatMac: {response}\n")
                
                if user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    self._save_history()
                    break
                    
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye! Thanks for using ChatMac!")
                self._save_history()
                break
            except EOFError:
                print("\n\n👋 Goodbye! Thanks for using ChatMac!")
                self._save_history()
                break
            except Exception as e:
                print(f"❌ Unexpected error: {str(e)}")

def main():
    """Main entry point"""
    try:
        chatmac = ChatMac()
        chatmac.start_chat()
    except Exception as e:
        print(f"❌ Failed to start ChatMac: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()