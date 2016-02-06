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
ISO = 100                                   # default ISO
shutter = 0                                 # default shutter speed
camera.set_cam_config(  resolution=(1920, 1080),
                        quality=100,
                        brightness = 50,
                        contrast = 5,
                        sharpness = 0,
                        saturation = 10,
                        awb_mode = 'auto',
                        iso=ISO,
                        shutter_speed=shutter)

# Default time lapse config
delta_time = 10                             # delta time in seconds
total_imgs = 4                           # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

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
    
def update_camera():
    camera.set_cam_config(  iso=ISO,
                            shutter_speed=shutter
                         )

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
    
    # Write info to manifest file
    with open(timelapse_name+'_info.txt','w') as f:
        f.write("%s\n" % timelapse_name)
        f.write("delta_time = %g\n" % delta_time)
        f.write("total_imgs = %g\n" % total_imgs)
        f.write("ISO = %g\n" % ISO)
        f.write("shutter = %g\n" %shutter)
    
    # Try block for image capture
    try:                
        # Main time lapse loop
        for image_count in xrange(1,total_imgs+1):
            # Take the image
            disp_big_msg(" TAKE ")
            filename = timelapse_name+"_%04d.jpg" % image_count
            #filename = timelapse_name+"_%04d.png" % image_count
            print("[{0}/{1}]:{2}".format(image_count,total_imgs,filename))
            acquire_start = time.time() 
            #camera.capture(filename)
            camera.capture_with_wait(filename)
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
        self.render("camera_shutdown.html")
        
    def post(self, ):
        BTN = self.get_argument('BTN')
        if (BTN=='POWER DOWN'):
            camera.disp_msg("BYE BYE")
            print "BYE BYE"
            self.write( '<html><body>'
                        '<center><h1>Powering down...</h1></center>'
                        '</body></html>'
                      )
            time.sleep(5)
            os.system("sudo halt") 
            exit()
        if (BTN=='STOP SERVER'):
            self.write( '<html><body>'
                        '<center><h1>Stopping server...</h1></center>'
                        '</body></html>'
                      )
            tornado.ioloop.IOLoop.instance().stop()
            
# camera capture
class CameraCaptureHandler(tornado.web.RequestHandler):
    def get(self, ):
        file_name = 'test.jpg'
        update_camera()
        #camera.capture(file_name)
        #camera.capture_with_wait(file_name)
        camera.capture_with_histogram(file_name)
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

    def post(self, ):
        BTN = self.get_argument('BTN')
        if (BTN=='SETUP'):
            self.redirect('camera_setup')
            
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
        print "GET Request from {}".format(self.request.remote_ip)
        disp_show_summary()
        kwargs = self.__build_kwargs__()
        self.render('camera_setup.html', **kwargs)
        
    def post(self):
        print "POST Request from {}".format(self.request.remote_ip)
        self.__parse_args__()
        update_camera()
        BTN = self.get_argument('BTN')
        if (BTN=='UPDATE'):
            disp_show_summary()
            kwargs = self.__build_kwargs__()
            self.render('camera_setup.html', **kwargs)
        if (BTN=='CAPT'):
            self.redirect('camera_capture')
        if (BTN=='PREV'):
            self.redirect('camera_preview')
        if (BTN=='TLAP'):
            self.redirect('camera_timelapse')
        
    def __parse_args__(self, ):
        global delta_time
        global total_imgs
        global total_time
        global ISO
        global shutter
        delta_time = int(self.get_argument('D'))
        total_imgs = int(self.get_argument('N'))
        total_time = delta_time * (total_imgs-1)
        ISO = int(self.get_argument('I'))
        shutter = int(self.get_argument('S'))
    
    def __build_kwargs__(self, ):
        kwargs = {}
        kwargs['D'] = '?' if (delta_time==None) else '%g' % delta_time
        kwargs['N'] = '?' if (total_imgs==None) else '%g' % total_imgs
        kwargs['T'] = '?' if (total_time==None) else time.strftime("%H:%M:%S", time.gmtime(total_time))
        kwargs['I_0'] = 'selected' if (ISO==0) else ''
        kwargs['I_1'] = 'selected' if (ISO==100) else ''
        kwargs['I_2'] = 'selected' if (ISO==200) else ''
        kwargs['I_3'] = 'selected' if (ISO==320) else ''
        kwargs['I_4'] = 'selected' if (ISO==400) else ''
        kwargs['I_5'] = 'selected' if (ISO==500) else ''
        kwargs['I_6'] = 'selected' if (ISO==640) else ''
        kwargs['I_7'] = 'selected' if (ISO==800) else ''
        kwargs['S_0'] = 'selected' if (shutter==0) else ''
        kwargs['S_1'] = 'selected' if (shutter==2000000) else ''
        kwargs['S_2'] = 'selected' if (shutter==1000000) else ''
        kwargs['S_3'] = 'selected' if (shutter==500000) else ''
        kwargs['S_4'] = 'selected' if (shutter==250000) else ''
        kwargs['S_5'] = 'selected' if (shutter==125000) else ''
        kwargs['S_6'] = 'selected' if (shutter==62500) else ''
        kwargs['S_7'] = 'selected' if (shutter==31250) else ''
        kwargs['S_8'] = 'selected' if (shutter==15625) else ''
        kwargs['S_9'] = 'selected' if (shutter==7813) else ''
        kwargs['S_10'] = 'selected' if (shutter==3906) else ''
        kwargs['S_11'] = 'selected' if (shutter==1953) else ''
        kwargs['S_12'] = 'selected' if (shutter==978) else ''
        kwargs['S_13'] = 'selected' if (shutter==489) else ''
        kwargs['S_14'] = 'selected' if (shutter==400) else ''
        kwargs['S_15'] = 'selected' if (shutter==350) else ''
        kwargs['S_16'] = 'selected' if (shutter==300) else ''
        kwargs['S_17'] = 'selected' if (shutter==250) else ''
        kwargs['S_18'] = 'selected' if (shutter==200) else ''
        kwargs['S_19'] = 'selected' if (shutter==150) else ''
        kwargs['S_20'] = 'selected' if (shutter==100) else ''
        return kwargs
    
# camera time lapse
class CameraTimeLapseHandler(tornado.web.RequestHandler):
    def get(self):
        print "GET Request from {}".format(self.request.remote_ip)
        disp_show_summary()
        kwargs = self.__build_kwargs__()
        self.render('camera_timelapse.html', **kwargs)
  
    def __build_kwargs__(self, ):
        kwargs = {}
        kwargs['D'] = '?' if (delta_time==None) else '%g' % delta_time
        kwargs['N'] = '?' if (total_imgs==None) else '%g' % total_imgs
        kwargs['T'] = '?' if (total_time==None) else time.strftime("%H:%M:%S", time.gmtime(total_time)) 
        kwargs['I'] = ISO
        kwargs['S'] = shutter
        return kwargs
        
    def post(self):
        # for now, this is a blocking call
        start_timelapse()
        self.write('<html><body>'
                   '<h1>'
                   'DONE.'
                   '</h1>'
                   '</body></html>')
       
# map URLs to handlers
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
disp_big_msg("  UP  ")
tornado.ioloop.IOLoop.instance().start()
disp_big_msg("STOPPD")
print "i guess we're done then."

