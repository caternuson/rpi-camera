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
import picamera
import time
import os

# Hardwire some values
T   = 60         # total time in seconds
dt  = 10         # delta time in seconds
N   = T /dt      # total number of frames

print "{0} images every {1} seconds.".format(N, dt)
print "Total time to acquire {0}".format(time.strftime("%H:%M:%S",time.gmtime(T)))
s = raw_input("Continue? ")
if (s.upper() != 'Y'):
    exit()
    
tl_name = time.strftime("%Y%m%d_%H%M",time.localtime())
os.mkdir(tl_name)
os.chdir(tl_name)

def get_time_str():
    return time.strftime("%H:%M:%S", time.gmtime(time.time()))

#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
print "{0} starting".format(get_time_str())

with picamera.PiCamera() as camera:
    print "{0} setting camera config".format(get_time_str())
    camera.resolution = (2592,1944)   # 2592 x 1944 max
    camera.vflip = True
    camera.hflip = True
    #camera.start_preview()
    #time.sleep(2)
    try:
        print "{0} starting loop".format(get_time_str())
        for i, filename in enumerate(camera.capture_continuous(tl_name+'_{counter:04d}.jpg',quality=100)):
            frame = i+1
            print "{3} [{0}/{1}]:{2}".format(frame,N,filename,get_time_str()) 
            if (frame==N):
                break
            print "{0} sleeping".format(get_time_str())
            time.sleep(dt)
            print "{0} taking next image".format(get_time_str())
    finally:
        pass
        #camera.stop_preview()

print "{0} done".format(get_time_str())