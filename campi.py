#!/usr/bin/env python
#===========================================================================
# campi.py
#
# Python class to represent RPi based camera.
# There are three main chunks of hardware:
#   * camera = rpi camera module
#   * display = Nokia LCD
#   * buttons = a 5 way navigation switch w/ common ground
#
# 2014-10-30
# Carter Nelson
#===========================================================================
import io
import os
import time
from fractions import Fraction

import Image
import ImageDraw
import ImageFont

import RPi.GPIO as GPIO
import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

from picamera import PiCamera

# GPIO pins for 5 way navigation switch
BTN_UP              =   19      # Up
BTN_DOWN            =   16      # Down
BTN_LEFT            =   26      # Left
BTN_RIGHT           =   20      # Right
BTN_SEL             =   21      # Select (push)
BUTTONS = [BTN_UP, BTN_DOWN, BTN_LEFT, BTN_RIGHT, BTN_SEL]

# GPIO pins for Nokia LCD display control
LCD_DC              =   23      # Nokia LCD display D/C
LCD_RST             =   24      # Nokia LCD displat Reset
LCD_SPI_PORT        =   0       # Hardware SPI port to use
LCD_SPI_DEVICE      =   0       # Hardware SPI device (determines chip select pin used)
LCD_LED             =   22      # LCD LED enable pin (HIGH=ON, LOW=OFF)
LCD_CONTRAST        =   50      # LCD contrast 0-100

# Load fonts
FONT_SMALL = ImageFont.load_default()
FONT_LARGE = ImageFont.truetype("5Identification-Mono.ttf",12)

# Image draw buffer for writing to LCD display
LCD_IMAGE = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
LCD_DRAW  = ImageDraw.Draw(LCD_IMAGE)

# Display locations
WHOLE_SCREEN    = ((0,0),(LCD.LCDWIDTH, LCD.LCDHEIGHT))
BIG_MSG         = (0,12)         

