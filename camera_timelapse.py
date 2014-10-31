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
import rpi_camera
import time
import Image
import ImageDraw
import ImageFont
import os

# Contstants
DEBOUNCE = 0.05                 # simple software debounce timing
MIN_DELTA_TIME = 5              # minimum time in seconds between images
MIN_IMGS = 1                    # mimumum number of images (1 is pretty stupid)

# Root directory where app was launched
root_dir = os.getcwd()

# Camera setup
camera = rpi_camera.RpiCamera()
resolution = (1920, 1080)                   # resolution of images
jpeg_quality = 100                          # jpeg image quality
camera.get_camera().resolution = resolution

# Default time lapse config
delta_time = 10                             # delta time in seconds
total_imgs = 3                            # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

# List of buttons and dictionary of state
buttons = [rpi_camera.BTN_1,
           rpi_camera.BTN_2,
           rpi_camera.BTN_3,
           rpi_camera.BTN_4,
           rpi_camera.BTN_5]
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

#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
disp_show_config()
print "="*25
print "Time lapse app started."
print "="*25
while True:    
    # Read buttons
    for button in buttons:
        button_state[button] = camera.get_button(button)
    
    # Up/Down buttons for total images and delta time   
    if (button_state[rpi_camera.BTN_2]):
        total_imgs += 1
        button_pressed = True
    if (button_state[rpi_camera.BTN_3]):
        total_imgs -= 1
        button_pressed = True
    if (button_state[rpi_camera.BTN_4]):
        delta_time += 1
        button_pressed = True
    if (button_state[rpi_camera.BTN_5]):
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
    if (button_state[rpi_camera.BTN_1]):
        
        # Display summary
        disp_show_summary()
        
        # Ask for verification
        print "Start new timelapse?",
        time.sleep(2*DEBOUNCE)
        while True:
            for button in buttons:
                button_state[button] = camera.get_button(button)
            if (button_state[rpi_camera.BTN_1]):
                start_timelapse = True
                break
            if (button_state[rpi_camera.BTN_2] or
                button_state[rpi_camera.BTN_3] or
                button_state[rpi_camera.BTN_4] or
                button_state[rpi_camera.BTN_5]):
                start_timelapse = False
                break
            time.sleep(DEBOUNCE)
                
        if start_timelapse:
            
            # Camera setup takes a while, so provide a wait message 
            print "OK."  
            disp_big_msg(" WAIT ")

            # Create directory for files and go there
            timelapse_name = time.strftime("%Y%m%d_%H%M",time.localtime())
            os.mkdir(timelapse_name)
            os.chdir(timelapse_name)
                        
            # Configure camera
            # moved this to global setup
            '''
            print "Camera configure."
            camera.get_camera().resolution = resolution
            '''
            
            # Warm up camera
            # IS THIS NEEDED? removed for now
            '''
            camera.get_camera().start_preview()
            print "Camera warm up."
            time.sleep(2)
            print "Warm up complete."
            '''
            
            start_time  = time.time()
            finish_time = start_time + total_time
            # Try block for image capture
            try:
                disp_big_msg(" TAKE ")
                print("TAKE")
                acquire_start = time.time()
                # Main time lapse loop
                for i, filename in enumerate(camera.get_camera().capture_continuous(timelapse_name+'_{counter:04d}.jpg',quality=jpeg_quality)):
                    acquire_finish = time.time()
                    acquire_time = acquire_finish - acquire_start
                    frame = i+1
                    print "[{0}/{1}]:{2}  DT={3}".format(frame,total_imgs,filename,acquire_time)
                    
                    # Stop when all images acquired
                    if (frame==total_imgs):
                        break
                    
                    # Update display while waiting for time to lapse
                    time_to_next = delta_time - acquire_time
                    print "Waiting for time to lapse."
                    while (time_to_next>0):
                        current_time = time.time()
                        time_to_next = acquire_start + delta_time - current_time
                        remaining_time = time_to_next + delta_time*(total_imgs-frame-1) + acquire_time
                        disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
                        # number of images taken so far
                        disp_draw.text(BIG4_2, "%04d" % (frame), font=font_large)
                        # seconds until next image
                        disp_draw.text(BIG4_1,"%04d" % (time_to_next), font=font_large)
                        # total time remaining for time lapse
                        disp_draw.text(TIME_2, time.strftime("%H:%M:%S", time.gmtime(remaining_time)), font=font_small)
                        # total images to be taken
                        disp_draw.text(TOT_IMG, "%04d" % (total_imgs))
                        # write to display
                        camera.disp_image(disp_image)
                        # sleep a bit to free up CPU
                        time.sleep(0.250)
                                            
                    print "Taking next image."
                    disp_big_msg(" TAKE ")
                    acquire_start = time.time()
            finally:
                # camera.get_camera().stop_preview()
                disp_big_msg(" DONE ")
                time.sleep(1)
            print "Time lapse complete, saved to {0}.".format(timelapse_name)
            os.chdir(root_dir)
        else:
            # Cancel time lapse
            print "CANCEL."
        disp_show_config()
    time.sleep(DEBOUNCE)
