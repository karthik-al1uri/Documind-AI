#!/usr/bin/env python3
"""Generate visualizations and reports from test results."""

import json
import sys
from pathlib import Path
from datetime import datetime

RESULTS_FILE = Path(__file__).resolve().parent / "test_results.json"
OUTPUT_DIR = Path(__file__).resolve().parent / "report"


def load_results() -> dict:
    """Load test results from JSON file."""
    if not RESULTS_FILE.exists():
        print(f"❌ Results file not found: {RESULTS_FILE}")
        print("   Run run_batch_tests.py first")
        sys.exit(1)
    
    with open(RESULTS_FILE) as f:
        return json.load(f)


def generate_html_report(data: dict) -> str:
    """Generate an HTML report with tables and charts."""
    summary = data["summary"]
    results = data["results"]
    
    # Calculate per-document-type stats
    type_stats = {}
    for r in results:
        if r["success"]:
            doc_type = r.get("doc_type", "unknown")
            if doc_type not in type_stats:
                type_stats[doc_type] = {
                    "count": 0,
                    "total_time": 0,
                    "total_pages": 0,
                    "total_chunks": 0,
                }
            type_stats[doc_type]["count"] += 1
            type_stats[doc_type]["total_time"] += r.get("response_time_sec", 0)
            type_stats[doc_type]["total_pages"] += r.get("pages_extracted", 0) or 0
            type_stats[doc_type]["total_chunks"] += r.get("chunks_indexed", 0) or 0
    
    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>DocuMind AI Test Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        .header h1 {{ margin: 0; font-size: 2em; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stat-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
            margin-top: 5px;
        }}
        
        .section {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .section h2 {{
            margin-top: 0;
            color: #333;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }}
        tr:hover {{ background: #f8f9fa; }}
        .success {{ color: #28a745; }}
        .failure {{ color: #dc3545; }}
        
        .chart-container {{
            position: relative;
            height: 300px;
            margin: 20px 0;
        }}
        
        .two-column {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        @media (max-width: 768px) {{
            .two-column {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 DocuMind AI Test Report</h1>
        <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p>Test Run: {data['test_run']['timestamp'][:19]}</p>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card">
            <div class="value">{summary['total_tests']}</div>
            <div class="label">Total PDFs Tested</div>
        </div>
        <div class="stat-card">
            <div class="value">{summary['success_rate_pct']}%</div>
            <div class="label">Success Rate</div>
        </div>
        <div class="stat-card">
            <div class="value">{summary['total_pages_processed']}</div>
            <div class="label">Pages Processed</div>
        </div>
        <div class="stat-card">
            <div class="value">{summary['total_chunks_indexed']}</div>
            <div class="label">Chunks Indexed</div>
        </div>
        <div class="stat-card">
            <div class="value">{summary['avg_response_time_sec']:.2f}s</div>
            <div class="label">Avg Response Time</div>
        </div>
        <div class="stat-card">
            <div class="value">{summary['total_data_uploaded_mb']:.2f}</div>
            <div class="label">MB Data Processed</div>
        </div>
    </div>
    
    <div class="two-column">
        <div class="section">
            <h2>📈 Document Type Distribution</h2>
            <div class="chart-container">
                <canvas id="docTypeChart"></canvas>
            </div>
        </div>
        
        <div class="section">
            <h2>⏱️ Response Time Distribution</h2>
            <div class="chart-container">
                <canvas id="responseTimeChart"></canvas>
            </div>
        </div>
    </div>
    
    <div class="section">
        <h2>📋 Per-Document-Type Statistics</h2>
        <table>
            <thead>
                <tr>
                    <th>Document Type</th>
                    <th>Count</th>
                    <th>Avg Time (s)</th>
                    <th>Avg Pages</th>
                    <th>Avg Chunks</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for doc_type, stats in sorted(type_stats.items()):
        avg_time = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0
        avg_pages = stats["total_pages"] / stats["count"] if stats["count"] > 0 else 0
        avg_chunks = stats["total_chunks"] / stats["count"] if stats["count"] > 0 else 0
        
        html += f"""                <tr>
                    <td><strong>{doc_type.replace('_', ' ').title()}</strong></td>
                    <td>{stats['count']}</td>
                    <td>{avg_time:.2f}</td>
                    <td>{avg_pages:.1f}</td>
                    <td>{avg_chunks:.1f}</td>
                </tr>
"""
    
    html += """            </tbody>
        </table>
    </div>
    
    <div class="section">
        <h2>📁 Detailed Results</h2>
        <table>
            <thead>
                <tr>
                    <th>Filename</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Time (s)</th>
                    <th>Pages</th>
                    <th>Chunks</th>
                </tr>
            </thead>
            <tbody>
"""
    
    for r in results:
        status_class = "success" if r["success"] else "failure"
        status_icon = "✅" if r["success"] else "❌"
        html += f"""                <tr>
                    <td>{r['filename']}</td>
                    <td>{r.get('doc_type', 'N/A')}</td>
                    <td class="{status_class}">{status_icon} {r.get('status', 'N/A')}</td>
                    <td>{r.get('response_time_sec', 0):.2f}</td>
                    <td>{r.get('pages_extracted', 'N/A')}</td>
                    <td>{r.get('chunks_indexed', 'N/A')}</td>
                </tr>
"""
    
    # Prepare chart data
    doc_type_labels = list(summary['document_types'].keys())
    doc_type_values = list(summary['document_types'].values())
    
    response_times = [r['response_time_sec'] for r in results if r['success']]
    time_ranges = {
        '0-2s': sum(1 for t in response_times if t <= 2),
        '2-5s': sum(1 for t in response_times if 2 < t <= 5),
        '5-10s': sum(1 for t in response_times if 5 < t <= 10),
        '10s+': sum(1 for t in response_times if t > 10),
    }
    
    html += f"""            </tbody>
        </table>
    </div>
    
    <script>
        // Document Type Chart
        new Chart(document.getElementById('docTypeChart'), {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(doc_type_labels)},
                datasets: [{{
                    data: {json.dumps(doc_type_values)},
                    backgroundColor: [
                        '#667eea', '#764ba2', '#f093fb', '#f5576c',
                        '#4facfe', '#00f2fe', '#43e97b', '#fa709a'
                    ]
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'right'
                    }}
                }}
            }}
        }});
        
        // Response Time Chart
        new Chart(document.getElementById('responseTimeChart'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(time_ranges.keys()))},
                datasets: [{{
                    label: 'Number of Documents',
                    data: {json.dumps(list(time_ranges.values()))},
                    backgroundColor: '#667eea'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html


def generate_markdown_table(data: dict) -> str:
    """Generate a Markdown table for easy copying."""
    summary = data["summary"]
    results = data["results"]
    
    md = f"""# DocuMind AI Batch Test Results

**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary

| Metric | Value |
|--------|-------|
| Total PDFs | {summary['total_tests']} |
| Successful | {summary['successful_uploads']} |
| Failed | {summary['failed_uploads']} |
| Success Rate | {summary['success_rate_pct']}% |
| Total Time | {summary['total_time_sec']:.2f}s |
| Avg Response Time | {summary['avg_response_time_sec']:.2f}s |
| Total Pages | {summary['total_pages_processed']} |
| Total Chunks | {summary['total_chunks_indexed']} |

## Document Types

| Type | Count |
|------|-------|
"""
    
    for doc_type, count in summary['document_types'].items():
        md += f"| {doc_type} | {count} |\n"
    
    md += """
## Detailed Results

| Filename | Type | Status | Time (s) | Pages | Chunks |
|----------|------|--------|----------|-------|--------|
"""
    
    for r in results:
        status = "✅" if r["success"] else "❌"
        md += f"| {r['filename']} | {r.get('doc_type', 'N/A')} | {status} {r.get('status', 'N/A')} | {r.get('response_time_sec', 0):.2f} | {r.get('pages_extracted', 'N/A')} | {r.get('chunks_indexed', 'N/A')} |\n"
    
    return md


def main():
    """Main entry point."""
    print("=" * 70)
    print("DOCUMIND AI REPORT GENERATOR")
    print("=" * 70)
    
    # Load results
    print("\n1. Loading test results...")
    data = load_results()
    print(f"✅ Loaded {len(data['results'])} test results")
    
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Generate HTML report
    print("\n2. Generating HTML report...")
    html = generate_html_report(data)
    html_file = OUTPUT_DIR / "report.html"
    with open(html_file, "w") as f:
        f.write(html)
    print(f"✅ HTML report saved to {html_file}")
    
    # Generate Markdown table
    print("\n3. Generating Markdown table...")
    md = generate_markdown_table(data)
    md_file = OUTPUT_DIR / "table.md"
    with open(md_file, "w") as f:
        f.write(md)
    print(f"✅ Markdown table saved to {md_file}")
    
    # Print quick summary
    print("\n" + "=" * 70)
    print("QUICK SUMMARY")
    print("=" * 70)
    summary = data["summary"]
    print(f"✅ {summary['successful_uploads']}/{summary['total_tests']} uploads successful ({summary['success_rate_pct']}%)")
    print(f"⏱️  Avg response time: {summary['avg_response_time_sec']:.2f}s")
    print(f"📄 Total pages: {summary['total_pages_processed']}")
    print(f"🧩 Total chunks: {summary['total_chunks_indexed']}")
    print(f"\n📊 Open {html_file} in your browser to view the full report")
    print("=" * 70)


if __name__ == "__main__":
    main()
