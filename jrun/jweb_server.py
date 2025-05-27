import http.server
import socketserver
import threading
import webbrowser
import subprocess
import json
import os
from typing import Optional
from urllib.parse import urlparse


class ReactAppHandler(http.server.SimpleHTTPRequestHandler):
    """Handler for serving React app with API endpoints"""

    def __init__(self, *args, build_dir="build", **kwargs):
        self.build_dir = build_dir
        super().__init__(*args, directory=build_dir, **kwargs)

    def do_GET(self):
        """Handle GET requests"""
        try:
            parsed_url = urlparse(self.path)

            if parsed_url.path.startswith("/api/"):
                self.handle_api_request(parsed_url.path)
            else:
                # Serve React app files
                self.serve_react_app(parsed_url.path)

        except BrokenPipeError:
            pass
        except Exception as e:
            print(f"Error handling request: {e}")

    def serve_react_app(self, path):
        """Serve React app files with SPA routing support"""
        # For SPA routing, serve index.html for non-file requests
        if not path.startswith("/static/") and "." not in os.path.basename(path):
            self.path = "/index.html"

        # Use parent class to serve static files
        super().do_GET()

    def handle_api_request(self, path):
        """Handle API requests"""
        if path == "/api/viz":
            self.handle_viz_request()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_viz_request(self):
        """Handle jrun viz API request"""
        try:
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

    def log_message(self, format, *args):
        """Override to customize logging"""
        print(f"[React Server] {format % args}")


class ReactWebServer:
    """Web server for Next.js static export with API"""

    def __init__(
        self, port: int = 3000, host: str = "localhost", build_dir: str = "out"
    ):
        self.port = port
        self.host = host
        self.build_dir = build_dir
        self.server: Optional[socketserver.TCPServer] = None
        self.server_thread: Optional[threading.Thread] = None

    def start(self, open_browser: bool = True, blocking: bool = True):
        """Start the React server"""
        # Check if build directory exists
        if not os.path.exists(self.build_dir):
            print(f"❌ Export directory '{self.build_dir}' not found!")
            print(f"💡 Run 'npm run build' in your Next.js app first")
            print(f"💡 Make sure you have 'output: export' in next.config.js")
            return

        try:
            # Create custom handler with build directory
            handler = lambda *args, **kwargs: ReactAppHandler(
                *args, build_dir=self.build_dir, **kwargs
            )

            self.server = socketserver.TCPServer((self.host, self.port), handler)

            url = f"http://{self.host}:{self.port}"
            print(f"⚛️  Next.js server starting at {url}")
            print(f"📁 Serving from: {os.path.abspath(self.build_dir)}")
            print(f"🔌 API available at: {url}/api/viz")
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
            print("✅ React server stopped")


def serve_react_app(
    port: int = 3000,
    host: str = "localhost",
    build_dir: str = "out",
    open_browser: bool = True,
    blocking: bool = True,
):
    """Start the Next.js static export server"""
    server = ReactWebServer(port=port, host=host, build_dir=build_dir)
    server.start(open_browser=open_browser, blocking=blocking)
    return server


# Usage example:
if __name__ == "__main__":
    # Serve Next.js static export from 'out' directory
    serve_react_app(port=3000, build_dir="out")
