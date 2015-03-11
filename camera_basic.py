#!/usr/bin/python
#===========================================================================
# camera_basic.py
#
# Basic camera app, based on recipe found here:
#   http://picamera.readthedocs.org/en/release-1.8/recipes1.html#capturing-timelapse-sequences
#
# It appears to work fine in a headless setup without using start_preview()
# and waiting 2 seconds.
#
# 2014-10-29
# Carter Nelson
#===========================================================================
import campi
import time
import datetime
import os

# Root directory where app was launched
root_dir = os.getcwd()

# Camera setup
camera = campi.Campi()
resolution = (1920, 1080)                   # resolution of images
jpeg_quality = 100                          # jpeg image quality
iso = 100                                   # ISO 100, 200, 320, 400, 500, 640, 800
shutter_speed = 4000                        # shutter speed in microseconds
camera.set_cam_config(resolution=resolution,quality=jpeg_quality)

# Default time lapse config
delta_time = 15                             # delta time in seconds
total_imgs = 600                          # total number of images
total_time = delta_time * (total_imgs-1)    # total time in seconds

#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
# Show stats and prompt for start
print "{0} images every {1} seconds.".format(total_imgs, delta_time)
print "Total time to acquire {0}".format(time.strftime("%H:%M:%S",time.gmtime(total_time)))
print "Current time {0}".format(time.strftime("%H:%M:%S",time.gmtime(time.time())))
print "Finish time {0}".format(time.strftime("%H:%M:%S",time.gmtime(time.time()+total_time)))
s = raw_input("Continue? ")
if (s.upper() != 'Y'):
    exit()

# Create directory for files and go there
timelapse_name = time.strftime("%Y%m%d_%H%M",time.localtime())
os.mkdir(timelapse_name)
os.chdir(timelapse_name)

# Slight pause before first image
time.sleep(1)

print "{0} starting".format(time.strftime("%H:%M:%S",time.gmtime(time.time())))

# Mark the time                  
start_time  = time.time()
finish_time = start_time + total_time
time_remaining = finish_time - start_time

# Try block for image capture
try:                
    # Main time lapse loop
    for image_count in xrange(1,total_imgs+1):
        # Take the image
        #print "Taking next image."
        filename = timelapse_name+"_%04d.jpg" % image_count
        acquire_start = time.time()
        camera.capture(filename)
        acquire_finish = time.time()
        acquire_time = acquire_finish - acquire_start
        # Pause
        print "[{0}/{1}]:{2}  remaining={3}".format(
            image_count,
            total_imgs,
            filename,
            datetime.timedelta(seconds=time_remaining)
            )
        if (image_count<total_imgs):
            #print "Waiting for time to lapse."
            keep_waiting = True
            while keep_waiting:
                time.sleep(0.250)
                current_time = time.time()
                time_to_next = acquire_start + delta_time - current_time
                time_remaining = time_to_next + delta_time*(total_imgs-image_count-1) + acquire_time
                if (time_to_next <= 0 ):
                    keep_waiting = False
                     
finally:
    time.sleep(1)
    
print "Time lapse complete, saved to {0}.".format(timelapse_name)
os.chdir(root_dir)
            