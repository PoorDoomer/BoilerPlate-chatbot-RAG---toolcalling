#!/usr/bin/env python3
"""
Simple HTTP server for serving generated dashboards.
Provides a web interface to view and manage generated dashboards.
"""

import os
import sys
import http.server
import socketserver
import webbrowser
from urllib.parse import urlparse, parse_qs
import json
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DashboardLLM import DashboardLLM


class DashboardHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for dashboard serving."""
    
    def __init__(self, *args, **kwargs):
        # Set the directory to serve files from
        self.dashboard_dir = "dashboard gen/generated_dashboards"
        super().__init__(*args, directory=self.dashboard_dir, **kwargs)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == "/" or parsed_path.path == "/index":
            self.serve_dashboard_index()
        elif parsed_path.path == "/generate":
            self.serve_generate_form()
        elif parsed_path.path == "/api/generate":
            self.handle_generate_api(parsed_path.query)
        elif parsed_path.path.startswith("/dashboard/"):
            self.serve_dashboard_file(parsed_path.path)
        else:
            # Default file serving
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/api/generate":
            self.handle_generate_post()
        else:
            self.send_error(404)
    
    def serve_dashboard_index(self):
        """Serve the main dashboard index page."""
        dashboard_files = self.get_dashboard_files()
        
        html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Gallery</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            max-width: 1200px;
            margin: 0 auto;
        }}
        .dashboard-card {{
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .dashboard-card:hover {{
            transform: translateY(-2px);
        }}
        .dashboard-title {{
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        .dashboard-meta {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 15px;
        }}
        .dashboard-actions {{
            display: flex;
            gap: 10px;
        }}
        .btn {{
            padding: 8px 16px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
            font-size: 0.9em;
            transition: background-color 0.2s;
        }}
        .btn-primary {{
            background-color: #2196F3;
            color: white;
        }}
        .btn-primary:hover {{
            background-color: #1976D2;
        }}
        .btn-secondary {{
            background-color: #666;
            color: white;
        }}
        .generate-section {{
            text-align: center;
            margin-bottom: 40px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .generate-form {{
            max-width: 600px;
            margin: 0 auto;
        }}
        .prompt-input {{
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1em;
            margin-bottom: 10px;
        }}
        .no-dashboards {{
            text-align: center;
            color: #666;
            font-style: italic;
            grid-column: 1 / -1;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🚀 Dashboard Gallery</h1>
        <p>Interactive dashboards generated from natural language prompts</p>
    </div>

    <div class="generate-section">
        <h2>Generate New Dashboard</h2>
        <div class="generate-form">
            <form action="/api/generate" method="post">
                <input type="text" 
                       name="prompt" 
                       class="prompt-input" 
                       placeholder="Enter your dashboard prompt (e.g., 'Show me monthly revenue and top products')"
                       required>
                <button type="submit" class="btn btn-primary">Generate Dashboard</button>
            </form>
        </div>
    </div>

    <div class="dashboard-grid">
        {self.render_dashboard_cards(dashboard_files)}
    </div>

    <script>
        // Auto-refresh every 30 seconds to show new dashboards
        setTimeout(() => {{
            window.location.reload();
        }}, 30000);
    </script>
</body>
</html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html_content.encode())
    
    def get_dashboard_files(self):
        """Get list of dashboard files with metadata."""
        dashboard_files = []
        dashboard_dir = "dashboard gen/generated_dashboards"
        
        if os.path.exists(dashboard_dir):
            for filename in os.listdir(dashboard_dir):
                if filename.endswith('.html'):
                    filepath = os.path.join(dashboard_dir, filename)
                    stat = os.stat(filepath)
                    
                    dashboard_files.append({
                        'filename': filename,
                        'filepath': filepath,
                        'created': datetime.fromtimestamp(stat.st_ctime),
                        'size': stat.st_size
                    })
        
        # Sort by creation time, newest first
        dashboard_files.sort(key=lambda x: x['created'], reverse=True)
        return dashboard_files
    
    def render_dashboard_cards(self, dashboard_files):
        """Render dashboard cards HTML."""
        if not dashboard_files:
            return '<div class="no-dashboards">No dashboards generated yet. Create your first dashboard above!</div>'
        
        cards_html = []
        for dashboard in dashboard_files:
            card_html = f'''
            <div class="dashboard-card">
                <div class="dashboard-title">{dashboard['filename']}</div>
                <div class="dashboard-meta">
                    Created: {dashboard['created'].strftime('%Y-%m-%d %H:%M:%S')}<br>
                    Size: {dashboard['size']:,} bytes
                </div>
                <div class="dashboard-actions">
                    <a href="/dashboard/{dashboard['filename']}" class="btn btn-primary" target="_blank">Open Dashboard</a>
                    <a href="/{dashboard['filename']}" class="btn btn-secondary" download>Download</a>
                </div>
            </div>
            '''
            cards_html.append(card_html)
        
        return '\n'.join(cards_html)
    
    def serve_dashboard_file(self, path):
        """Serve a specific dashboard file."""
        filename = path.split('/')[-1]
        filepath = os.path.join("dashboard gen/generated_dashboards", filename)
        
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                content = f.read()
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_error(404)
    
    def handle_generate_post(self):
        """Handle POST request to generate dashboard."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # Parse form data
            from urllib.parse import parse_qs
            form_data = parse_qs(post_data)
            prompt = form_data.get('prompt', [''])[0]
            
            if not prompt:
                self.send_error(400, "Missing prompt parameter")
                return
            
            # Generate dashboard
            dashboard_llm = DashboardLLM()
            result = dashboard_llm.generate_dashboard_from_prompt(prompt, save_file=True)
            
            # Redirect to dashboard or show error
            if result['filepath']:
                filename = os.path.basename(result['filepath'])
                self.send_response(302)
                self.send_header('Location', f'/dashboard/{filename}')
                self.end_headers()
            else:
                self.send_error(500, "Failed to generate dashboard")
                
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")


def start_dashboard_server(port=8080, auto_open=True):
    """
    Start the dashboard server.
    
    Args:
        port (int): Port to serve on
        auto_open (bool): Whether to automatically open browser
    """
    # Create generated_dashboards directory if it doesn't exist
    os.makedirs("dashboard gen/generated_dashboards", exist_ok=True)
    
    try:
        with socketserver.TCPServer(("", port), DashboardHTTPRequestHandler) as httpd:
            print(f"🌐 Dashboard server starting on http://localhost:{port}")
            print("📊 Dashboard Gallery: http://localhost:{port}")
            print("🛠️  Generate Dashboard: http://localhost:{port}/generate")
            print("⏹️  Press Ctrl+C to stop the server")
            
            if auto_open:
                webbrowser.open(f'http://localhost:{port}')
            
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n👋 Server stopped")
    except Exception as e:
        print(f"❌ Server error: {str(e)}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Dashboard Server")
    parser.add_argument("--port", type=int, default=8080, help="Port to serve on (default: 8080)")
    parser.add_argument("--no-open", action="store_true", help="Don't automatically open browser")
    
    args = parser.parse_args()
    
    start_dashboard_server(port=args.port, auto_open=not args.no_open) 