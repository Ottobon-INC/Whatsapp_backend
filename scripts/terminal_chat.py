#!/usr/bin/env python3
"""
Terminal Chat Interface for Sakhi Chatbot
==========================================
Interactive CLI to test the Sakhi chatbot locally without needing WhatsApp.

Usage:
    1. Start the FastAPI server: uvicorn main:app --reload
    2. Run this script: python terminal_chat.py

Commands:
    /new     - Start a new session with a fresh user
    /user    - Show current user info
    /clear   - Clear the screen
    /help    - Show available commands
    /quit    - Exit the chat
"""

import requests
import json
import random
import string
import os
import sys

# Configuration
BASE_URL = os.getenv("SAKHI_API_URL", "http://127.0.0.1:8000")
CHAT_ENDPOINT = f"{BASE_URL}/sakhi/chat"
REGISTER_ENDPOINT = f"{BASE_URL}/user/register"

# ANSI Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def random_string(length=10):
    return ''.join(random.choices(string.ascii_lowercase, k=length))


def random_phone():
    return f"9{random.randint(100000000, 999999999)}"


def print_header():
    """Print the chat header."""
    clear_screen()
    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                    🌸 SAKHI CHATBOT TESTER 🌸                    ║")
    print("║                  Terminal Chat Interface v1.0                     ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}")
    print(f"{Colors.YELLOW}Type /help for available commands | /quit to exit{Colors.ENDC}\n")


def clear_screen():
    """Clear the terminal screen."""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_help():
    """Print available commands."""
    print(f"\n{Colors.HEADER}📋 Available Commands:{Colors.ENDC}")
    print(f"  {Colors.GREEN}/new{Colors.ENDC}     - Start a new session with a fresh user")
    print(f"  {Colors.GREEN}/phone{Colors.ENDC}   - Use a specific phone number (e.g., /phone 9876543210)")
    print(f"  {Colors.GREEN}/user{Colors.ENDC}    - Show current user info")
    print(f"  {Colors.GREEN}/clear{Colors.ENDC}   - Clear the screen")
    print(f"  {Colors.GREEN}/debug{Colors.ENDC}   - Toggle debug mode (show full API response)")
    print(f"  {Colors.GREEN}/help{Colors.ENDC}    - Show this help message")
    print(f"  {Colors.GREEN}/quit{Colors.ENDC}    - Exit the chat\n")


def print_user_info(user_data):
    """Print current user information."""
    print(f"\n{Colors.HEADER}👤 Current User Info:{Colors.ENDC}")
    if user_data:
        for key, value in user_data.items():
            print(f"  {Colors.CYAN}{key}:{Colors.ENDC} {value}")
    else:
        print(f"  {Colors.YELLOW}No user session active{Colors.ENDC}")
    print()


def check_server():
    """Check if the server is running."""
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            return True
    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return False
    return False


def send_message(phone_number, message, language="en"):
    """Send a message to the Sakhi chatbot."""
    payload = {
        "phone_number": phone_number,
        "message": message,
        "language": language
    }
    
    try:
        response = requests.post(
            CHAT_ENDPOINT,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=60  # Increased timeout
        )
        
        # Check for HTTP errors first
        if response.status_code != 200:
            try:
                error_json = response.json()
                return response.status_code, {"error": f"HTTP {response.status_code}: {error_json.get('detail', 'Unknown error')}"}
            except:
                return response.status_code, {"error": f"HTTP {response.status_code}: {response.text[:200]}"}
        
        return response.status_code, response.json()
    except requests.exceptions.Timeout:
        return None, {"error": "Request timed out. The server might be processing a complex query."}
    except requests.exceptions.ConnectionError:
        return None, {"error": "Cannot connect to server. Is the FastAPI server running?"}
    except json.JSONDecodeError as e:
        return response.status_code, {"error": f"Invalid JSON response: {response.text[:500]}"}
    except Exception as e:
        return None, {"error": str(e)}


