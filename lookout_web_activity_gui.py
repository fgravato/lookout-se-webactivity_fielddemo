"""Web GUI for Lookout Web Access Feed with basic search capability."""

import os
import concurrent.futures
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import math
import secrets
from urllib.parse import urlencode, urlparse

from flask import Flask, request, render_template_string

from lookout_web_activity_feed import LookoutAPIClient, get_ip_type_and_mode

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(16))

# Instantiate a single API client per process to reuse access tokens.
INIT_ERROR = None
try:
    client = LookoutAPIClient()
except SystemExit as exc:
    INIT_ERROR = "Configuration required. Check that WEB_ACTIVITY_KEY is set in your .env file."
    client = None
except Exception as exc:
    INIT_ERROR = "Configuration required. The API client could not be initialized. Check your .env file and restart the server."
    client = None

TIME_WINDOW_OPTIONS = {
    '1h': ('Last 1 hour', timedelta(hours=1)),
    '12h': ('Last 12 hours', timedelta(hours=12)),
    '24h': ('Last 24 hours', timedelta(hours=24)),
    '48h': ('Last 48 hours', timedelta(hours=48)),
    'custom': ('Custom start time', None),
}

# Module-level DNS cache — persists for the lifetime of the Flask process.
_dns_cache: Dict[str, str] = {}

import requests as _requests  # noqa: E402 — already a project dep


def _extract_hostname(url: str) -> str:
    try:
        parsed = urlparse(url if '://' in url else 'https://' + url)
        return (parsed.hostname or '').lower()
    except Exception:
        return ''


def _doh_lookup(hostname: str, server: str) -> str:
    """Single DNS-over-HTTPS query. server must be 'cloudflare' or 'google'."""
    try:
        endpoint = 'https://1.1.1.1/dns-query' if server == 'cloudflare' else 'https://dns.google/resolve'
        r = _requests.get(
            endpoint,
            params={'name': hostname, 'type': 'A'},
            headers={'accept': 'application/dns-json'},
            timeout=3,
        )
        data = r.json()
        answers = [a['data'] for a in data.get('Answer', []) if a.get('type') == 1]
        return answers[0] if answers else ''
    except Exception:
        return ''


