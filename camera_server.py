#!/usr/bin/python
#===========================================================================
# camera_server.py
#
# Time lapse camera app with web interface.
#
# Uses the "5 Identification Mono" font created by:
#       http://winty5.wix.com/noahtheawesome
#       Note of the author:
#       Free for personal and commercial uses
#
# 2015-04-06
# Carter Nelson
#===========================================================================
import campi

import tornado.httpserver
import tornado.websocket
import tornado.web

import time
import cStringIO as io
import base64
import Image
import ImageDraw
import ImageFont

# define port server will listen to
PORT = 8008

# Camera setup
camera = campi.Campi()
resolution = (1920, 1080)                   # resolution of images
jpeg_quality = 100                          # jpeg image quality
camera.set_cam_config(resolution=resolution,quality=jpeg_quality)

# Default time lapse config
delta_time = 60                             # delta time in seconds
total_imgs = 500                           # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

#-------------------------------------------------------------------------
# Tornado Server Setup
#-------------------------------------------------------------------------
# camera preview
class CameraPreviewHandler(tornado.web.RequestHandler):
    def get(self):
        print "GET Request from {}".format(self.request.remote_ip)
        self.render("camera_preview.html")
        
class CameraPreviewWebSocket(tornado.websocket.WebSocketHandler):
    
    def initialize(self):
        self.camera_loop = None
        
    def loop(self):
        iostream = io.StringIO()
        camera.capture_stream(iostream)
        try:
            self.write_message(base64.b64encode(iostream.getvalue()))
        except tornado.websocket.WebSocketClosedError:
            self.__stopStream__()

        
    def open(self):
        self.__startStream__()
    
    def on_close(self):
        self.__stopStream__()
    
    def __startStream__(self):
        self.camera_loop = tornado.ioloop.PeriodicCallback(self.loop, 500)
        self.camera_loop.start()
    
    def __stopStream__(self):
        if (self.camera_loop != None):
            self.camera_loop.stop()
            self.camera_loop = None
        
# this will handle HTTP requests
class MyRequestHandler(tornado.web.RequestHandler):
    def get(self):
        print "GET Request from {}".format(self.request.remote_ip)
        self.render("camera.html")
        
    def post(self):
        print "POST Request from {}".format(self.request.remote_ip)
        DT = self.get_argument('delta_time')
        N = self.get_argument('total_imgs')
        self.write("DT=%s  N=%s" % (DT, N))
        #self.set_header("Content-Type", "text/plain")
        #self.write("You wrote " + self.get_body_argument("message"))        

# separate HTTP and WebSockets based on URL
handlers = ([
    (r"/camera", MyRequestHandler),
    (r"/camera_preview", CameraPreviewHandler),
    (r"/camera_ws", CameraPreviewWebSocket)
])

#===========================
# MAIN
#===========================
print "create app..."
app = tornado.web.Application(handlers)
print "create http server..."
server = tornado.httpserver.HTTPServer(app)
print "start listening on port {}...".format(PORT)
server.listen(PORT)
print "start ioloop..."
tornado.ioloop.IOLoop.instance().start()
print "i guess we're done then."
