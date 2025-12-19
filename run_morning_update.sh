#!/bin/bash

# Activate virtual environment
source /home/anushka/Cyberagent/myenv/bin/activate

# Navigate to project directory
cd /home/anushka/Cyberagent

# Log file with timestamp
LOG_FILE="/home/anushka/Cyberagent/logs/agentic_news_$(date +'%Y-%m-%d_%H-%M-%S').log"

# Make sure logs directory exists
mkdir -p /home/anushka/Cyberagent/logs

# Run command, show output, and save it to log file
python manage.py agentic_news_update --scrape-first --show-reasoning 2>&1 | tee "$LOG_FILE"

echo "News update completed at $(date)"
echo "Log saved to: $LOG_FILE"

# # Optional email notification with results
# mail -s "Agentic News Update Report $(date)" you@email.com < "$LOG_FILE"