def _batch_resolve(raw_events: List[Dict[str, Any]]) -> Dict[str, str]:
    """Race 1.1.1.1 vs 8.8.8.8 for every unique uncached hostname in parallel.
    Returns {hostname: ip} for all hostnames found in the event list."""
    all_hostnames = [_extract_hostname(e.get('request_url', '')) for e in raw_events]
    uncached = list({h for h in all_hostnames if h and h not in _dns_cache})

    if uncached:
        workers = min(len(uncached) * 2, 40)
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures: Dict[concurrent.futures.Future, str] = {}
            for h in uncached:
                futures[pool.submit(_doh_lookup, h, 'cloudflare')] = h
                futures[pool.submit(_doh_lookup, h, 'google')] = h

            resolved: Dict[str, str] = {}
            for fut in concurrent.futures.as_completed(futures):
                h = futures[fut]
                if h in resolved:
                    continue
                try:
                    ip = fut.result()
                    if ip:
                        resolved[h] = ip
                except Exception:
                    pass

        for h in uncached:
            _dns_cache[h] = resolved.get(h, '')

    return {h: _dns_cache.get(h, '') for h in set(all_hostnames) if h}

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Lookout Web Activity — Activity Browser</title>
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg: #0e1c1f;
            --surface: #122629;
            --surface-2: #0b2f2f;
            --surface-3: #0f2023;
            --text: #e6f2f2;
            --muted: #9fb9b8;
            --muted-2: #6f8f8e;
            --border: rgba(255,255,255,.08);
            --border-strong: rgba(255,255,255,.14);

            --accent: #9AF24F;
            --accent-contrast: #0f1a11;
            --accent-soft: rgba(154,242,79,.12);

            --accent-2: #FF8266;
            --accent-2-contrast: #2a110e;

            --focus: #7ae6ff;
            --danger: #ff6363;

            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-sm: 8px;
            --shadow-1: 0 10px 28px rgba(0,0,0,.35);

            --font-ui: "Inter", ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "Helvetica Neue", Arial;
            --font-display: "Space Grotesk", var(--font-ui);
            --font-mono: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;

            --fs-body: 15px;
            --container: 1280px;
        }

        * { box-sizing: border-box; }
        html, body { height: 100%; }
        body.theme-lookout {
            margin: 0;
            background:
                radial-gradient(1200px 600px at 80% -10%, rgba(154,242,79,.05), transparent 60%),
                radial-gradient(900px 500px at -10% 10%, rgba(122,230,255,.04), transparent 60%),
                var(--bg);
            color: var(--text);
            font-family: var(--font-ui);
            font-size: var(--fs-body);
            line-height: 1.55;
            -webkit-font-smoothing: antialiased;
            text-rendering: optimizeLegibility;
        }

        a { color: inherit; text-decoration: none; }
        a:hover { text-decoration: underline; }

        .app {
            max-width: var(--container);
            margin: 28px auto 56px;
            padding: 0 24px;
        }

        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            box-shadow: var(--shadow-1);
        }

        /* ---------- Banner ---------- */
        .banner {
            padding: 22px 26px;
            margin-bottom: 18px;
            background: linear-gradient(180deg, #102426 0%, #0d1d1f 100%);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 24px;
            flex-wrap: wrap;
        }

        .banner-text { min-width: 280px; }

        .banner-title-row {
            display: flex;
            align-items: center;
            gap: 14px;
            flex-wrap: wrap;
        }

        .banner h1 {
            font-family: var(--font-display);
            font-size: clamp(26px, 3.2vw, 36px);
            line-height: 1.05;
            margin: 0;
            letter-spacing: -0.01em;
        }

        .banner p {
            margin: 6px 0 0;
            color: var(--muted);
            font-size: 14px;
        }

        .live-badge {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-family: var(--font-ui);
            font-size: 11px;
            font-weight: 700;
            letter-spacing: .12em;
            text-transform: uppercase;
            color: #d3ff9f;
            background: var(--accent-soft);
            border: 1px solid rgba(154,242,79,.35);
            padding: 4px 10px;
            border-radius: 999px;
        }

        .live-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 0 0 rgba(154,242,79,.7);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0%   { box-shadow: 0 0 0 0 rgba(154,242,79,.6); }
            70%  { box-shadow: 0 0 0 8px rgba(154,242,79,0); }
            100% { box-shadow: 0 0 0 0 rgba(154,242,79,0); }
        }

        .brand-mark {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: var(--font-display);
            font-weight: 700;
            color: var(--muted);
            font-size: 13px;
            letter-spacing: .14em;
            text-transform: uppercase;
        }

        .brand-mark .dot {
            width: 10px; height: 10px;
            border-radius: 50%;
            background: var(--accent);
            box-shadow: 0 0 14px rgba(154,242,79,.5);
        }

        /* ---------- Toolbar ---------- */
        form { margin: 0; }

        .toolbar-card {
            padding: 12px 14px;
            margin-bottom: 18px;
        }

        .toolbar {
            display: flex;
            align-items: center;
            gap: 10px;
            flex-wrap: wrap;
        }

        .pill-group {
            display: inline-flex;
            background: var(--surface-3);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 3px;
            gap: 2px;
        }

        .pill {
            appearance: none;
            border: 0;
            background: transparent;
            color: var(--muted);
            font: 600 13px var(--font-ui);
            padding: 7px 14px;
            border-radius: 999px;
            cursor: pointer;
            transition: color .15s ease, background .15s ease;
            letter-spacing: .02em;
        }

        .pill:hover { color: var(--text); }

        .pill.is-active {
            background: var(--accent);
            color: var(--accent-contrast);
        }

        .toolbar-divider {
            width: 1px;
            height: 24px;
            background: var(--border);
            margin: 0 4px;
        }

        .toolbar-field {
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .toolbar-label {
            font-size: 11px;
            letter-spacing: .12em;
            color: var(--muted);
            text-transform: uppercase;
            font-weight: 600;
        }

        .toolbar input[type="number"] {
            width: 78px;
        }

        .toolbar input[type="text"],
        .toolbar input[type="search"],
        .toolbar input[type="datetime-local"],
        .toolbar input[type="number"] {
            background: var(--surface-3);
            color: var(--text);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 8px 14px;
            outline: none;
            font-family: var(--font-ui);
            font-size: 13px;
            line-height: 1.2;
        }

        .toolbar input[type="datetime-local"] {
            font-family: var(--font-mono);
            font-size: 12px;
            color-scheme: dark;
        }

        .toolbar input[type="search"] {
            flex: 1 1 220px;
            min-width: 200px;
        }

        .toolbar input::placeholder { color: rgba(255,255,255,0.4); }

        .toolbar input:focus {
            border-color: var(--focus);
            box-shadow: 0 0 0 3px rgba(122,230,255,0.18);
        }

        .custom-toggle {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            background: transparent;
            color: var(--muted);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 7px 12px;
            cursor: pointer;
            font: 600 12px var(--font-ui);
            letter-spacing: .04em;
        }
        .custom-toggle:hover { color: var(--text); border-color: var(--border-strong); }
        .custom-toggle.is-open {
            color: var(--accent);
            border-color: rgba(154,242,79,.35);
            background: var(--accent-soft);
        }

        .custom-wrap {
            display: none;
            align-items: center;
            gap: 8px;
        }
        .custom-wrap.is-open { display: inline-flex; }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            border-radius: 999px;
            padding: 9px 18px;
            font-weight: 700;
            border: 1px solid transparent;
            transition: transform 0.15s ease, filter 0.15s ease;
            font-family: var(--font-ui);
            font-size: 13px;
            letter-spacing: .02em;
        }
        .btn:hover { transform: translateY(-1px); }
        .btn:focus-visible {
            outline: 2px solid var(--focus);
            outline-offset: 3px;
        }
        .btn-accent {
            background: var(--accent);
            color: var(--accent-contrast);
            margin-left: auto;
        }
        .btn-accent:hover { filter: brightness(0.96); }
        .btn:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
            filter: none;
        }

        /* ---------- Stats ---------- */
        .stats {
            display: flex;
            gap: 12px;
            margin-bottom: 18px;
        }

        .stat {
            flex: 1 1 0;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-md);
            padding: 16px 18px;
            display: flex;
            flex-direction: column;
            gap: 6px;
            min-width: 0;
        }

        .stat-value {
            font-family: var(--font-display);
            font-size: 32px;
            font-weight: 700;
            line-height: 1;
            color: var(--accent);
            letter-spacing: -0.01em;
            font-variant-numeric: tabular-nums;
        }

        .stat-value.is-text {
            font-size: 20px;
            color: var(--text);
        }

        .stat-label {
            font-size: 11px;
            color: var(--muted);
            letter-spacing: .14em;
            text-transform: uppercase;
            font-weight: 600;
        }

        /* ---------- Alert ---------- */
        .alert {
            margin-bottom: 18px;
            padding: 16px 22px;
            background: rgba(255,99,99,0.12);
            border: 1px solid rgba(255,99,99,0.4);
            border-radius: var(--radius-md);
            color: #ffd5d5;
        }

        /* ---------- Table ---------- */
        .table-card { padding: 18px 22px; }

        .table-header {
            display: flex;
            flex-wrap: wrap;
            justify-content: space-between;
            align-items: center;
            gap: 16px;
            margin-bottom: 8px;
        }

        .table-title {
            font-family: var(--font-display);
            font-size: 14px;
            font-weight: 600;
            color: var(--muted);
            letter-spacing: .12em;
            text-transform: uppercase;
        }

        .table-wrap {
            margin-top: 8px;
            overflow-x: auto;
            border-radius: var(--radius-md);
            border: 1px solid var(--border);
        }

        table {
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            min-width: 980px;
        }

        thead th {
            position: sticky;
            top: 0;
            z-index: 1;
            text-align: left;
            font-size: 11px;
            color: var(--muted);
            background: var(--surface-3);
            border-bottom: 1px solid var(--border);
            text-transform: uppercase;
            letter-spacing: .12em;
            padding: 11px 14px;
            font-weight: 600;
            white-space: nowrap;
        }

        tbody td {
            padding: 12px 14px;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
        }

        tbody tr:last-child td { border-bottom: 0; }

        tbody tr { transition: background .12s ease; }
        tbody tr:hover { background: rgba(154, 242, 79, 0.04); }

        .col-ts     { width: 170px; }
        .col-url    { width: auto; }
        .col-dns    { width: 130px; }
        .col-region { width: 110px; }
        .col-device { width: 150px; }
        .col-ip     { width: 150px; }

        .mono { font-family: var(--font-mono); }

        .cell-ts {
            font-family: var(--font-mono);
            font-size: 12px;
            color: var(--muted);
            white-space: nowrap;
        }

        .ts-utc { color: var(--muted); }
        .ts-label {
            font-size: 10px;
            letter-spacing: .08em;
            text-transform: uppercase;
            color: var(--muted-2);
            margin-left: 3px;
        }
        .ts-local {
            font-size: 11px;
            color: var(--muted-2);
            margin-top: 2px;
        }

        .doh-tag {
            display: inline-block;
            font-size: 9px;
            font-weight: 700;
            letter-spacing: .08em;
            color: var(--focus);
            border: 1px solid rgba(122,230,255,.3);
            border-radius: 4px;
            padding: 1px 5px;
            vertical-align: middle;
            margin-left: 5px;
        }

        .cell-url {
            font-size: 13px;
            color: var(--text);
            max-width: 0;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .cell-ip {
            font-family: var(--font-mono);
            font-size: 12.5px;
            color: var(--text);
        }

        .small { font-size: 12px; color: var(--muted); }

        .chip {
            display: inline-block;
            padding: 3px 9px;
            border-radius: 999px;
            background: var(--surface-2);
            border: 1px solid var(--border);
            color: var(--text);
            font-family: var(--font-mono);
            font-size: 11.5px;
            font-weight: 600;
            letter-spacing: .02em;
        }

        .badge {
            display: inline-block;
            padding: 5px 12px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
            border: 1px solid var(--border);
            background: var(--surface-2);
            color: var(--text);
            letter-spacing: .02em;
        }
        .badge.ok {
            background: rgba(154,242,79,.12);
            border-color: rgba(154,242,79,.35);
            color: #d3ff9f;
        }
        .badge.warn {
            background: rgba(255,130,102,.12);
            border-color: rgba(255,130,102,.35);
            color: #ffc4b6;
        }

        /* ---------- Pager ---------- */
        .pager {
            display: flex;
            gap: 12px;
            align-items: center;
            color: var(--muted);
            font-size: 13px;
        }

        .pager a {
            color: var(--text);
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            text-decoration: none;
            font-size: 12px;
            font-weight: 600;
        }
        .pager a:hover { background: var(--surface-3); }

        .pager-bottom {
            margin-top: 14px;
            justify-content: space-between;
            flex-wrap: wrap;
        }

        /* ---------- Empty ---------- */
        .empty-card {
            padding: 56px 28px;
            color: var(--muted);
            text-align: center;
        }
        .empty-card .empty-title {
            font-family: var(--font-display);
            font-size: 18px;
            color: var(--text);
            margin-bottom: 6px;
        }
        .empty-card .empty-sub {
            font-size: 14px;
            color: var(--muted);
            max-width: 480px;
            margin: 0 auto;
        }

        @media (max-width: 820px) {
            .toolbar { gap: 8px; }
            .toolbar input[type="search"] { flex-basis: 100%; order: 10; }
            .btn-accent { order: 11; margin-left: 0; }
            .stats { flex-wrap: wrap; }
            .stat { flex-basis: calc(50% - 6px); }
            table { min-width: 820px; }
        }

        @media (max-width: 520px) {
            .stat { flex-basis: 100%; }
            .banner { padding: 18px; }
            .table-card { padding: 14px; }
        }
    </style>
</head>
<body class="theme-lookout">
    <div class="app">
        <div class="banner card">
            <div class="banner-text">
                <div class="banner-title-row">
                    <h1>Lookout Web Activity</h1>
                    {% if fetched and not error %}
                    <span class="live-badge"><span class="live-dot"></span> LIVE</span>
                    {% endif %}
                </div>
                <p>Real-time visibility into mobile web access events across your fleet</p>
            </div>
            <div class="brand-mark"><span class="dot"></span> Lookout</div>
        </div>

        <div class="card toolbar-card">
            <form method="get" action="/">
                <div class="toolbar">
                    <div class="pill-group" role="group" aria-label="Time window">
                        {% for key, (label, delta) in time_windows.items() %}
                            {% if key != 'custom' %}
                            <button type="submit"
                                    class="pill {% if key == selected_time_window %}is-active{% endif %}"
                                    name="time_window"
                                    value="{{ key }}"
                                    title="{{ label }}">{{ key }}</button>
                            {% endif %}
                        {% endfor %}
                    </div>

                    <button type="button" id="customToggle"
                            class="custom-toggle {% if selected_time_window == 'custom' %}is-open{% endif %}"
                            aria-expanded="{% if selected_time_window == 'custom' %}true{% else %}false{% endif %}">
                        Custom
                    </button>

                    <div id="customWrap" class="custom-wrap {% if selected_time_window == 'custom' %}is-open{% endif %}">
                        <input type="datetime-local" name="custom_start" id="custom_start"
                               value="{{ custom_start_display }}" step="1"
                               aria-label="Custom start (UTC)">
                    </div>

                    <div class="toolbar-divider" aria-hidden="true"></div>

                    <div class="toolbar-field">
                        <label class="toolbar-label" for="limit">Limit</label>
                        <input type="number" name="limit" id="limit" min="1" max="500" value="{{ limit }}">
                    </div>

                    <input type="search" name="search" id="search" value="{{ search }}"
                           placeholder="Search URL, region, IP, device…" aria-label="Search">

                    <input type="hidden" name="time_window" id="time_window_hidden" value="{{ selected_time_window }}">

                    <button type="submit" class="btn btn-accent" id="fetchBtn">Fetch activity</button>
                </div>
            </form>
        </div>

        {% if error %}
        <div class="alert">
            {{ error }}
        </div>
        {% endif %}

        {% if fetched and not error and events %}
        <div class="stats">
            <div class="stat">
                <div class="stat-value">{{ total_count }}</div>
                <div class="stat-label">Total Events</div>
            </div>
            <div class="stat">
                <div class="stat-value">{{ filtered_count }}</div>
                <div class="stat-label">Filtered</div>
            </div>
            <div class="stat">
                <div class="stat-value is-text">
                    {% if selected_time_window in time_windows %}
                        {{ time_windows[selected_time_window][0] }}
                    {% else %}
                        {{ selected_time_window }}
                    {% endif %}
                </div>
                <div class="stat-label">Time Window</div>
            </div>
        </div>
        {% endif %}

        {% if events %}
        <div class="card table-card">
            <div class="table-header">
                <div class="table-title">Activity Stream</div>
                {% if total_pages > 1 %}
                <div class="pager">
                    {% if has_prev %}
                    <a href="{{ prev_url }}">&larr; Previous</a>
                    {% endif %}
                    <span>Page {{ page }} of {{ total_pages }}</span>
                    {% if has_next %}
                    <a href="{{ next_url }}">Next &rarr;</a>
                    {% endif %}
                </div>
                {% endif %}
            </div>

            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th class="col-ts">Timestamp (UTC)</th>
                            <th class="col-url">Request URL</th>
                            <th class="col-dns">DNS Mode</th>
                            <th class="col-region">Region</th>
                            <th class="col-device">Device</th>
                            <th class="col-ip">Resolved IP</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for event in events %}
                        <tr>
                            <td class="cell-ts" data-utc="{{ event.timestamp_iso }}">
                                <div class="ts-utc">{{ event.timestamp }} <span class="ts-label">UTC</span></div>
                                <div class="ts-local"></div>
                            </td>
                            <td class="cell-url" title="{{ event.request_url }}">{{ event.request_url }}</td>
                            <td><span class="badge {{ event.dns_badge_class }}">{{ event.dns_mode }}</span></td>
                            <td><span class="chip">{{ event.region }}</span></td>
                            <td><span class="chip">{{ event.device_guid_display }}</span></td>
                            <td class="cell-ip">{{ event.resolved_ip_main }}{% if event.doh_resolved %}<span class="doh-tag">DoH</span>{% endif %}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>

            {% if total_pages > 1 %}
            <div class="pager pager-bottom">
                <div>
                    {% if has_prev %}
                    <a href="{{ prev_url }}">&larr; Previous</a>
                    {% endif %}
                </div>
                <span>Page {{ page }} of {{ total_pages }}</span>
                <div>
                    {% if has_next %}
                    <a href="{{ next_url }}">Next &rarr;</a>
                    {% endif %}
                </div>
            </div>
            {% endif %}
        </div>
        {% elif fetched and not error %}
        <div class="card empty-card">
            <div class="empty-title">No events matched</div>
            <div class="empty-sub">Try a wider time range or clear the search filter.</div>
        </div>
        {% elif not fetched %}
        <div class="card empty-card">
            <div class="empty-title">Ready when you are</div>
            <div class="empty-sub">Select a time range and click <strong>Fetch activity</strong> to load events.</div>
        </div>
        {% endif %}
    </div>
    <script>
        (function () {
            var form   = document.querySelector('form');
            var btn    = document.getElementById('fetchBtn');
            var toggle = document.getElementById('customToggle');
            var wrap   = document.getElementById('customWrap');
            var hidden = document.getElementById('time_window_hidden');

            if (form && btn) {
                form.addEventListener('submit', function () {
                    btn.disabled = true;
                    btn.textContent = 'Loading…';
                });
            }

            if (toggle && wrap) {
                toggle.addEventListener('click', function () {
                    var open = wrap.classList.toggle('is-open');
                    toggle.classList.toggle('is-open', open);
                    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
                    if (open && hidden) { hidden.value = 'custom'; }
                });
            }

            document.querySelectorAll('.pill[name="time_window"]').forEach(function (p) {
                p.addEventListener('click', function () {
                    if (hidden) { hidden.value = p.value; }
                });
            });

            document.querySelectorAll('[data-utc]').forEach(function (el) {
                var iso = el.getAttribute('data-utc');
                if (!iso) return;
                var d = new Date(iso);
                if (isNaN(d.getTime())) return;
                var local = d.toLocaleString(undefined, {
                    year: 'numeric', month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', second: '2-digit',
                    hour12: false
                });
                var span = el.querySelector('.ts-local');
                if (span) span.textContent = local;
            });
        }());
    </script>