def format_response(response_data, debug_mode=False):
    """Format the chatbot response for display."""
    if "error" in response_data:
        return f"{Colors.RED}❌ Error: {response_data['error']}{Colors.ENDC}"
    
    reply = response_data.get("reply", "No response")
    mode = response_data.get("mode", "unknown")
    route = response_data.get("route", "")
    language = response_data.get("language", "")
    
    formatted = f"\n{Colors.GREEN}🌸 Sakhi:{Colors.ENDC}\n{reply}\n"
    
    # Show metadata
    metadata_parts = []
    if mode:
        metadata_parts.append(f"Mode: {mode}")
    if route:
        metadata_parts.append(f"Route: {route}")
    if language:
        metadata_parts.append(f"Lang: {language}")
    
    if metadata_parts:
        formatted += f"\n{Colors.CYAN}[{' | '.join(metadata_parts)}]{Colors.ENDC}"
    
    # Show additional info
    if response_data.get("youtube_link"):
        formatted += f"\n{Colors.BLUE}📺 YouTube: {response_data['youtube_link']}{Colors.ENDC}"
    if response_data.get("infographic_url"):
        formatted += f"\n{Colors.BLUE}🖼️ Infographic: {response_data['infographic_url']}{Colors.ENDC}"
    if response_data.get("image"):
        formatted += f"\n{Colors.BLUE}📷 Image: {response_data['image']}{Colors.ENDC}"
    
    if debug_mode:
        formatted += f"\n\n{Colors.YELLOW}📋 Debug - Full Response:{Colors.ENDC}"
        formatted += f"\n{json.dumps(response_data, indent=2)}"
    
    return formatted


def main():
    """Main chat loop."""
    print_header()
    
    # Check if server is running
    print(f"{Colors.YELLOW}Checking server connection...{Colors.ENDC}")
    if not check_server():
        print(f"{Colors.RED}")
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║  ❌ ERROR: Cannot connect to the Sakhi API server!               ║")
        print("╠══════════════════════════════════════════════════════════════════╣")
        print("║  Please start the server first:                                   ║")
        print("║                                                                    ║")
        print("║    uvicorn main:app --reload                                       ║")
        print("║                                                                    ║")
        print("║  Then run this script again.                                       ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        print(f"{Colors.ENDC}")
        sys.exit(1)
    
    print(f"{Colors.GREEN}✅ Server is running at {BASE_URL}{Colors.ENDC}\n")
    
    # Session state
    phone_number = random_phone()
    user_data = {"phone_number": phone_number}
    debug_mode = False
    
    print(f"{Colors.CYAN}📱 New session started with phone: {phone_number}{Colors.ENDC}")
    print(f"{Colors.YELLOW}💡 Tip: Send any message to start the onboarding flow!{Colors.ENDC}\n")
    print("-" * 70)
    
    while True:
        try:
            # Get user input
            user_input = input(f"\n{Colors.BOLD}👤 You:{Colors.ENDC} ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower().split()[0]
                
                if cmd == "/quit" or cmd == "/exit":
                    print(f"\n{Colors.CYAN}👋 Goodbye! Thank you for testing Sakhi!{Colors.ENDC}\n")
                    break
                
                elif cmd == "/new":
                    phone_number = random_phone()
                    user_data = {"phone_number": phone_number}
                    print(f"\n{Colors.GREEN}✅ New session started with phone: {phone_number}{Colors.ENDC}")
                    continue
                
                elif cmd == "/phone":
                    parts = user_input.split()
                    if len(parts) > 1:
                        phone_number = parts[1]
                        user_data = {"phone_number": phone_number}
                        print(f"\n{Colors.GREEN}✅ Using phone number: {phone_number}{Colors.ENDC}")
                    else:
                        print(f"\n{Colors.YELLOW}Usage: /phone <phone_number>{Colors.ENDC}")
                    continue
                
                elif cmd == "/user":
                    print_user_info(user_data)
                    continue
                
                elif cmd == "/clear":
                    print_header()
                    print(f"{Colors.CYAN}📱 Current session phone: {phone_number}{Colors.ENDC}\n")
                    continue
                
                elif cmd == "/debug":
                    debug_mode = not debug_mode
                    status = "enabled" if debug_mode else "disabled"
                    print(f"\n{Colors.YELLOW}🔧 Debug mode {status}{Colors.ENDC}")
                    continue
                
                elif cmd == "/help":
                    print_help()
                    continue
                
                else:
                    print(f"\n{Colors.YELLOW}Unknown command: {cmd}. Type /help for available commands.{Colors.ENDC}")
                    continue
            
            # Send message to chatbot
            print(f"\n{Colors.YELLOW}⏳ Sending to Sakhi...{Colors.ENDC}")
            status_code, response_data = send_message(phone_number, user_input)
            
            # Display response
            print(format_response(response_data, debug_mode))
            
            # Update user data from response
            if response_data.get("mode"):
                user_data["last_mode"] = response_data.get("mode")
            if response_data.get("route"):
                user_data["last_route"] = response_data.get("route")
            
            print("\n" + "-" * 70)
            
        except KeyboardInterrupt:
            print(f"\n\n{Colors.CYAN}👋 Goodbye! (Ctrl+C detected){Colors.ENDC}\n")
            break
        except Exception as e:
            print(f"\n{Colors.RED}❌ Unexpected error: {e}{Colors.ENDC}")


if __name__ == "__main__":
    main()
