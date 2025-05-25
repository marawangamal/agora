import http.server
import socketserver
import threading
import webbrowser
import subprocess
import json
from typing import Optional
from urllib.parse import urlparse, parse_qs


class SimpleHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    """Simple HTTP request handler with error handling"""

    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_url = urlparse(self.path)

            if parsed_url.path == "/api/viz":
                # Handle API request for jrun viz
                self.handle_viz_request()
            else:
                # Handle main page
                self.handle_main_page()

        except BrokenPipeError:
            # Client disconnected, ignore
            pass
        except Exception as e:
            # Log other errors but don't crash
            print(f"Error handling request: {e}")

    def handle_viz_request(self):
        """Handle jrun viz API request"""
        try:
            # Run jrun viz --mode json
            result = subprocess.run(
                ["jrun", "viz", "--mode", "json"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

            response = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }

            self.wfile.write(json.dumps(response).encode("utf-8"))

        except subprocess.TimeoutExpired:
            self.send_error(408, "Request timeout")
        except FileNotFoundError:
            self.send_error(500, "jrun command not found")
        except Exception as e:
            self.send_error(500, f"Internal error: {str(e)}")

    def handle_main_page(self):
        """Handle main page request"""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()

        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>JRun Server</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        button {
            background: #007bff;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            margin: 10px 0;
        }
        button:hover {
            background: #0056b3;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        #output {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
            white-space: pre-wrap;
            font-family: monospace;
            max-height: 400px;
            overflow-y: auto;
            display: none;
        }
        .loading {
            color: #007bff;
            font-style: italic;
        }
        .error {
            color: #dc3545;
            background: #f8d7da;
            border-color: #f5c6cb;
        }
        .success {
            color: #155724;
            background: #d4edda;
            border-color: #c3e6cb;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Hello World from JRun!</h1>
        <p>Server is running successfully.</p>
        
        <button id="vizBtn" onclick="runJrunViz()">Run jrun viz --mode json</button>
        
        <div id="output"></div>
    </div>

    <script>
        async function runJrunViz() {
            const btn = document.getElementById('vizBtn');
            const output = document.getElementById('output');
            
            // Disable button and show loading
            btn.disabled = true;
            btn.textContent = 'Running...';
            output.style.display = 'block';
            output.className = 'loading';
            output.textContent = 'Executing jrun viz --mode json...';
            
            try {
                const response = await fetch('/api/viz');
                const data = await response.json();
                
                if (data.success) {
                    output.className = 'success';
                    output.textContent = data.stdout || 'Command executed successfully (no output)';
                } else {
                    output.className = 'error';
                    output.textContent = `Error (code ${data.returncode}):\\n${data.stderr || data.stdout || 'Unknown error'}`;
                }
            } catch (error) {
                output.className = 'error';
                output.textContent = `Network error: ${error.message}`;
            } finally {
                // Re-enable button
                btn.disabled = false;
                btn.textContent = 'Run jrun viz --mode json';
            }
        }
    </script>
</body>
</html>
"""
        self.wfile.write(html_content.encode("utf-8"))

    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[JRun Server] {format % args}")


class JRunWebServer:
    """Simple web server for jrun"""

    def __init__(self, port: int = 8080, host: str = "localhost"):
        self.port = port
        self.host = host
        self.server: Optional[socketserver.TCPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, open_browser: bool = True, blocking: bool = True):
        """Start the web server"""
        try:
            self.server = socketserver.TCPServer(
                (self.host, self.port), SimpleHTTPRequestHandler
            )

            url = f"http://{self.host}:{self.port}"
            print(f"🌳 JRun server starting at {url}")
            print(f"⏹️  Press Ctrl+C to stop")

            if open_browser:
                try:
                    webbrowser.open(url)
                except:
                    pass

            if blocking:
                try:
                    self.server.serve_forever()
                except KeyboardInterrupt:
                    print(f"\n🛑 Shutting down...")
                    self.stop()
            else:
                self.server_thread = threading.Thread(
                    target=self.server.serve_forever, daemon=True
                )
                self.server_thread.start()

        except OSError as e:
            if "Address already in use" in str(e):
                print(f"❌ Port {self.port} already in use")
            else:
                print(f"❌ Error: {e}")
            raise

    def stop(self):
        """Stop the server"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            print("✅ Server stopped")


def serve_web_interface(
    port: int = 8080,
    host: str = "localhost",
    open_browser: bool = True,
    blocking: bool = True,
):
    """Start the JRun web server"""
    server = JRunWebServer(port=port, host=host)
    server.start(open_browser=open_browser, blocking=blocking)
    return server