</body>
</html>"""


def _normalize_custom_start(custom_start: str) -> str:
    """Convert form input into the API's expected ISO-8601 string."""
    if not custom_start:
        return None

    raw = custom_start.strip()
    if not raw:
        return None

    transformed = raw.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(transformed)
    except ValueError:
        return raw

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S+00:00')


def _format_custom_start_for_input(custom_start: str) -> str:
    """Return a datetime-local friendly value for the form field."""
    if not custom_start:
        return ''

    raw = custom_start.strip()
    if not raw:
        return ''

    transformed = raw.replace('Z', '+00:00')
    try:
        parsed = datetime.fromisoformat(transformed)
    except ValueError:
        return ''

    if parsed.tzinfo is None:
        return parsed.strftime('%Y-%m-%dT%H:%M:%S')

    return parsed.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


def _build_start_time(time_window: str, custom_start: str) -> str:
    """Translate UI input into a start_time string for the API."""
    if time_window in TIME_WINDOW_OPTIONS and TIME_WINDOW_OPTIONS[time_window][1] is not None:
        delta = TIME_WINDOW_OPTIONS[time_window][1]
        start_time = datetime.now(timezone.utc) - delta
        return start_time.strftime('%Y-%m-%dT%H:%M:%S+00:00')

    if time_window == 'custom' and custom_start:
        normalized = _normalize_custom_start(custom_start)
        return normalized

    return None


