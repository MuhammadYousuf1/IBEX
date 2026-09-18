"""
Sales Dashboard Application
===========================
Main entry point integrating Flask with Dash for multi-page dashboard.

Run with: python app.py
    - Served by waitress (production WSGI server) by default.
    - Set DASH_DEBUG=true to use the Flask development server with auto-reload.
"""

import os
import sys
from flask import Flask, render_template_string, send_from_directory, session, request, redirect
from dotenv import load_dotenv
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
load_dotenv()

# Import shared data module (after Dash creation so the merged page's
# register_page/callbacks are collected by the pages plugin correctly)

# ============================================================================
# FLASK SERVER SETUP
# ============================================================================

server = Flask(__name__, 
               template_folder='templates',
               static_folder='assets')
server.secret_key = os.getenv('FLASK_SECRET_KEY', 'change-me-in-production')
server.config['SESSION_COOKIE_HTTPONLY'] = True
server.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def get_supabase_client():
    """Create and cache a Supabase client for server-side auth checks."""
    from supabase import create_client
    supabase_url = os.getenv('SUPABASE_URL', '').strip()
    api_key = (os.getenv('SUPABASE_KEY') or os.getenv('SUPABASE_SERVICE_ROLE_KEY') or '').strip()
    if not supabase_url or not api_key:
        return None

    try:
        from supabase import ClientOptions
        return create_client(
            supabase_url,
            api_key,
            options=ClientOptions(postgrest_client_timeout=float(os.getenv('SUPABASE_TIMEOUT', '10'))),
        )
    except Exception:
        return create_client(supabase_url, api_key)


def _login_template(error_message='', next_url='/', email_value=''):
    return render_template_string('''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Sales Dashboard Login</title>
      <style>
        :root {
          --bg:#020817;
          --panel:#0f172a;
          --panel-alt:#111827;
          --field:#0b1220;
          --border:#334155;
          --text:#e2e8f0;
          --muted:#94a3b8;
          --primary:#3b82f6;
          --primary-strong:#2563eb;
          --success:#22c55e;
          --danger:#ef4444;
        }
        * { box-sizing: border-box; }
        body {
          margin:0;
          min-height:100vh;
          display:flex;
          align-items:center;
          justify-content:center;
          font-family: "Segoe UI", Arial, sans-serif;
          background: radial-gradient(circle at top, rgba(59,130,246,0.18), transparent 30%), linear-gradient(135deg, #020817, #0f172a 40%, #111827);
          color: var(--text);
        }
        .card {
          width:min(420px, 92vw);
          background: rgba(15, 23, 42, 0.96);
          border:1px solid rgba(148,163,184,0.2);
          border-radius: 22px;
          box-shadow: 0 24px 80px rgba(2, 8, 23, 0.75);
          padding: 32px 28px 26px;
          backdrop-filter: blur(8px);
        }
        .brand {
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding:7px 12px;
          border-radius:999px;
          background: rgba(59, 130, 246, 0.12);
          border:1px solid rgba(59,130,246,0.3);
          color: #bfdbfe;
          font-size: 0.76rem;
          letter-spacing: 0.12em;
          text-transform: uppercase;
          font-weight: 700;
        }
        h1 {
          margin:20px 0 8px;
          font-size: clamp(2rem, 5vw, 2.5rem);
          font-weight: 800;
          letter-spacing: -0.04em;
        }
        .subtitle {
          margin:0 0 22px;
          color: var(--muted);
          font-size: 0.98rem;
          line-height: 1.55;
          text-align: left;
        }
        form { display:flex; flex-direction:column; gap:18px; }
        label {
          display:flex;
          flex-direction:column;
          gap:8px;
          font-size: 0.9rem;
          color: var(--muted);
          font-weight: 600;
        }
        input {
          width:100%;
          border:1px solid var(--border);
          border-radius:12px;
          background: rgba(11,18,32,0.95);
          color: var(--text);
          padding: 13px 14px;
          font-size: 1rem;
          transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        input:focus {
          outline:none;
          border-color: var(--primary);
          box-shadow: 0 0 0 3px rgba(59,130,246,0.16);
        }
        .row {
          display:flex;
          align-items:center;
          justify-content:space-between;
          gap:12px;
          margin-top:-4px;
          font-size: 0.85rem;
          color: var(--muted);
        }
        .remember {
          display:inline-flex;
          align-items:center;
          gap:8px;
        }
        .remember input { width: 15px; height: 15px; accent-color: var(--primary); }
        .link {
          color: #bfdbfe;
          text-decoration:none;
          font-weight:600;
        }
        .link:hover { text-decoration:underline; }
        button {
          margin-top:4px;
          background: linear-gradient(135deg, var(--primary-strong), var(--primary));
          color: white;
          border:none;
          border-radius: 12px;
          padding: 14px 16px;
          font-size: 1rem;
          font-weight: 700;
          cursor: pointer;
          box-shadow: 0 12px 25px rgba(37,99,235,0.35);
          transition: transform 0.15s ease, filter 0.15s ease;
        }
        button:hover { transform: translateY(-1px); filter: brightness(1.04); }
        .error {
          background: rgba(239,68,68,0.1);
          border:1px solid rgba(239,68,68,0.35);
          color: #fecaca;
          border-radius: 12px;
          padding: 10px 12px;
          margin-bottom: 8px;
          font-size: 0.92rem;
        }
        .footer-note {
          margin-top:18px;
          padding-top:16px;
          border-top:1px solid rgba(148,163,184,0.18);
          color: var(--muted);
          font-size: 0.82rem;
          text-align:center;
        }
        @media (max-width: 480px) {
          .card { padding: 26px 20px 22px; }
          .row { flex-direction:column; align-items:flex-start; }
        }
      </style>
    </head>
    <body>
      <div class="card">
        <div class="brand">Sales Dashboard</div>
        <h1>Welcome back</h1>
        <p class="subtitle">Sign in to access your dashboard and store reports.</p>
        {% if error_message %}
        <div class="error">{{ error_message }}</div>
        {% endif %}
        <form method="post" action="/login">
          <input type="hidden" name="next" value="{{ next_url }}" />
          <label>
            Email address
            <input type="email" name="email" value="{{ email_value }}" placeholder="you@example.com" required />
          </label>
          <label>
            Password
            <input type="password" name="password" placeholder="Enter your password" required />
          </label>
          <div class="row">
            <label class="remember"><input type="checkbox" name="remember" /> Stay signed in</label>
            <a class="link" href="#">Forgot password?</a>
          </div>
          <button type="submit">Sign in</button>
        </form>
        <div class="footer-note">Need a new account? Ask your administrator to invite you.</div>
      </div>
    </body>
    </html>
    ''', error_message=error_message, next_url=next_url, email_value=email_value)


