from flask import Flask, request, render_template_string
import subprocess
import os
import urllib.request
import urllib.error
import ssl
import json
from datetime import datetime, timezone

app = Flask(__name__)

DEBUG_PATH = os.environ.get('DEBUG_PATH')
DEPLOYMENT_NAME = os.environ.get('DEPLOYMENT_NAME', 'phoenix-app')

DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phoenix</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'IBM Plex Sans', -apple-system, sans-serif;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f8f9fa;
            color: #1a1a1a;
        }

        .container {
            text-align: center;
            padding: 3rem 2rem;
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 600;
            letter-spacing: -0.03em;
            color: #111;
            margin-bottom: 1.5rem;
        }

        .status-line {
            font-size: 1.125rem;
            color: #444;
            line-height: 1.6;
        }

        .status-line strong {
            color: #16a34a;
            font-weight: 600;
        }

        .error-text {
            color: #dc2626;
        }

        details {
            margin-top: 2rem;
            text-align: left;
            display: inline-block;
        }

        summary {
            cursor: pointer;
            font-size: 0.875rem;
            color: #666;
            padding: 0.5rem 0;
            user-select: none;
        }

        summary:hover {
            color: #111;
        }

        summary::marker {
            color: #999;
        }

        .details-table {
            margin-top: 1rem;
            font-family: 'IBM Plex Mono', monospace;
            font-size: 0.8125rem;
            border-collapse: collapse;
        }

        .details-table td {
            padding: 0.375rem 0;
        }

        .details-table td:first-child {
            color: #888;
            padding-right: 1.5rem;
            white-space: nowrap;
        }

        .details-table td:last-child {
            color: #222;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Phoenix</h1>
        <div class="status-line">
            Status: <strong>{{ status }}</strong>
            {% if payment_status %}
            <br>Payment API: <strong class="{{ 'error-text' if payment_status.startswith('error') else '' }}">{{ payment_status }}</strong>
            {% endif %}
        </div>

        <details>
            <summary>deployment info</summary>
            <table class="details-table">
                <tr><td>deployment</td><td>{{ deployment_name }}</td></tr>
                <tr><td>timestamp</td><td>{{ timestamp }}</td></tr>
                {% if node_name %}<tr><td>node</td><td>{{ node_name }}</td></tr>{% endif %}
                {% if pod_ip %}<tr><td>pod ip</td><td>{{ pod_ip }}</td></tr>{% endif %}
                {% if namespace %}<tr><td>namespace</td><td>{{ namespace }}</td></tr>{% endif %}
            </table>
        </details>
    </div>
</body>
</html>
'''

RCE_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Debug Console</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: 'IBM Plex Mono', monospace;
            background: #0d1117;
            color: #c9d1d9;
            min-height: 100vh;
            padding: 2rem;
        }

        .terminal {
            max-width: 900px;
            margin: 0 auto;
        }

        .prompt-line {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }

        .prompt {
            color: #3fb950;
            font-weight: 500;
            white-space: nowrap;
        }

        input[name=cmd] {
            flex: 1;
            background: transparent;
            border: none;
            border-bottom: 1px solid #30363d;
            color: #c9d1d9;
            font-family: inherit;
            font-size: 0.9rem;
            padding: 0.25rem 0;
            outline: none;
        }

        input[name=cmd]:focus {
            border-bottom-color: #58a6ff;
        }

        button {
            background: #21262d;
            border: 1px solid #30363d;
            color: #c9d1d9;
            font-family: inherit;
            font-size: 0.85rem;
            padding: 0.25rem 0.75rem;
            cursor: pointer;
            border-radius: 4px;
        }

        button:hover {
            background: #30363d;
        }

        .output-block {
            margin-top: 1.5rem;
            border: 1px solid #21262d;
            border-radius: 4px;
            overflow: hidden;
        }

        .output-header {
            background: #161b22;
            padding: 0.5rem 1rem;
            font-size: 0.75rem;
            color: #8b949e;
            border-bottom: 1px solid #21262d;
        }

        pre {
            padding: 1rem;
            font-size: 0.85rem;
            line-height: 1.5;
            overflow-x: auto;
            white-space: pre-wrap;
            word-break: break-all;
        }

        .success { color: #3fb950; }
        .error   { color: #f85149; }
    </style>
</head>
<body>
    <div class="terminal">
        <form method="POST">
            <div class="prompt-line">
                <span class="prompt">root@{{ hostname }} ~#</span>
                <input type="text" name="cmd" value="{{ cmd or '' }}" autofocus autocomplete="off" spellcheck="false">
                <button type="submit">run</button>
            </div>
        </form>

        {% if cmd %}
        <div class="output-block">
            <div class="output-header">$ {{ cmd }}</div>
            <pre class="{{ 'error' if error else 'success' }}">{{ output }}</pre>
        </div>
        {% endif %}
    </div>
</body>
</html>
'''


def check_payment_api():
    """Try to reach payment-api and return status string."""
    payment_url = os.environ.get('PAYMENT_API_URL', 'http://payment-api:8080/health')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        req = urllib.request.Request(payment_url, headers={'User-Agent': 'phoenix-health'})
        with urllib.request.urlopen(req, timeout=2, context=ctx) as resp:
            data = json.loads(resp.read().decode())
            return data.get('status', 'ok')
    except urllib.error.URLError as e:
        return f'error: {e.reason}'
    except Exception as e:
        return f'error: {type(e).__name__}'


@app.route('/health')
def health():
    return {'status': 'ok', 'service': 'phoenix', 'deployment': DEPLOYMENT_NAME}


@app.route('/')
def index():
    payment_status = check_payment_api()
    return render_template_string(
        DASHBOARD_HTML,
        status='running',
        payment_status=payment_status,
        deployment_name=DEPLOYMENT_NAME,
        timestamp=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        node_name=os.environ.get('NODE_NAME'),
        pod_ip=os.environ.get('POD_IP'),
        namespace=os.environ.get('NAMESPACE'),
    )


# ── INTENTIONALLY VULNERABLE DEBUG ENDPOINT ────────────────────────────────
# This endpoint executes arbitrary shell commands as root.
# It exists to demonstrate VULN-01 (privileged pod + RCE).
# In the training cluster the path is randomised via DEBUG_PATH env var.
# DO NOT deploy this to any real environment.
# ───────────────────────────────────────────────────────────────────────────

if DEBUG_PATH:
    @app.route(f'/{DEBUG_PATH}/', methods=['GET', 'POST'])
    def debug_console():
        cmd = None
        output = ''
        error = False
        hostname = subprocess.check_output(['hostname']).decode().strip()

        if request.method == 'POST':
            cmd = request.form.get('cmd', '').strip()
            if cmd:
                try:
                    result = subprocess.check_output(
                        cmd, shell=True, stderr=subprocess.STDOUT,
                        timeout=10
                    )
                    output = result.decode(errors='replace')
                except subprocess.CalledProcessError as e:
                    output = e.output.decode(errors='replace')
                    error = True
                except subprocess.TimeoutExpired:
                    output = 'command timed out after 10 seconds'
                    error = True

        return render_template_string(
            RCE_HTML,
            cmd=cmd,
            output=output,
            error=error,
            hostname=hostname,
        )


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=False)
