import threading
import SimpleHTTPServer
import SocketServer
import io

keepStreaming = False
camera = None
resize = (640,360)

class MJPGStreamThread(threading.Thread):
    """Thread to server MJPG stream."""
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)
        
        global camera, resize
        camera = kwargs['camera']
        resize = kwargs['resize']
        self.port = kwargs['port']
        self.keepRunnning = False
        self.streamRunning = False
        self.server = None
    
    def run(self, ):
        print "mjpgstream_thread starting"
        self.server = SocketServer.TCPServer(("",self.port), MJPGStreamHandler,
            bind_and_activate=False)
        self.server.allow_reuse_address = True
        self.server.timeout = 0.1
        self.server.server_bind()
        self.server.server_activate()
        self.keepRunning = True
        self.streamRunning = True        
        while self.keepRunning:   
            self.server.handle_request()
        self.streamRunning = False
        camera.close()
        self.server.server_close()
        print "mjpgstream_thread done"
            
    def stop(self, ):
        global keepStreaming
        keepStreaming = False
        self.keepRunning = False
        
class MJPGStreamHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    """Handler for MJPG stream."""
    
    def do_GET(self, ):
        print "mjpgstream handler GET"
        global keepStreaming
        keepStreaming = True
        
        stream = io.BytesIO()
        
        self.send_response(200)
        self.send_header('Content-type','multipart/x-mixed-replace; boundary=--picameramjpg')
        self.end_headers()
        for frame in camera.capture_continuous(stream, 'jpeg',
                                                    use_video_port = True,
                                                    resize = resize):
            if not keepStreaming:
                break
            self.wfile.write("--picameramjpg")
            self.send_header('Content-type','image/jpeg')
            self.send_header('Content-length',len(stream.getvalue()))
            self.end_headers()
            self.wfile.write(stream.getvalue())
            stream.seek(0)
            stream.truncate() 