#!/bin/bash

# Start the Telegram Bot in the background
python main_pro.py &

# Start the Web Admin interface using Gunicorn
# -w 1: 1 worker process (sufficient for admin interface)
# -b 0.0.0.0:8080: Bind to all interfaces on port 8080
exec gunicorn -w 1 -b 0.0.0.0:8080 web_admin:app
