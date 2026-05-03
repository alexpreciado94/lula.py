# sub.py — Servidor y Salud de Hardware
import os, sys


def start_web_server():
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class TinyHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            if self.path == "/favicon.ico":
                self.send_response(204)
                self.end_headers()
                return
            try:
                return super().do_GET()
            except:
                pass

    os.makedirs("/app/data", exist_ok=True)
    os.chdir("/app/data")
    try:
        server = HTTPServer(("0.0.0.0", 5000), TinyHandler)
        server.serve_forever()
    except:
        pass


def calculate_ia_weight(prob):
    """Calcula cuánto del bloque de $4,000 usamos según la prob."""
    if prob >= 0.88:
        return 1.0  # 100% ($4,000)
    if prob >= 0.78:
        return 0.7  # 70%  ($2,800)
    if prob >= 0.68:
        return 0.4  # 40%  ($1,600)
    if prob >= 0.60:
        return 0.2  # 20%  ($800)
    return 0.0  # Bloqueado