@server.before_request
def require_login():
    """Protect dashboard routes until a valid Supabase session exists."""
    path = request.path
    allowed = {'/login', '/logout', '/health'}
    if path.startswith('/_dash') or path.startswith('/assets') or path.startswith('/static'):
        return None
    if path in allowed:
        return None
    if not session.get('authenticated'):
        return redirect(f"/login?next={path}")


@server.route('/')
def index():
    if session.get('authenticated'):
        return redirect('/sales-dashboard')
    return redirect('/login')


@server.route('/login', methods=['GET', 'POST'])
def login_page():
    next_url = request.form.get('next') or request.args.get('next', '/')
    if session.get('authenticated'):
        return redirect(next_url if next_url.startswith('/') else '/')

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip()
        password = request.form.get('password') or ''
        if not email or not password:
            return _login_template('Email and password are required.', next_url, email)

        client = get_supabase_client()
        if client is None:
            return _login_template('Supabase is not configured. Add SUPABASE_URL and SUPABASE_KEY in your .env file.', next_url, email)

        try:
            auth_response = client.auth.sign_in_with_password({
                'email': email,
                'password': password,
            })
            user = getattr(auth_response, 'user', None)
            session['authenticated'] = True
            session['user_email'] = getattr(user, 'email', email)
            return redirect(next_url if next_url.startswith('/') else '/')
        except Exception as exc:
            return _login_template(f'Login failed: {exc}', next_url, email)

    return _login_template(next_url=next_url)


@server.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ============================================================================
# DASH APP SETUP WITH PAGES
# ============================================================================


app = dash.Dash(
    __name__,
    server=server,
    use_pages=True,
    pages_folder='pages',
    external_stylesheets=[
        dbc.themes.DARKLY,
        'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
        '/assets/custom.css'
    ],
    suppress_callback_exceptions=True,
    meta_tags=[{'name': 'viewport', 'content': 'width=device-width, initial-scale=1.0'}]
)

app.title = 'Sales Analytics Dashboard'

# Import shared data module (after Dash creation so the merged page's
# register_page/callbacks are collected by the pages plugin correctly)
from pages import sales_dashboard as sd  # noqa: E402

# ============================================================================
# SHARED NAVIGATION & LAYOUT COMPONENTS
# ============================================================================

def create_navbar():
    """Create the top navigation bar."""
    return dbc.Navbar(
        dbc.Container([
            dbc.NavbarBrand([
                html.I(className='fas fa-chart-line me-2'),
                'SOFT RAPIDO WIRELESS'
            ], href='/', className='navbar-brand-custom'),
            dbc.NavbarToggler(id='navbar-toggler'),
            dbc.Collapse(
                dbc.Nav([
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-home me-1'),
                        'Home'
                    ], href='/', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-chart-pie me-1'),
                        'Sales Dashboard'
                    ], href='/sales-dashboard', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-file-arrow-down me-1'),
                        'Reports'
                    ], href='/reports', active='exact', className='nav-link-custom')),
                    dbc.NavItem(dbc.NavLink([
                        html.I(className='fas fa-money-bill-wave me-1'),
                        'Deposit & Expense'
                    ], href='/deposit-expense', active='exact', className='nav-link-custom')),
                ], className='ms-auto', navbar=True),
                id='navbar-collapse',
                navbar=True,
            ),
        ], fluid=True),
        color='dark',
        dark=True,
        className='navbar-custom mb-4',
        sticky='top'
    )

