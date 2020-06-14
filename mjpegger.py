#===========================================================================
# mjpegger.py
#
# Runs a MJPG stream on provided port.
#
# 2016-07-25 (original)
# 2020-06-14 (update)
# Carter Nelson
#===========================================================================
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import io

class MJPEGThread(threading.Thread):
    """Thread to serve MJPEG stream."""
    def __init__(self, **kwargs):
        super().__init__()

        self.keep_running = False

        self.server = HTTPServer(('', kwargs.get('port', 8081)), MJPEGStreamHandler)
        self.server.camera = kwargs.get('camera', None)
        self.server.resize = kwargs.get('resize', (640, 360))
        self.server.keep_streaming = False

    def run(self):
        self.keep_running = True
        self.server.keep_streaming = True
        while self.keep_running:
            self.server.handle_request()
        self.server.server_close()

    def stop(self):
        self.server.keep_streaming = False
        self.keep_running = False

class MJPEGStreamHandler(SimpleHTTPRequestHandler):
    """Handler for MJPEG stream."""

    def do_GET(self):
        camera = self.server.camera
        resize = self.server.resize

        stream = io.BytesIO()

        self.send_response(200)
        self.send_header('Content-type','multipart/x-mixed-replace; boundary=--picameramjpg')
        self.end_headers()
        for frame in camera.capture_continuous(stream, 'jpeg',
                                               use_video_port = True,
                                               resize = resize):
            if not self.server.keep_streaming:
                break
            self.wfile.write(b"--picameramjpg\n")
            self.send_header('Content-type','image/jpeg')
            self.send_header('Content-length',len(stream.getvalue()))
            self.end_headers()
            self.wfile.write(stream.getvalue())
            stream.seek(0)
            stream.truncate()

        self.server.camera.close()