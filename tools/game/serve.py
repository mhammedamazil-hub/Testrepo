"""Serve the real Godot Web export, with WASM MIME and optional gzip files."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import mimetypes

class GameHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control','no-cache')
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()

    def send_head(self):
        path=Path(self.translate_path(self.path.split('?',1)[0]))
        compressed=Path(str(path)+'.gz')
        if path.suffix in {'.wasm','.pck','.js'} and compressed.is_file() and 'gzip' in self.headers.get('Accept-Encoding',''):
            stream=compressed.open('rb')
            self.send_response(200)
            self.send_header('Content-Type',mimetypes.guess_type(str(path))[0] or 'application/octet-stream')
            self.send_header('Content-Encoding','gzip')
            self.send_header('Content-Length',str(compressed.stat().st_size))
            self.send_header('Vary','Accept-Encoding')
            self.end_headers()
            return stream
        return super().send_head()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',default='.exports/web')
    parser.add_argument('--port',type=int,default=3000)
    args=parser.parse_args()
    directory=Path(args.directory).resolve()
    if not (directory/'index.html').is_file():raise SystemExit('Export missing: run tools/game/export_game.py first')
    mimetypes.add_type('application/wasm','.wasm')
    print(f'Serving actual Godot game on 0.0.0.0:{args.port} from {directory}',flush=True)
    ThreadingHTTPServer(('0.0.0.0',args.port),partial(GameHandler,directory=str(directory))).serve_forever()
