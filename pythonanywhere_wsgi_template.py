# This file contains the code you need to paste into the WSGI configuration file on PythonAnywhere.
# You can find the WSGI file link in the "Web" tab, usually named /var/www/yourusername_pythonanywhere_com_wsgi.py

import sys
import os

# Add your project directory to the sys.path
# REPLACE 'yourusername' with your actual PythonAnywhere username
project_home = '/home/yourusername/mysite'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Import flask app but need to call it "application" for WSGI to work
from web_admin import app as application
