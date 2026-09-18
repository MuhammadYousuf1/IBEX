"""
WSGI Entry Point
================
Exposes the Flask app as a standard WSGI callable for production servers.

`python app.py` already serves the dashboard with waitress (see `_serve()` in
app.py), so this module is only needed when an external server or a container
platform expects to import a WSGI application.

Examples (Linux / macOS / containers):
    waitress-serve --listen=0.0.0.0:8050 wsgi:application
    gunicorn -w 4 -b 0.0.0.0:8050 wsgi:application
"""

from app import server

application = server
