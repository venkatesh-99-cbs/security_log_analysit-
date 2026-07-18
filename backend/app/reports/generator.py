import os
from datetime import datetime
from typing import Any, List
from jinja2 import Environment, FileSystemLoader, select_autoescape
from ..core.settings import settings

class ReportGenerator:
    """
    Generates professional, security-focused, HTML-based incident and executive reports.
    Uses Jinja2 with strict autoescaping enabled to prevent stored XSS attacks.
    """

    def __init__(self, report_dir: str = settings.REPORT_DIR):
        self.report_dir = report_dir
        os.makedirs(self.report_dir, exist_ok=True)
        # Use an in-memory or embedded Jinja environment with autoescape enabled.
        self.env = Environment(
            autoescape=select_autoescape(["html", "xml", "xhtml"])
        )

    def generate_incident_report(self, incidents: List[Any], title: str = "Security Incident Report") -> str:
        """
        Compiles, formats, and saves an HTML report of the provided incidents.
        Returns the absolute filepath of the generated report.
        """
        template_str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        :root {
            --primary: #0f172a;
            --primary-light: #1e293b;
            --accent: #ef4444;
            --accent-bg: #fef2f2;
            --accent-border: #fca5a5;
            --text-dark: #0f172a;
            --text-light: #64748b;
            --bg-muted: #f8fafc;
            --border: #e2e8f0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: var(--text-dark);
            line-height: 1.5;
            margin: 0;
            padding: 0;
            background-color: #ffffff;
        }
        .container {
            max-width: 1100px;
            margin: 0 auto;
            padding: 40px 20px;
        }
        .header {
            border-bottom: 2px solid var(--primary);
            padding-bottom: 20px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
        }
        .header-title h1 {
            font-size: 28px;
            margin: 0 0 8px 0;
            color: var(--primary);
        }
        .header-title p {
            margin: 0;
            color: var(--text-light);
            font-size: 14px;
        }
        .meta-box {
            text-align: right;
            font-size: 13px;
            color: var(--text-light);
        }
        .summary-cards {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .card {
            background-color: var(--bg-muted);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 15px 20px;
            text-align: center;
        }
        .card .value {
            font-size: 24px;
            font-weight: bold;
            color: var(--primary);
            margin-bottom: 5px;
        }
        .card .label {
            font-size: 12px;
            color: var(--text-light);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .incident-section {
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 30px;
            margin-bottom: 40px;
            background-color: #ffffff;
        }
        .incident-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid var(--border);
            padding-bottom: 15px;
            margin-bottom: 20px;
        }
        .incident-title {
            font-size: 20px;
            font-weight: bold;
            margin: 0 0 5px 0;
            color: var(--primary-light);
        }
        .incident-meta {
            font-size: 13px;
            color: var(--text-light);
        }
        .badge {
            display: inline-block;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 12px;
            text-transform: uppercase;
        }
        .badge-critical { background-color: #fecaca; color: #991b1b; }
        .badge-high { background-color: #fed7aa; color: #c2410c; }
        .badge-medium { background-color: #fef08a; color: #854d0e; }
        .badge-low { background-color: #dcfce7; color: #166534; }
        .badge-info { background-color: #e0f2fe; color: #075985; }
        .badge-open { background-color: #fee2e2; color: #991b1b; }
        .badge-in-progress { background-color: #ffedd5; color: #9a3412; }
        .badge-resolved { background-color: #dcfce7; color: #166534; }
        .badge-closed { background-color: #f1f5f9; color: #475569; }

        .section-subtitle {
            font-size: 14px;
            font-weight: bold;
            text-transform: uppercase;
            color: var(--text-light);
            letter-spacing: 0.5px;
            margin: 25px 0 10px 0;
            border-bottom: 1px solid var(--border);
            padding-bottom: 5px;
        }
        .description-box {
            background-color: var(--bg-muted);
            border-left: 4px solid var(--primary-light);
            padding: 15px;
            margin: 15px 0;
            font-size: 14px;
            white-space: pre-wrap;
        }
        .mitre-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin: 10px 0;
            padding: 0;
            list-style-type: none;
        }
        .mitre-item {
            background-color: var(--bg-muted);
            border: 1px solid var(--border);
            border-radius: 4px;
            padding: 5px 12px;
            font-size: 12px;
        }
        .mitre-id {
            font-weight: bold;
            color: var(--accent);
            margin-right: 5px;
        }
        .evidence-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 12px;
            margin-top: 15px;
        }
        .evidence-table th {
            background-color: var(--bg-muted);
            border-bottom: 2px solid var(--border);
            text-align: left;
            padding: 10px;
            font-weight: 600;
            color: var(--primary-light);
        }
        .evidence-table td {
            border-bottom: 1px solid var(--border);
            padding: 10px;
            vertical-align: top;
        }
        .evidence-table tr:nth-child(even) {
            background-color: #fafafa;
        }
        .footer {
            margin-top: 80px;
            border-top: 1px solid var(--border);
            padding-top: 20px;
            text-align: center;
            font-size: 12px;
            color: var(--text-light);
        }
        .confidence-indicator {
            font-size: 13px;
            font-weight: bold;
            color: var(--primary-light);
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>{{ title }}</h1>
                <p>Security Operations Center (SOC) Automated Audit Report</p>
            </div>
            <div class="meta-box">
                <div>Generated: {{ generated_at }}</div>
                <div>Classified: INTERNAL USE ONLY</div>
            </div>
        </div>

        <div class="summary-cards">
            <div class="card">
                <div class="value">{{ incidents|length }}</div>
                <div class="label">Total Incidents</div>
            </div>
            <div class="card">
                <div class="value">{{ critical_count }}</div>
                <div class="label">Critical Severity</div>
            </div>
            <div class="card">
                <div class="value">{{ high_count }}</div>
                <div class="label">High Severity</div>
            </div>
            <div class="card">
                <div class="value">{{ open_count }}</div>
                <div class="label">Active/Open</div>
            </div>
        </div>

        {% for incident in incidents %}
        <div class="incident-section">
            <div class="incident-header">
                <div>
                    <h2 class="incident-title">INC-{{ incident.id }}: {{ incident.title }}</h2>
                    <div class="incident-meta">
                        Detected: {{ incident.created_at }} &nbsp;|&nbsp;
                        Last Updated: {{ incident.updated_at }}
                    </div>
                    {% if incident.confidence is defined %}
                    <div class="confidence-indicator">
                        Analytic Confidence Score: {{ incident.confidence }}%
                    </div>
                    {% endif %}
                </div>
                <div>
                    <span class="badge badge-{{ incident.severity }}">{{ incident.severity }}</span>
                    <span class="badge badge-{{ incident.status }}">{{ incident.status }}</span>
                </div>
            </div>

            <div class="section-subtitle">Incident Description & Scope</div>
            <div class="description-box">{{ incident.description }}</div>

            {% if incident.mitre_mappings %}
            <div class="section-subtitle">MITRE ATT&CK Mappings</div>
            <ul class="mitre-list">
                {% for m in incident.mitre_mappings %}
                <li class="mitre-item">
                    <span class="mitre-id">{{ m.technique_id }}</span>: {{ m.technique_name }} ({{ m.tactic }})
                </li>
                {% endfor %}
            </ul>
            {% endif %}

            {% if incident.evidence_logs %}
            <div class="section-subtitle">Key Evidence Logs (First 100)</div>
            <table class="evidence-table">
                <thead>
                    <tr>
                        <th style="width: 15%;">Timestamp (UTC)</th>
                        <th style="width: 15%;">Source</th>
                        <th style="width: 15%;">Category</th>
                        <th style="width: 10%;">Severity</th>
                        <th style="width: 45%;">Message / raw data</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in incident.evidence_logs %}
                    <tr>
                        <td>{{ log.timestamp }}</td>
                        <td>{{ log.source }}</td>
                        <td>{{ log.category }}</td>
                        <td>
                            <span class="badge badge-{{ log.severity }}">{{ log.severity }}</span>
                        </td>
                        <td>{{ log.message }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% endif %}
        </div>
        {% endfor %}

        <div class="footer">
            <p>This document is automatically generated by the Security Log Analysis Assistant. Confidentiality: Highly Restricted.</p>
            <p>&copy; {{ current_year }} SOC Incident Response Team. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""
        # Calculate summary metrics
        critical_count = sum(1 for inc in incidents if getattr(inc, "severity", "").lower() == "critical")
        high_count = sum(1 for inc in incidents if getattr(inc, "severity", "").lower() == "high")
        open_count = sum(1 for inc in incidents if getattr(inc, "status", "").lower() in ("open", "in_progress"))

        generated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        current_year = datetime.utcnow().year

        template = self.env.from_string(template_str)
        rendered_html = template.render(
            title=title,
            incidents=incidents,
            critical_count=critical_count,
            high_count=high_count,
            open_count=open_count,
            generated_at=generated_at,
            current_year=current_year
        )

        filename = f"report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}.html"
        filepath = os.path.join(self.report_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(rendered_html)

        return filepath
