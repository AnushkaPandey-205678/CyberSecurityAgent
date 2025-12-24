#!/bin/bash

#############################################################################
# Agentic News Analysis Cron Script
# 
# Purpose: Scrape cybersecurity news and run AI analysis to find top 10
#          most important articles from the last 24 hours
#
# Usage: 
#   Manual: ./run_agentic_news.sh
#   Cron:   Add to crontab (see instructions below)
#############################################################################

# Configuration
PROJECT_DIR="/home/anushka/Cyberagent"  # CHANGE THIS to your actual project path
PYTHON_ENV="/home/anushka/Cyberagent/myenv/bin/python"  # CHANGE THIS to your virtual environment
LOG_DIR="${PROJECT_DIR}/logs"
LOG_FILE="${LOG_DIR}/agentic_news_$(date +%Y%m%d).log"
ERROR_LOG="${LOG_DIR}/agentic_news_errors.log"
LOCK_FILE="/tmp/agentic_news.lock"

# Analysis parameters
HOURS=24           # Analyze news from last 24 hours
TOP_N=10          # Get top 10 most important items
MODEL="llama3"    # Ollama model to use
WORKERS=4         # Parallel workers (2-6 recommended)

#############################################################################
# Functions
#############################################################################

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $1" | tee -a "$LOG_FILE" "$ERROR_LOG"
}

cleanup() {
    rm -f "$LOCK_FILE"
}

check_dependencies() {
    if ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        log_error "Ollama is not running. Please start Ollama first."
        return 1
    fi
    
    if [ ! -f "$PYTHON_ENV" ]; then
        log_error "Python environment not found at: $PYTHON_ENV"
        return 1
    fi
    
    if [ ! -f "${PROJECT_DIR}/manage.py" ]; then
        log_error "Django project not found at: $PROJECT_DIR"
        return 1
    fi
    
    return 0
}

#############################################################################
# Main Script
#############################################################################

mkdir -p "$LOG_DIR"

log_message "=========================================="
log_message "Starting Agentic News Analysis"
log_message "=========================================="

if [ -f "$LOCK_FILE" ]; then
    log_error "Another instance is already running (lock file exists)"
    exit 1
fi

touch "$LOCK_FILE"
trap cleanup EXIT

cd "$PROJECT_DIR" || {
    log_error "Failed to change to project directory: $PROJECT_DIR"
    exit 1
}

if ! check_dependencies; then
    log_error "Dependency check failed"
    exit 1
fi

log_message "All dependencies satisfied"
log_message "Running agentic analysis (hours=$HOURS, top_n=$TOP_N, workers=$WORKERS)..."

$PYTHON_ENV manage.py agentic_news_update \
    --hours "$HOURS" \
    --top-n "$TOP_N" \
    --model "$MODEL" \
    --workers "$WORKERS" \
    --show-reasoning \
    2>&1 | tee -a "$LOG_FILE"

if [ ${PIPESTATUS[0]} -eq 0 ]; then
    log_message "✅ Agentic analysis completed successfully"
else
    log_error "❌ Agentic analysis failed with exit code ${PIPESTATUS[0]}"
    exit 1
fi

log_message "=========================================="
log_message "Agentic News Analysis Complete"
log_message "=========================================="

find "$LOG_DIR" -name "agentic_news_*.log" -mtime +30 -delete 2>/dev/null

exit 0

#############################################################################
# CRON SETUP INSTRUCTIONS
#############################################################################
#
# 1. Make this script executable:
#    chmod +x /path/to/run_agentic_news.sh
#
# 2. Edit the script and update these variables:
#    - PROJECT_DIR: Path to your Django project
#    - PYTHON_ENV: Path to your Python virtual environment
#
# 3. Test the script manually first:
#    ./run_agentic_news.sh
#
# 4. Add to crontab (crontab -e):
#
#    # Run every day at 8:00 AM
#    0 8 * * * /path/to/run_agentic_news.sh
#
#    # Run every 6 hours
#    0 */6 * * * /path/to/run_agentic_news.sh
#
#    # Run every day at 6:00 AM and 6:00 PM
#    0 6,18 * * * /path/to/run_agentic_news.sh
#
#    # Run Monday to Friday at 9:00 AM
#    0 9 * * 1-5 /path/to/run_agentic_news.sh
#
# 5. View cron logs:
#    tail -f /path/to/your/project/logs/agentic_news_$(date +%Y%m%d).log
#
# 6. Common cron schedules:
#    - "0 */4 * * *"   : Every 4 hours
#    - "0 0 * * *"     : Daily at midnight
#    - "0 6 * * *"     : Daily at 6 AM
#    - "*/30 * * * *"  : Every 30 minutes
#    - "0 9-17 * * *"  : Every hour from 9 AM to 5 PM
#
#############################################################################








