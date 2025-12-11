#!/bin/bash

# Activate virtual environment
source /home/anushka/Cyberagent/myenv/bin/activate

# Navigate to project directory
cd /home/anushka/Cyberagent

# Run the management command
python manage.py process_news --workers 1 --batch-size 100 --clean-days 1

# Optional: Send notification (if you have mail configured)
# echo "Morning news update completed at $(date)" | mail -s "News Update Complete" your@email.com