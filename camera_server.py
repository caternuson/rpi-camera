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

#-------------------------------------------------------------------------
# LCD display functions
#-------------------------------------------------------------------------
# Load fonts
font_small = ImageFont.load_default()
font_large = ImageFont.truetype("5Identification-Mono.ttf",12)

# Image draw buffer for writing to LCD display
disp_image = Image.new('1', camera.get_lcd_size())
disp_draw  = ImageDraw.Draw(disp_image)

# Display locations
WHOLE_SCREEN    = campi.WHOLE_SCREEN
BIG4_1          = (31,0)
BIG4_2          = (31,18)
BIG_MSG         = (0,12)         
BIG4_1_LABEL    = (4,5)
BIG4_2_LABEL    = (4,23)
TIME_1          = (4,36)
TIME_2          = (2,36)
TOT_IMG         = (60,36)
OK_CONFIRM      = (4,14)
PROG_BAR_H      = 31
PROG_BAR_W      = 14
PROG_BAR_LOC    = (8,4)
PROG_BAR_BOX    = (PROG_BAR_LOC,(PROG_BAR_LOC[0]+PROG_BAR_W,PROG_BAR_LOC[1]+PROG_BAR_H))
Y1              = 0
Y2              = Y1 + font_small.getsize(" ")[1]
Y3              = Y2 + (Y2-Y1)
Y4              = Y3 + (Y2-Y1)
Y5              = Y4 + (Y2-Y1)

def disp_big_msg(msg, location=BIG_MSG):
    # Display a message using large font
    disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
    disp_draw.text(location, msg, font=font_large)
    camera.disp_image(disp_image)

def disp_show_config():
    # Display current time lapse config info
    disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)   
    disp_draw.text(BIG4_1_LABEL," d=", font=font_small)
    disp_draw.text(BIG4_1, "%04d" % (delta_time), font=font_large)
    disp_draw.text(BIG4_2_LABEL, " N=", font=font_small)
    disp_draw.text(BIG4_2, "%04d" % (total_imgs), font=font_large)   
    disp_draw.text(TIME_1, time.strftime(" T=  %H:%M:%S", time.gmtime(total_time)), font=font_small)
    camera.disp_image(disp_image)
    
def disp_show_summary():
    # Display summary of time lapse config info
    disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
    disp_draw.text(BIG4_1,"%04d" % (delta_time), font=font_large)
    disp_draw.text(BIG4_2, "%04d" % (total_imgs), font=font_large)       
    disp_draw.text(TIME_1, time.strftime("     %H:%M:%S", time.gmtime(total_time)), font=font_small)
    disp_draw.text(OK_CONFIRM,"OK?", font=font_small)
    camera.disp_image(disp_image)
    
def disp_show_summary2():
    # Display summary of time lapse and camera config
    disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
    disp_draw.text((0,Y1),"del_tim=%04d" % (delta_time), font=font_small)
    disp_draw.text((0,Y2),"tot_imgs=%04d" % (total_imgs), font=font_small)
    disp_draw.text((0,Y3),"ISO=%g" % (camera._iso), font=font_small)
    disp_draw.text((0,Y4),"s=%g" % (camera._shutter_speed) , font=font_small)
    camera.disp_image(disp_image)
    
def disp_show_status(time_to_next, image_count, time_remaining):
    disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
    disp_draw.rectangle(PROG_BAR_BOX, outline=0, fill=255)
    #progress = int(float(PROG_BAR_H) * ( float(image_count)/float(total_imgs)))
    progress = int(float(PROG_BAR_H) * ((total_time-time_remaining)/total_time))
    PROG_BAR_FILL = ((PROG_BAR_LOC[0], PROG_BAR_LOC[1]+PROG_BAR_H-progress),
                    (PROG_BAR_LOC[0]+PROG_BAR_W,PROG_BAR_LOC[1]+PROG_BAR_H))
    disp_draw.rectangle(PROG_BAR_FILL, outline=0, fill=0)
    disp_draw.text(BIG4_2, "%04d" % (image_count), font=font_large)
    disp_draw.text(BIG4_1,"%04d" % (time_to_next), font=font_large)
    disp_draw.text(TIME_2, time.strftime("%H:%M:%S", time.gmtime(time_remaining)), font=font_small)
    disp_draw.text(TOT_IMG, "%04d" % (total_imgs), font=font_small)
    camera.disp_image(disp_image) 