class Campi():
    '''A class to provide an interface to the campi hardware.'''
        
    def __init__(self):
        '''Constructor.'''
        self.settings = {}
        self.settings['sensor_mode'] = 0               # 0 (auto), 2 (1-15fps), 3 (0.1666-1fps) (see doc)
        self.settings['resolution'] = (2592,1944)      # full resolution 2592 x 1944
        self.settings['iso'] = 0                       # 0 (auto), 100, 200, 320, 400, 500, 640, 800
        self.settings['shutter_speed'] = 0             # 0 (auto), value in microseconds
        self.settings['framerate'] = Fraction(30,1)    # NOTE: this limits max shutter speed
        self.settings['brightness'] = 50               # 0 - 100 (50)
        self.settings['contrast'] = 0                  # -100 - 100 (0)
        self.settings['sharpness'] = 0                 # -100 - 100 (0)
        self.settings['saturation'] = 0                # -100 - 100 (0)
        self.settings['awb_mode'] = 'auto'             # white balance mode (see doc)
        self.settings['exposure_mode'] = 'auto'        # exposure mode (see doc)
        self.settings['hvflip'] = (True, True)         # horizontal/vertical flip
        self.settings['quality'] = 100                 # 0 - 100, applies only to JPGs
        self.settings['awb_gains'] = None
 
        self._disp = LCD.PCD8544(LCD_DC,
                                 LCD_RST,
                                 spi=SPI.SpiDev(LCD_SPI_PORT,
                                                LCD_SPI_DEVICE,
                                                max_speed_hz=4000000)
                                 )
        self._disp.begin(contrast=LCD_CONTRAST)
        self._disp.clear()
        self._disp.display()
        
        self._gpio = GPIO
        self._gpio.setwarnings(False)
        self._gpio.setmode(GPIO.BCM)
        for B in BUTTONS:
            GPIO.setup(B, GPIO.IN , pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LCD_LED, GPIO.OUT, initial=GPIO.LOW)
  
    #---------------------------------------------------------------
    #                   C  A  M  E  R  A
    #---------------------------------------------------------------        
    def capture(self, filename):
        '''Capture an image using current settings and save to the specified
        filename.
        '''
        with PiCamera(sensor_mode=self.settings['sensor_mode']) as camera:
            camera = self.__update_camera(camera=camera)
            camera.capture(filename, quality=self.settings['quality'])
            self.__update_settings(camera)
                                                                   
    def capture_stream(self, ios=None, size=(400,225)):
        '''Capture an image to the specified IO stream. Image size can
        also be specified.'''
        if ios == None:
            return
        with PiCamera(sensor_mode=5) as camera:
            camera = self.__update_camera(camera=camera, use_video_port=True)
            camera.capture(ios, 'jpeg', use_video_port=True, resize=size)
            
    def capture_with_histogram(self, filename, fill=False):
        '''Capture an image with histogram overlay and save to specified file.
        If fill=True, the area under the histogram curves will be filled.
        '''
        # capture then open in PIL image
        hname = 'hist_' + time.strftime("%H%M%S", time.localtime()) + '.jpg'
        self.capture(hname)
        im_in   = Image.open(hname)
        im_out  = Image.new('RGBA', im_in.size)
        im_out.paste(im_in)
        width, height = im_in.size
        draw = ImageDraw.Draw(im_out)

        # add rule of thirds lines
        x1 = width/3
        x2 = 2*x1
        y1 = height/3
        y2 = 2*y1
        draw.line([(x1,0),(x1,height)], width=3)
        draw.line([(x2,0),(x2,height)], width=3)
        draw.line([(0,y1),(width,y1)], width=3)
        draw.line([(0,y2),(width,y2)], width=3)
        
        # compute histogram, scaled for image size
        hist = im_in.histogram()
        rh = hist[0:256]
        gh = hist[256:512]
        bh = hist[512:768]
        xs = float(width)/float(256)
        ys = float(height)/float(max(hist))
        rl=[]
        gl=[]
        bl=[]
        for i in xrange(256):
            rl.append((int(i*xs),height-int(rh[i]*ys)))
            gl.append((int(i*xs),height-int(gh[i]*ys)))
            bl.append((int(i*xs),height-int(bh[i]*ys)))        
        
        # draw it
        lw = max(5,int((0.005*max(im_out.size))))
        if (fill):
            rpoly = [(0,height)] + rl + [(width,height)]
            gpoly = [(0,height)] + gl + [(width,height)]
            bpoly = [(0,height)] + bl + [(width,height)]
            draw.polygon(rpoly, fill=(255,0,0,90))
            draw.polygon(gpoly, fill=(0,255,0,90))
            draw.polygon(bpoly, fill=(0,0,255,90))
        draw.line(rl, fill='red', width=lw)
        draw.line(gl, fill='green', width=lw)
        draw.line(bl, fill='blue', width=lw)
        
        # add image info
        font = ImageFont.truetype("5Identification-Mono.ttf",72)
        fw,fh = font.getsize(" ")
        lines = []
        lines.append("MODE %s" % self.settings['exposure_mode'])
        lines.append("SPEED %f" % (self.settings['exposure_speed'] / 1.e6))
        lines.append("ISO %d" % self.settings['iso'])
        N = 0
        for line in lines:
            draw.text((10,10+N*fh), line, font=font)
            N += 1

        # save it and clean up 
        im_out.save(filename, quality=95)
        os.remove(hname)
        
    def set_cam_config(self, setting=None, value=None):
        '''Set the specified camera setting to the supplied value.'''
        if value == None:
            return
        if setting not in self.settings:
            return
        if "shutter_speed" == setting:
            self.__set_shutter_speed(value)
            return
        if "framerate" == setting:
            self.__set_framerate(value)
            return
        self.settings[setting] = value
        
    def __set_shutter_speed(self, value=None):
        '''Setting shutter speed manually requires some effort. The acceptable
        values are limited by the sensor_mode and frame_rate. Here, those values
        are altered as needed to support the specified shutter speed.
        '''
        if value == None:
            return
        if value != 0:
            # force settings to support non-zero (non-auto) shutter_speed
            self.settings['exposure_mode'] = 'off'      # shutter speed ignored otherwise
            if value > 6000000:                         # global max is 6 secs
                value = 6000000
            if value > 1000000:                         # sensor mode 2 or 3 for stills
                self.settings['sensor_mode'] = 3        # 6 secs max (0.1666-1fps)
                self.settings['framerate'] = min(Fraction(1),Fraction(1.e6/value))
            else:
                self.settings['sensor_mode'] = 2        # 1 sec max (1-15fps)
                self.settings['framerate'] = min(Fraction(15),Fraction(1.e6/value))
            self.settings['shutter_speed'] = value      # and finally, set shutter speed
        else:
            # auto mode
            self.settings['sensor_mode'] = 0
            self.settings['exposure_mode'] = 'auto'
            self.settings['shutter_speed'] = value
            
    def __set_framerate(self, value=None):
        '''Framerate is tied to shutter_speed. Priority is given to shutter
        speed if in manual mode.
        '''
        if self.settings['shutter_speed'] != 0:
            # force framerate to a value that will support shutter_speed
            self.settings['framerate'] = Fraction(1.e6/self.settings['shutter_speed'])
        else:
            # auto mode, so just set it
            self.settings['framerate'] = value 
            
    def __update_camera(self, camera=None, use_video_port=False):
        '''Update the Raspberry Pi Camera Module with the current settings.
        Basically a mapping of this class's member variables to the ones used
        by the picamera module.
        '''
        if not isinstance(camera, PiCamera):
            return
        #---[from http://picamera.readthedocs.io]--
        # At the time of writing, setting this property does nothing unless the
        # camera has been initialized with a sensor mode other than 0.
        # Furthermore, some mode transitions appear to require setting the
        # property twice (in a row). This appears to be a firmware limitation.
        #---
        '''
        camera.sensor_mode = self.settings['sensor_mode']
        '''
        camera.framerate = self.settings['framerate']             # set this before shutter_speed
        camera.exposure_mode = self.settings['exposure_mode']     # set this before shutter_speed
        camera.resolution = self.settings['resolution']
        camera.iso =  self.settings['iso']
        camera.awb_mode = self.settings['awb_mode']
        camera.shutter_speed = self.settings['shutter_speed']
        camera.brightness = self.settings['brightness']
        camera.constrast = self.settings['contrast']
        camera.sharpness = self.settings['sharpness']
        camera.saturation = self.settings['saturation']
        camera.hflip = self.settings['hvflip'][0]
        camera.vflip = self.settings['hvflip'][1]
        if use_video_port:
            camera.framerate = Fraction(30,1)
            camera.exposure_mode = 'auto'
        return camera
    
    def __update_settings(self, camera=None):
        '''Update dictionary of settings with actual values from supplied
        camera object.'''
        if not isinstance(camera, PiCamera):
            return
        self.settings['sensor_mode'] = camera.sensor_mode
        self.settings['framerate'] = camera.framerate
        self.settings['exposure_mode'] = camera.exposure_mode
        self.settings['resolution'] = camera.resolution
        self.settings['iso'] = camera.iso
        self.settings['awb_mode'] = camera.awb_mode
        self.settings['shutter_speed'] = camera.shutter_speed
        self.settings['exposure_speed'] = camera.exposure_speed
        self.settings['brightness'] = camera.brightness
        self.settings['contrast'] = camera.contrast
        self.settings['sharpness'] = camera.sharpness
        self.settings['saturation'] = camera.saturation
        self.settings['hvflip'] = (camera.hflip,camera.vflip)            
    
    #---------------------------------------------------------------
    #                  D  I  S  P  L  A  Y
    #---------------------------------------------------------------
    def LCD_LED_On(self):
        '''Enable power to LCD display.'''
        self._gpio.output(LCD_LED, GPIO.HIGH)
        
    def LCD_LED_Off(self):
        '''Disable power to LCD display.'''
        self._gpio.output(LCD_LED, GPIO.LOW)
        
    def disp_clear(self):
        '''Clear the display.'''
        self._disp.clear()
        self._disp.display()
    
    def disp_image(self, image):
        '''Display the supplied image.'''
        self._disp.image(image)
        self._disp.display()
        
    def get_lcd_size(self):
        '''Return the width and height of the LCD screen as a tuple.'''
        return (LCD.LCDWIDTH, LCD.LCDHEIGHT)
    
    def disp_msg(self, msg, font=FONT_SMALL):
        '''Display the supplied message on the screen. An optional
        font can be supplied.
        '''
        fw,fh = font.getsize(" ")    # font width and height
        cx = LCD.LCDWIDTH / fw       # max characters per line
        cy = LCD.LCDHEIGHT / fh      # max number of lines

        lines = [ msg[i:i+cx] for i in range(0, len(msg), cx) ]
        
        LCD_DRAW.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        y = 0
        for line in lines:
            LCD_DRAW.text((0,y), line, font=FONT_SMALL)
            y += fh
        self.disp_image(LCD_IMAGE)
        
    def disp_big_msg(self, msg, location=BIG_MSG):
        '''Display the supplied message on the screen using large text.
        An optional location can be specified.
        '''
        LCD_DRAW.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        LCD_DRAW.text(location, msg, font=FONT_LARGE)
        self.disp_image(LCD_IMAGE)
               
    #---------------------------------------------------------------
    #                  B  U  T  T  O  N  S
    #---------------------------------------------------------------
    def __get_raw_button(self, btn=None):
        '''Return the state of all buttons or specified button.'''
        if (btn==None):
            return (self._gpio.input(BTN_UP),
                    self._gpio.input(BTN_DOWN),
                    self._gpio.input(BTN_LEFT),
                    self._gpio.input(BTN_RIGHT),
                    self._gpio.input(BTN_SEL))     
        elif (btn in BUTTONS):
            return self._gpio.input(btn)
        else:
            return None
            
    def is_pressed(self, btn=None):
        '''Return True if specified button is pressed. False otherwise.'''
        if (btn in BUTTONS):
            if (self.__get_raw_button(btn)==0):
                return True
            else:
                return False
        else:
            return None
        
    def get_buttons(self, ):
        '''Return a dictionary of button state.'''
        state = {}
        for B in BUTTONS:
            state[B] = self.is_pressed(B)
        return state
   
#--------------------------------------------------------------------
# M A I N 
#--------------------------------------------------------------------
if __name__ == '__main__':
    print "I'm just a class, nothing to do..."