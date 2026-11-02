"""Disposable loopback-only fixture; no database, accounts or write endpoints."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import escape

PAGES = {'/': 'Local QA Demo', '/catalog': 'Product catalog', '/help': 'Help center',
         '/status': 'Service status', '/about': 'About this demo'}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in PAGES:
            self.send_error(404)
            return
        nav = ' | '.join(f'<a href="{p}">{escape(n)}</a>' for p, n in PAGES.items())
        body = (f'<!doctype html><html lang="en"><meta charset="utf-8">'
                f'<title>{PAGES[self.path]}</title><body><nav>{nav}</nav>'
                f'<main><h1>{PAGES[self.path]}</h1><p>Read-only local test fixture.</p>'
                f'</main></body></html>').encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == '__main__':
    print('Local demo: http://127.0.0.1:8765 (Ctrl+C to stop)', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8765), Handler).serve_forever()
