#!/usr/bin/python
#===========================================================================
# camera_timelapse.py
#
# Time lapse camera app.
#
# Uses the "5 Identification Mono" font created by:
#       http://winty5.wix.com/noahtheawesome
#       Note of the author:
#       Free for personal and commercial uses
#
# 2014-10-30
# Carter Nelson
#===========================================================================
import campi
import time
import Image
import ImageDraw
import ImageFont
import os

# Contstants
DEBOUNCE = 0.05                 # simple software debounce timing
MIN_DELTA_TIME = 0              # minimum time in seconds between images
MIN_IMGS = 0                    # mimumum number of images (1 is pretty stupid)

# Root directory where app was launched
root_dir = os.getcwd()

# Camera setup
camera = campi.Campi()
resolution = (1920, 1080)                   # resolution of images
jpeg_quality = 100                          # jpeg image quality
camera.set_cam_config(resolution=resolution,quality=jpeg_quality)

# Default time lapse config
delta_time = 10                             # delta time in seconds
total_imgs = 4                              # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

# List of buttons and dictionary of state
buttons = [campi.BTN_UP,
           campi.BTN_DOWN,
           campi.BTN_LEFT,
           campi.BTN_RIGHT,
           campi.BTN_SEL]
button_state = {}
button_pressed = False

# Load fonts
font_small = ImageFont.load_default()
font_large = ImageFont.truetype("5Identification-Mono.ttf",12)

# Image draw buffer for writing to LCD display
disp_image = Image.new('1', camera.get_lcd_size())
disp_draw  = ImageDraw.Draw(disp_image)

# Display locations
BIG4_1          = (31,0)
BIG4_2          = (31,18)
BIG_MSG         = (0,12)         
BIG4_1_LABEL    = (4,5)
BIG4_2_LABEL    = (4,23)
TIME_1          = (4,36)
TIME_2          = (2,36)
TOT_IMG         = (60,36)
WHOLE_SCREEN    = ((0,0),camera.get_lcd_size())
OK_CONFIRM      = (4,14)
PROG_BAR_H      = 31
PROG_BAR_W      = 14
PROG_BAR_LOC    = (8,4)
PROG_BAR_BOX    = (PROG_BAR_LOC,(PROG_BAR_LOC[0]+PROG_BAR_W,PROG_BAR_LOC[1]+PROG_BAR_H))


def disp_big_msg(msg, location=BIG_MSG):
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


#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
disp_show_config()
print "="*25
print "Time lapse app started."
print "="*25
while True:    
    # Read buttons
    button_state = camera.get_buttons()
    
    # Up/Down buttons for total images and delta time   
    if (button_state[campi.BTN_UP]):
        total_imgs += 1
        button_pressed = True
    if (button_state[campi.BTN_DOWN]):
        total_imgs -= 1
        button_pressed = True
    if (button_state[campi.BTN_RIGHT]):
        delta_time += 1
        button_pressed = True
    if (button_state[campi.BTN_LEFT]):
        delta_time -= 1
        button_pressed = True
              
    # Sanity check values
    delta_time = delta_time if (delta_time>MIN_DELTA_TIME) else MIN_DELTA_TIME
    total_imgs = total_imgs if (total_imgs>MIN_IMGS) else MIN_IMGS
    
    # Compute total time for time lapse
    total_time = delta_time * (total_imgs-1)
    
    # Update display if needed
    if (button_pressed):
        disp_show_config()
        button_pressed = False
        
    # Time lapse start button
    if (button_state[campi.BTN_SEL]):
        
        # Display summary
        disp_show_summary()
        
        # Ask for verification
        print "Start new timelapse?"
        # Prevent hair trigger on verify button
        time.sleep(10*DEBOUNCE)
        while True:
            button_state = camera.get_buttons()
            if (button_state[campi.BTN_SEL]):
                start_timelapse = True
                break
            if (button_state[campi.BTN_UP] or
                button_state[campi.BTN_DOWN] or
                button_state[campi.BTN_LEFT] or
                button_state[campi.BTN_RIGHT]):
                start_timelapse = False
                break
            time.sleep(DEBOUNCE)
                
        if start_timelapse:
            
            # Exit app if delta_time and total_imgs=0
            if (delta_time==0) and (total_imgs==0):
                print "Exiting app...Bye"
                disp_big_msg(" BYE  ")
                exit()
            
            # Camera setup takes a while, so provide a wait message 
            print "OK."  
            disp_big_msg("  OK  ")
            
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
            
            # Slight pause before first image
            time.sleep(1)
            
            # Mark the time                  
            start_time  = time.time()
            finish_time = start_time + total_time
            
            # Try block for image capture
            try:                
                # Main time lapse loop
                for image_count in xrange(1,total_imgs+1):
                    # Take the image
                    print "Taking next image."
                    disp_big_msg(" TAKE ")
                    filename = timelapse_name+"_%04d.jpg" % image_count
                    acquire_start = time.time()
                    camera.capture(filename)
                    acquire_finish = time.time()
                    acquire_time = acquire_finish - acquire_start
                    # Pause
                    print "[{0}/{1}]:{2}  DT={3}".format(image_count,total_imgs,filename,acquire_time)
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
            print "Time lapse complete, saved to {0}.".format(timelapse_name)
            os.chdir(root_dir)
        else:
            # Cancel time lapse
            print "CANCEL."
        disp_show_config()
    time.sleep(DEBOUNCE)