#-------------------------------------------------------------------------
# Time Lapse
#-------------------------------------------------------------------------
def start_timelapse():
    total_time = delta_time * (total_imgs-1)
    print "---| Starting Time Lapse |-------------------"
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
            disp_big_msg(" TAKE ")
            filename = timelapse_name+"_%04d.jpg" % image_count
            print("[{0}/{1}]:{2}".format(image_count,total_imgs,filename))
            acquire_start = time.time() 
            camera.capture(filename)
            acquire_finish = time.time()
            acquire_time = acquire_finish - acquire_start
            # Pause
            if (image_count<total_imgs):
                print "Waiting for time to lapse."
                keep_waiting = True
                while keep_waiting:
                    time.sleep(0.250)
                    current_time = time.time()
                    time_to_next = acquire_start + delta_time - current_time
                    time_remaining = time_to_next + delta_time*(total_imgs-image_count-1) + acquire_time
                    disp_show_status(time_to_next, image_count, time_remaining)
                    if (time_to_next <= 0 ):
                        keep_waiting = False                                 
    finally:
        disp_big_msg(" DONE ")
        time.sleep(1)
    print "---| Done |----------------------------------"
    print "Time lapse complete, saved to {0}.".format(timelapse_name)
    os.chdir(root_dir)

#-------------------------------------------------------------------------
# Tornado Server Setup
#-------------------------------------------------------------------------
# camera shut down
class CameraShutDownHandler(tornado.web.RequestHandler):
    def get(self, ):
        camera.disp_msg("BYE BYE")
        print "BYE BYE"
        self.write( '<html><body>'
                    '<center><h1>BYE BYE</h1></center>'
                    '</body></html>'
                  )
        time.sleep(5)
        os.system("sudo halt") 
        exit()

# camera capture
class CameraCaptureHandler(tornado.web.RequestHandler):
    def get(self, ):
        file_name = 'test.jpg'
        camera.capture(file_name)
        buf_size = 4096
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=' + file_name)
        with open(file_name, 'r') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()
        
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
        global camera
        global total_time
        print "GET Request from {}".format(self.request.remote_ip)
        delta_time  = int(self.get_argument("D", delta_time))
        total_imgs  = int(self.get_argument("N", total_imgs))
        ISO         = int(self.get_argument("I", ISO))
        shutter     = int(self.get_argument("S", shutter))
        total_time  = delta_time * (total_imgs-1)
        camera.set_cam_config(iso=ISO, shutter_speed=shutter)
        #camera.disp_msg("DT=%g  N=%g ISO=%g s=%g" % (delta_time, total_imgs, ISO, shutter))
        disp_show_summary2()
        self.render("camera_setup.html")
        
    def post(self):
        print "POST Request from {}".format(self.request.remote_ip)
        self.write("there is no post handler")
        
# camera time lapse
class CameraTimeLapseHandler(tornado.web.RequestHandler):
    def get(self):
        #global delta_time
        #global total_imgs
        #global ISO
        #global shutter
        print "GET Request from {}".format(self.request.remote_ip)
        #camera.disp_msg("DT=%g  N=%g ISO=%g s=%g" % (delta_time, total_imgs, ISO, shutter))
        disp_show_summary()
        self.write('<html><body>'
                   '<h1>'
                   'delta_time=%g<br/>' % (delta_time) +
                   'total_imgs=%g<br/>' % (total_imgs) +
                   'total_time=%g<br/>' % (total_time) +
                   'ISO=%g<br/>' % (camera._iso) +
                   'shutter_speed=%g<br/>' % (camera._shutter_speed) +
                   '</h1>'
                   '<form method="POST"><input type="submit" value="GO"/>'
                   '</body></html>')
       
    def post(self):
        # for now, this is a blocking call
        start_timelapse()
        self.write('<html><body>'
                   '<h1>'
                   'DONE.'
                   '</h1>'
                   '</body></html>')

# separate HTTP and WebSockets based on URL
handlers = ([
    (r"/camera_setup",      CameraSetUpHandler),
    (r"/camera_timelapse",  CameraTimeLapseHandler),
    (r"/camera_preview",    CameraPreviewHandler),
    (r"/camera_capture",    CameraCaptureHandler),
    (r"/camera_ws",         CameraPreviewWebSocket),
    (r"/camera_shutdown",   CameraShutDownHandler)
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
camera.disp_msg("SERVER UP!")
tornado.ioloop.IOLoop.instance().start()
print "i guess we're done then."

