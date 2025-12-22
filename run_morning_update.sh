#!/usr/bin/env python3
"""
Cross-Platform Agentic News Analysis Script
Analyzes last 24 hours and selects top 10 most important news
Compatible with: Linux, macOS, Windows
"""

import os
import sys
import subprocess
import platform
from datetime import datetime
from pathlib import Path

# Detect OS
SYSTEM = platform.system()  # 'Linux', 'Darwin' (macOS), 'Windows'

# Get script directory (works on all platforms)
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_DIR = SCRIPT_DIR

# Virtual environment paths (platform-specific)
if SYSTEM == "Windows":
    VENV_PYTHON = PROJECT_DIR / "myenv" / "Scripts" / "python.exe"
    VENV_ACTIVATE = PROJECT_DIR / "myenv" / "Scripts" / "activate.bat"
else:  # Linux, macOS
    VENV_PYTHON = PROJECT_DIR / "myenv" / "bin" / "python"
    VENV_ACTIVATE = PROJECT_DIR / "myenv" / "bin" / "activate"

# Logs directory
LOGS_DIR = PROJECT_DIR / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Log file with timestamp
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
LOG_FILE = LOGS_DIR / f"agentic_news_{timestamp}.log"


def print_and_log(message, log_file=None):
    """Print to console and write to log file"""
    print(message)
    if log_file:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(message + '\n')


def print_banner(title, log_file=None):
    """Print a formatted banner"""
    separator = "=" * 60
    print_and_log(separator, log_file)
    print_and_log(title, log_file)
    print_and_log(separator, log_file)


def run_command(cmd, log_file=None):
    """Run command and stream output to console and log file"""
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
            cwd=PROJECT_DIR
        )
        
        # Stream output
        for line in iter(process.stdout.readline, ''):
            if line:
                print(line.rstrip())
                if log_file:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(line)
        
        process.wait()
        return process.returncode
        
    except Exception as e:
        error_msg = f"Error running command: {e}"
        print_and_log(error_msg, log_file)
        return 1


def check_venv():
    """Check if virtual environment exists"""
    if not VENV_PYTHON.exists():
        print(f"❌ Virtual environment not found at: {VENV_PYTHON}")
        print(f"Please create it first:")
        print(f"  python -m venv myenv")
        sys.exit(1)


def main():
    """Main execution function"""
    
    # Print startup banner
    print_banner("🤖 COMPREHENSIVE AGENTIC NEWS ANALYSIS", LOG_FILE)
    print_and_log(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", LOG_FILE)
    print_and_log(f"💻 Operating System: {SYSTEM}", LOG_FILE)
    print_and_log(f"📁 Project Directory: {PROJECT_DIR}", LOG_FILE)
    print_and_log(f"🐍 Python: {sys.version.split()[0]}", LOG_FILE)
    print_and_log(f"🎯 Target: Top 10 news from last 24 hours", LOG_FILE)
    print_and_log(f"⏱️  Note: Quality analysis - may take several minutes", LOG_FILE)
    print_and_log("", LOG_FILE)
    
    # Check virtual environment
    check_venv()
    print_and_log(f"✅ Virtual environment found: {VENV_PYTHON}", LOG_FILE)
    print_and_log("", LOG_FILE)
    
    # Build command (platform-independent)
    cmd = [
        str(VENV_PYTHON),
        "manage.py",
        "agentic_news_update",
        "--scrape-first",
        "--show-reasoning",
        "--hours", "24",
        "--top-n", "10",
        "--workers", "4"
    ]
    
    print_and_log("🚀 Starting analysis...", LOG_FILE)
    print_and_log("", LOG_FILE)
    
    # Run the command
    return_code = run_command(cmd, LOG_FILE)
    
    # Completion banner
    print_and_log("", LOG_FILE)
    print_banner("✅ ANALYSIS COMPLETE", LOG_FILE)
    print_and_log(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", LOG_FILE)
    print_and_log(f"📄 Log saved to: {LOG_FILE}", LOG_FILE)
    print_and_log("", LOG_FILE)
    
    # Quick summary
    print_and_log("📊 Quick Summary:", LOG_FILE)
    print_and_log("  - Timeframe: Last 24 hours", LOG_FILE)
    print_and_log("  - Top items selected: 10", LOG_FILE)
    print_and_log("  - Check log for detailed analysis", LOG_FILE)
    print_and_log("", LOG_FILE)
    
    # Cleanup old logs (keep last 30 days)
    cleanup_old_logs()
    
    return return_code


def cleanup_old_logs():
    """Remove log files older than 30 days"""
    try:
        import time
        now = time.time()
        thirty_days_ago = now - (30 * 86400)  # 30 days in seconds
        
        deleted_count = 0
        for log_file in LOGS_DIR.glob("agentic_news_*.log"):
            if log_file.stat().st_mtime < thirty_days_ago:
                log_file.unlink()
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"🗑️  Cleaned up {deleted_count} old log file(s)")
    except Exception as e:
        print(f"⚠️  Warning: Could not clean up old logs: {e}")


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================================================
# USAGE INSTRUCTIONS
# ============================================================================
#
# LINUX / macOS:
#   chmod +x run_agentic_update.py
#   ./run_agentic_update.py
#   
#   Or: python3 run_agentic_update.py
#
# WINDOWS:
#   python run_agentic_update.py
#   
#   Or double-click the file (if .py associated with Python)
#
# SCHEDULE WITH CRON (Linux/macOS):
#   crontab -e
#   Add: 0 9 * * * cd /path/to/project && /usr/bin/python3 run_agentic_update.py
#
# SCHEDULE WITH TASK SCHEDULER (Windows):
#   1. Open Task Scheduler
#   2. Create Basic Task
#   3. Set trigger (e.g., Daily at 9 AM)
#   4. Action: Start a program
#   5. Program: C:\Path\to\python.exe
#   6. Arguments: run_agentic_update.py
#   7. Start in: C:\Path\to\project
#
# OPTIONAL CONFIGURATIONS:
#
# To modify settings, edit the cmd list in main():
#   - Change hours: "--hours", "48"
#   - Change top N: "--top-n", "20"
#   - Change workers: "--workers", "2"
#   - Add details: "--show-details"
#   - Limit items: "--limit", "50"
#
# ============================================================================