def create_footer():
    """Create the footer."""
    return html.Footer(
        dbc.Container(
            dbc.Row([
                dbc.Col([
                    html.P([
                        html.I(className='fas fa-copyright me-1'),
                        f' {datetime.now().year} Sales Analytics Dashboard. All rights reserved.'
                    ], className='text-center text-muted mb-0 py-3')
                ])
            ]),
            fluid=True
        ),
        className='footer-custom mt-auto'
    )

# ============================================================================
# MAIN APP LAYOUT
# ============================================================================

app.layout = dbc.Container([
    dcc.Location(id='url', refresh=False),
    create_navbar(),
    html.Div(id='page-content', children=dash.page_container),
    create_footer(),
    dcc.Store(id='filtered-data-store'),
    dcc.Store(id='current-filters-store'),
], fluid=True, className='main-container')

# ============================================================================
# FLASK ROUTES (Non-Dash pages if needed)
# ============================================================================

@server.route('/health')
def health_check():
    return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}

# ============================================================================
# RUN APPLICATION
# ============================================================================

def _serve():
    """Start the HTTP server.

    Production (the default) is served by **waitress**, a pure-Python WSGI
    server that runs on Windows as well as Linux, so Flask's "development
    server" warning no longer applies. Set DASH_DEBUG=true to fall back to the
    Flask development server (with auto-reload) while developing.
    """
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8050'))
    debug = os.getenv('DASH_DEBUG', '').strip().lower() in ('1', 'true', 'yes')
    shown_host = '127.0.0.1' if host in ('0.0.0.0', '::') else host

    # Quiet waitress' per-request logging by default. It still prints the
    # startup banner and any errors; set WAITRESS_LOG_LEVEL=info to see every
    # request again (e.g. when debugging).
    log_level = os.getenv('WAITRES_LOG_LEVEL', '').strip().lower()
    quiet = log_level not in ('info', 'debug')

    _setup_loggers(quiet)

    print("\n" + "=" * 60)
    print("  SALES ANALYTICS DASHBOARD")
    print("=" * 60)
    print("  Open your browser and navigate to:")
    print(f"  http://{shown_host}:{port}/")
    print("=" * 60 + "\n")

    if debug:
        print("  Mode: development (Flask server, auto-reload on)\n")
        app.run(debug=True, use_reloader=True, host=host, port=port)
        return

    try:
        from waitress import serve
    except ImportError:
        print("  Mode: development (Flask server) - waitress is not installed.")
        print("  For production serving install it with:  pip install waitress\n")
        app.run(debug=False, use_reloader=False, host=host, port=port)
        return

    threads = int(os.getenv('WEB_THREADS', '8'))
    mode_line = f"  Mode: production (waitress, {threads} threads)" + (
        "  (per-request logging: on)" if not quiet else "  (per-request logging: off)"
    )
    print(mode_line + "\n")
    serve_kwargs = dict(
        app=app.server,
        host=host,
        port=port,
        threads=threads,
    )
    serve(**serve_kwargs)


def _quiet_logger():
    """A waitress logger stub that swallows access/debug lines but keeps errors."""
    import logging

    class _QuietLogger:
        def output(self, msg):  # noqa: D102
            pass  # drop access lines

        def log(self, level, msg):  # noqa: D102
            if level < logging.WARNING:
                return
            print(msg, flush=True)

        def log_exception(self, msg, *args, **kwargs):  # noqa: D102
            print(msg % args, flush=True)

        def errlog(self, msg, *args, **kwargs):  # noqa: D102
            print("waitress: " + (msg % args), flush=True)

    return _QuietLogger()


def _setup_loggers(quiet):
    """Keep the app/werkzeug noise down when running under waitress."""
    if not quiet:
        return
    import logging
    for name in ('waitress', 'werkzeug', 'flask', 'dash'):
        lg = logging.getLogger(name)
        # Keep real errors/warnings but drop the INFO access noise.
        lg.setLevel(logging.WARNING)
        _remove_handlers(lg)
        if not lg.handlers:
            lg.addHandler(logging.StreamHandler(sys.stderr))


def _remove_handlers(logger):
    """Silently drop any handlers that would otherwise duplicate log lines."""
    for h in list(logger.handlers):
        logger.removeHandler(h)
        try:
            h.close()
        except Exception:
            pass


if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)

    # Copy sample data if not exists (for first run)
    if not os.path.exists('data/SALES UPDATE.xlsx'):
        print("\n⚠️  Please place your 'SALES UPDATE.xlsx' file in the 'data/' folder")
        print("   Expected path: data/SALES UPDATE.xlsx\n")

    # Serve through waitress (production) unless DASH_DEBUG=true was set.
    _serve()