def _format_event(event: Dict[str, Any], resolved_ips: Dict[str, str] = None) -> Dict[str, Any]:
    """Convert raw API event into display-friendly structure."""
    timestamp_ms = event.get('timestamp')
    resolved_ip = event.get('resolved_ip_address', '')
    dns_mode, ip_type = get_ip_type_and_mode(resolved_ip)

    readable_time = 'Unknown'
    timestamp_iso = ''
    if timestamp_ms:
        try:
            dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
            readable_time = dt.strftime('%Y-%m-%d %H:%M:%S')
            timestamp_iso = dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        except Exception:
            readable_time = str(timestamp_ms)

    # IP: prefer API value; fall back to DoH-resolved IP.
    doh_resolved = False
    if resolved_ip:
        ip_main = resolved_ip
        ip_meta = ip_type or ''
    else:
        hostname = _extract_hostname(event.get('request_url', ''))
        doh_ip = (resolved_ips or {}).get(hostname, '') if hostname else ''
        if doh_ip:
            ip_main = doh_ip
            ip_meta = 'DoH'
            doh_resolved = True
        else:
            ip_main = 'N/A'
            ip_meta = ''

    device_guid = event.get('device_guid', 'Unknown') or 'Unknown'
    if len(device_guid) > 12:
        device_display = f"{device_guid[:6]}…{device_guid[-4:]}"
    else:
        device_display = device_guid

    event_id_full = event.get('id', 'Unknown') or 'Unknown'
    if len(event_id_full) > 14:
        event_id_display = f"{event_id_full[:6]}…{event_id_full[-4:]}"
    else:
        event_id_display = event_id_full

    badge_class = 'ok' if dns_mode == 'SecureDNS' else 'warn'

    return {
        'timestamp': readable_time,
        'timestamp_iso': timestamp_iso,
        'device_guid_full': device_guid,
        'device_guid_display': device_display,
        'region': event.get('region', 'Unknown'),
        'request_url': event.get('request_url', 'Unknown'),
        'dns_mode': dns_mode,
        'dns_badge_class': badge_class,
        'resolved_ip_main': ip_main,
        'resolved_ip_meta': ip_meta,
        'doh_resolved': doh_resolved,
        'event_id_full': event_id_full,
        'event_id_display': event_id_display,
        'event_id': event_id_full,
    }


