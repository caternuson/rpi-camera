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
# this will handle HTTP requests
class MyRequestHandler(tornado.web.RequestHandler):
    def get(self):
        print "GET Request from {}".format(self.request.remote_ip)
        self.render("camera.html")

# separate HTTP and WebSockets based on URL
handlers = ([
    (r"/camera", MyRequestHandler),
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
