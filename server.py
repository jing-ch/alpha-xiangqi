#!/usr/bin/env python3
from http.server import HTTPServer, SimpleHTTPRequestHandler

def main():
    port = 8000
    server = HTTPServer(('localhost', port), SimpleHTTPRequestHandler)
    print(f"Xiangqi server running at http://localhost:{port}")
    server.serve_forever()

if __name__ == "__main__":
    main()