#!/usr/bin/env python3
"""Local test harness only. Never copy tests into a publishable Web directory."""
import http.server
import json
import os
import pathlib
import sys

build = pathlib.Path(sys.argv[1]).resolve()
tests = pathlib.Path(__file__).resolve().parent


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/tests/controls.html':
            # Production DOM/CSS/event handlers with an explicitly fake engine.
            data = (build / 'index.html').read_text().replace('<head>', '<head><base href="/">')
            data = data.replace('./ioquake3.js', './tests/fake-engine.mjs')
            data = data.replace('ioq3 remaster', 'HOST FIXTURE — NOT A GAME')
            self.reply(data.encode(), 'text/html')
        elif path == '/tests/game-manifest.json':
            self.reply(json.dumps({'schemaVersion': 1, 'basegame': 'baseq3', 'revision': 'fixture', 'files': [
                {'path': 'baseq3/test.pk3', 'bytes': 3,
                 'sha256': 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'}]}).encode(), 'application/json')
        elif path == '/tests/baseq3/test.pk3':
            self.reply(b'abc', 'application/octet-stream')
        else:
            super().do_GET()

    def reply(self, data, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def translate_path(self, path):
        for name in ['runtime.html', 'fake-engine.mjs']:
            if path.split('?', 1)[0] == '/tests/' + name:
                return str(tests / name)
        return super().translate_path(path)


os.chdir(build)
http.server.ThreadingHTTPServer(('0.0.0.0', int(os.environ.get('PORT', '4174'))), Handler).serve_forever()
