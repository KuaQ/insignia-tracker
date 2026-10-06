from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)

host="127.0.0.1"
port=8080
print(f"Insignia Tracker: http://{host}:{port}/dashboard/")
ThreadingHTTPServer((host,port),SimpleHTTPRequestHandler).serve_forever()