def _filter_events(events: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Filter events client-side with a simple substring search."""
    if not query:
        return events

    lowered = query.lower()
    filtered = []
    for event in events:
        searchable_values = [
            event.get('request_url', ''),
            event.get('device_guid', ''),
            event.get('region', ''),
            event.get('resolved_ip_address', ''),
            event.get('id', ''),
        ]

        if any(lowered in str(value).lower() for value in searchable_values if value):
            filtered.append(event)

    return filtered


@app.route('/', methods=['GET'])
def index():
    time_window = request.args.get('time_window', '1h')
    custom_start = request.args.get('custom_start', '')
    search_query = request.args.get('search', '').strip()
    limit_param = request.args.get('limit', '').strip()
    page_param = request.args.get('page', '1').strip()

    custom_start_display = _format_custom_start_for_input(custom_start)
    if custom_start and time_window != 'custom':
        time_window = 'custom'

    try:
        limit = int(limit_param) if limit_param else 50
    except ValueError:
        limit = 50
    limit = max(1, min(limit, 500))

    try:
        page = int(page_param) if page_param else 1
    except ValueError:
        page = 1
    page = max(page, 1)

    events = []
    filtered_count = 0
    total_count = 0
    total_pages = 1
    error = INIT_ERROR
    fetched = bool(request.args)

    # Only call the API if the user submitted parameters and the client is ready.
    if request.args and not error:
        try:
            start_time = _build_start_time(time_window, custom_start_display or custom_start)
            raw_response = client.fetch_events(start_time=start_time)
            raw_events = raw_response.get('lookup_access_events', [])
            total_count = len(raw_events)

            filtered_raw = _filter_events(raw_events, search_query)
            filtered_count = len(filtered_raw)

            if filtered_count > 0:
                total_pages = max(1, math.ceil(filtered_count / limit))
                page = min(page, total_pages)
                start_idx = (page - 1) * limit
                end_idx = start_idx + limit
                sliced_events = filtered_raw[start_idx:end_idx]
                resolved_ips = _batch_resolve(sliced_events)
                events = [_format_event(evt, resolved_ips) for evt in sliced_events]
            else:
                page = 1
                total_pages = 1
        except SystemExit as exc:
            raw = str(exc)
            if '401' in raw or 'Unauthorized' in raw:
                error = "Authentication failed. Your credentials may have expired."
            elif '403' in raw or 'Forbidden' in raw:
                error = "Access denied. Check that your account has Web Activity feed permission."
            elif 'timed out' in raw.lower() or 'timeout' in raw.lower():
                error = "Request timed out. Try a shorter time range or check your network connection."
            else:
                error = "Unable to fetch data. Please try again."
        except Exception as exc:
            raw = str(exc)
            if '401' in raw or 'Unauthorized' in raw:
                error = "Authentication failed. Your credentials may have expired."
            elif '403' in raw or 'Forbidden' in raw:
                error = "Access denied. Check that your account has Web Activity feed permission."
            elif 'timed out' in raw.lower() or 'timeout' in raw.lower():
                error = "Request timed out. Try a shorter time range or check your network connection."
            else:
                error = "Unable to fetch data. Please try again."

    base_params = request.args.to_dict(flat=True)
    base_params['time_window'] = time_window
    base_params['limit'] = str(limit)
    if custom_start_display:
        base_params['custom_start'] = custom_start_display
    elif custom_start:
        base_params['custom_start'] = custom_start
    else:
        base_params.pop('custom_start', None)
    if search_query:
        base_params['search'] = search_query
    else:
        base_params.pop('search', None)
    base_params.pop('page', None)

    def build_page_url(target_page: int) -> str:
        params = base_params.copy()
        if target_page <= 1:
            params.pop('page', None)
        else:
            params['page'] = str(target_page)
        if not params:
            return '/'
        return f"?{urlencode(params)}"

    has_prev = page > 1 and fetched and not error
    has_next = page < total_pages and fetched and not error
    prev_url = build_page_url(page - 1) if has_prev else None
    next_url = build_page_url(page + 1) if has_next else None

    return render_template_string(
        HTML_TEMPLATE,
        time_windows=TIME_WINDOW_OPTIONS,
        selected_time_window=time_window,
        custom_start_display=custom_start_display,
        limit=limit,
        search=search_query,
        events=events,
        filtered_count=filtered_count,
        total_count=total_count,
        error=error,
        fetched=fetched,
        page=page,
        total_pages=total_pages,
        has_prev=has_prev,
        has_next=has_next,
        prev_url=prev_url,
        next_url=next_url,
    )


def create_app():
    """Factory for gunicorn/uwsgi compatibility."""
    return app


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
