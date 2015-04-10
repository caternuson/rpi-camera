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
import os

# Root directory where app was launched
root_dir = os.getcwd()

# define port server will listen to
PORT = 8008

# Camera setup
camera = campi.Campi()
resolution = (1920, 1080)                   # resolution of images
jpeg_quality = 100                          # jpeg image quality
camera.set_cam_config(resolution=resolution,quality=jpeg_quality)

# Default time lapse config
delta_time = 10                             # delta time in seconds
total_imgs = 2                           # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

ISO = 400
shutter = 0

def start_timelapse():
    total_time = delta_time * (total_imgs-1)
    print "delta_time=%g" % delta_time
    print "total_imgs=%g" % total_imgs
    print "total_time=%g" % total_time
    
    # Create directory for files and go there
    timelapse_name = time.strftime("%Y%m%d_%H%M",time.localtime())
    try:
        os.mkdir(timelapse_name)
    except OSError:
        # directory exist
        # not likely in real world scenario ?
        # ignore and overwrite, for now
        pass
    os.chdir(timelapse_name)
    
    # Mark the time                  
    start_time  = time.time()
    finish_time = start_time + total_time
    
    # Try block for image capture
    try:                
        # Main time lapse loop
        for image_count in xrange(1,total_imgs+1):
            # Take the image
            #print "Taking next image."
            #disp_big_msg(" TAKE ")
            filename = timelapse_name+"_%04d.jpg" % image_count
            acquire_start = time.time()
            camera.disp_msg("[{0}/{1}]:{2}".format(image_count,total_imgs,filename))
            camera.capture(filename)
            acquire_finish = time.time()
            acquire_time = acquire_finish - acquire_start
            # Pause
            if (image_count<total_imgs):
                # print "Waiting for time to lapse."
                keep_waiting = True
                while keep_waiting:
                    time.sleep(0.250)
                    current_time = time.time()
                    time_to_next = acquire_start + delta_time - current_time
                    time_remaining = time_to_next + delta_time*(total_imgs-image_count-1) + acquire_time
                    #disp_show_status(time_to_next, image_count, time_remaining)
                    camera.disp_msg("%g" % time_remaining)
                    if (time_to_next <= 0 ):
                        keep_waiting = False                                 
    finally:
        #disp_big_msg(" DONE ")
        camera.disp_msg("DONE")
        time.sleep(1)
    #print "Time lapse complete, saved to {0}.".format(timelapse_name)
    os.chdir(root_dir)

#-------------------------------------------------------------------------
# Tornado Server Setup
#-------------------------------------------------------------------------
# camera preview
class CameraPreviewHandler(tornado.web.RequestHandler):
    def get(self):
        print "GET Request from {}".format(self.request.remote_ip)
        self.render("camera_preview.html")

# camera preview webscoket        
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
        
# camera set up
class CameraSetUpHandler(tornado.web.RequestHandler):
    def get(self):
        global delta_time
        global total_imgs
        global ISO
        global shutter
        print "GET Request from {}".format(self.request.remote_ip)
        delta_time = int(self.get_argument("delta_time", default=delta_time))
        total_imgs = int(self.get_argument("total_imgs", default=total_imgs))
        ISO = int(self.get_argument("ISO", default=ISO))
        shutter = int(self.get_argument("shutter", default=shutter))
        camera.disp_msg("DT=%g  N=%g ISO=%g s=%g" % (delta_time, total_imgs, ISO, shutter))
        URL  = "camera_setup.html"
        #URL += "?delta_time=%g" % delta_time
        #URL += "&total_imgs=%g" % total_imgs
        #URL += "&ISO=%g" % ISO
        #URL += "&shutter=%g" % shutter
        self.render(URL,delta_time=20,total_imgs=3,ISO=400,shutter=125000)
        
    def post(self):
        print "POST Request from {}".format(self.request.remote_ip)
        #delta_time = int(self.get_argument('delta_time'))
        #total_imgs = int(self.get_argument('total_imgs'))
        #camera.disp_msg("DT=%s  N=%s" % (delta_time, total_imgs))
        #self.write("DT=%s  N=%s" % (DT, N))
        #self.set_header("Content-Type", "text/plain")
        #self.write("You wrote " + self.get_body_argument("message"))
        
# camera time lapse
class CameraTimeLapseHandler(tornado.web.RequestHandler):
    def get(self):
        self.write("OK, HERE WE GO!!!")
        self.write("DT=%s  N=%s" % (delta_time, total_imgs))
        start_timelapse()

# separate HTTP and WebSockets based on URL
handlers = ([
    (r"/camera_setup",      CameraSetUpHandler),
    (r"/camera_timelapse",  CameraTimeLapseHandler),
    (r"/camera_preview",    CameraPreviewHandler),
    (r"/camera_ws",         CameraPreviewWebSocket)
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
