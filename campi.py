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
# Uses the "5 Identification Mono" font created by:
#       http://winty5.wix.com/noahtheawesome
#       Note of the author:
#       Free for personal and commercial uses
#
# 2014-10-30
# Carter Nelson
#===========================================================================
import io
import os
import time
from fractions import Fraction

from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import board
import busio
from digitalio import DigitalInOut, Direction, Pull
import adafruit_pcd8544 as LCD

from picamera import PiCamera
import mjpegger

SPI = busio.SPI(board.SCK, MOSI=board.MOSI)

# GPIO pins for 5 way navigation switch
BTN_UP              =   board.D19      # Up
BTN_DOWN            =   board.D16      # Down
BTN_LEFT            =   board.D26      # Left
BTN_RIGHT           =   board.D20      # Right
BTN_SEL             =   board.D21      # Select (push)

# GPIO pins for Nokia LCD display control
LCD_DC              =   board.D23      # Nokia LCD display D/C
LCD_CS              =   board.D8       # Nokia LCD display CS
LCD_RST             =   board.D24      # Nokia LCD displat Reset
LCD_LED             =   board.D22      # LCD LED enable pin (HIGH=ON, LOW=OFF)
LCD_CONTRAST        =   50      # LCD contrast 0-100

# Load fonts
FONT_SMALL = ImageFont.load_default()
FONT_LARGE = ImageFont.truetype("5Identification-Mono.ttf",12)

# Image draw buffer for writing to LCD display
LCD_IMAGE = Image.new('1', (LCD._LCDWIDTH, LCD._LCDHEIGHT))
LCD_DRAW  = ImageDraw.Draw(LCD_IMAGE)

# Display locations
WHOLE_SCREEN    = ((0,0),(LCD._LCDWIDTH, LCD._LCDHEIGHT))
BIG_MSG         = (0,12)

class Campi():
    """A class to provide an interface to the campi hardware."""

    def __init__(self):
        """Constructor."""
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

        self._disp = LCD.PCD8544( SPI,
                                  DigitalInOut(LCD_DC),
                                  DigitalInOut(LCD_CS),
                                  DigitalInOut(LCD_RST) )
        self._disp.invert = True
        self._disp.contrast = 50
        self._lcd_led = DigitalInOut(LCD_LED)
        self._lcd_led.direction = Direction.OUTPUT
        self._lcd_led.value = False

        self._mjpegger = None

        self._button_up = DigitalInOut(BTN_UP)
        self._button_down = DigitalInOut(BTN_DOWN)
        self._button_left = DigitalInOut(BTN_LEFT)
        self._button_right = DigitalInOut(BTN_RIGHT)
        self._button_sel = DigitalInOut(BTN_SEL)
        self._buttons = [ self._button_up,
                          self._button_down,
                          self._button_left,
                          self._button_right,
                          self._button_sel   ]
        for button in self._buttons:
            button.direction = Direction.INPUT
            button.pull = Pull.UP

    #---------------------------------------------------------------
    #                   C  A  M  E  R  A
    #---------------------------------------------------------------
    def capture(self, filename):
        """Capture an image using current settings and save to the specified
        filename.
        """
        with PiCamera(sensor_mode=self.settings['sensor_mode']) as camera:
            camera = self.__update_camera(camera=camera)
            camera.capture(filename, quality=self.settings['quality'])
            self.__update_settings(camera)

    def capture_stream(self, ios=None, size=(400,225)):
        """Capture an image to the specified IO stream. Image size can
        also be specified."""
        if ios == None:
            return
        with PiCamera(sensor_mode=5) as camera:
            camera = self.__update_camera(camera=camera, use_video_port=True)
            camera.capture(ios, 'jpeg', use_video_port=True, resize=size)

    def mjpegstream_start(self, port=8081, resize=(640,360)):
        """Start thread to serve MJPEG stream on specified port."""
        if not self._mjpegger == None:
            return
        camera = self.__update_camera(camera=PiCamera(sensor_mode=5))
        kwargs = {'camera':camera, 'port':port, 'resize':resize}
        self._mjpegger = mjpegger.MJPEGThread(kwargs=kwargs)
        self._mjpegger.start()
        while not self._mjpegger.streamRunning:
            pass

    def mjpegstream_stop(self, ):
        """Stop the MJPEG stream, if running."""
        if not self._mjpegger == None:
            if self._mjpegger.is_alive():
                self._mjpegger.stop()
            self._mjpegger = None

    def mjpgstream_is_alive(self, ):
        """Return True if stream is running, False otherwise."""
        if self._mjpegger == None:
            return False
        else:
            return self._mjpegger.is_alive()

    def capture_with_histogram(self, filename, fill=False):
        """Capture an image with histogram overlay and save to specified file.
        If fill=True, the area under the histogram curves will be filled.
        """
        # capture then open in PIL image
        hname = 'hist_' + time.strftime("%H%M%S", time.localtime()) + '.jpg'
        self.capture(hname)
        im_in   = Image.open(hname)
        im_out  = Image.new('RGBA', im_in.size)
        im_out.paste(im_in)
        width, height = im_out.size
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
        for i in range(256):
            rl.append((int(i*xs),height-int(rh[i]*ys)))
            gl.append((int(i*xs),height-int(gh[i]*ys)))
            bl.append((int(i*xs),height-int(bh[i]*ys)))

        # draw it
        lw = int((0.01*max(im_out.size)))
        if (fill):
            rpoly = [(0,height)] + rl + [(width,height)]
            gpoly = [(0,height)] + gl + [(width,height)]
            bpoly = [(0,height)] + bl + [(width,height)]
            draw.polygon(rpoly, fill=(255,0,0,40))
            draw.polygon(gpoly, fill=(0,255,0,40))
            draw.polygon(bpoly, fill=(0,0,255,40))
        draw.line(rl, fill='red', width=lw)
        draw.line(gl, fill='green', width=lw)
        draw.line(bl, fill='blue', width=lw)

        # add image info
        font = ImageFont.truetype("5Identification-Mono.ttf",72)
        fw,fh = font.getsize(" ")
        lines = []
        lines.append("EXP MODE %s" % self.settings['exposure_mode'])
        if self.settings['iso'] == 0:
            lines.append("ISO AUTO")
        else:
            lines.append("ISO %d" % self.settings['iso'])
        lines.append("SPEED %f" % (self.settings['exposure_speed'] / 1.e6))
        lines.append("AWB %s" % self.settings['awb_mode'])
        N = 0
        for line in lines:
            draw.text((10,10+N*fh), line, font=font)
            N += 1

        # save it and clean up
        im_out.convert(mode="RGB").save(filename, quality=95)
        os.remove(hname)

    def set_cam_config(self, setting=None, value=None):
        """Set the specified camera setting to the supplied value."""
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
        """Setting shutter speed manually requires some effort. The acceptable
        values are limited by the sensor_mode and frame_rate. Here, those values
        are altered as needed to support the specified shutter speed.
        """
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
        """Framerate is tied to shutter_speed. Priority is given to shutter
        speed if in manual mode.
        """
        if self.settings['shutter_speed'] != 0:
            # force framerate to a value that will support shutter_speed
            self.settings['framerate'] = Fraction(1.e6/self.settings['shutter_speed'])
        else:
            # auto mode, so just set it
            self.settings['framerate'] = value

    def __update_camera(self, camera=None, use_video_port=False):
        """Update the Raspberry Pi Camera Module with the current settings.
        Basically a mapping of this class's member variables to the ones used
        by the picamera module.
        """
        if not isinstance(camera, PiCamera):
            return
        #---[from http://picamera.readthedocs.io]--
        # At the time of writing, setting this property does nothing unless the
        # camera has been initialized with a sensor mode other than 0.
        # Furthermore, some mode transitions appear to require setting the
        # property twice (in a row). This appears to be a firmware limitation.
        #
        """
        camera.sensor_mode = self.settings['sensor_mode']
        """
        #---
        camera.framerate = self.settings['framerate']             # set this before shutter_speed
        camera.exposure_mode = self.settings['exposure_mode']     # set this before shutter_speed
        camera.resolution = self.settings['resolution']
        camera.iso =  self.settings['iso']
        camera.awb_mode = self.settings['awb_mode']
        camera.shutter_speed = self.settings['shutter_speed']
        camera.brightness = self.settings['brightness']
        camera.contrast = self.settings['contrast']
        camera.sharpness = self.settings['sharpness']
        camera.saturation = self.settings['saturation']
        camera.hflip = self.settings['hvflip'][0]
        camera.vflip = self.settings['hvflip'][1]
        if use_video_port:
            camera.framerate = Fraction(30,1)
            camera.exposure_mode = 'auto'
        return camera

    def __update_settings(self, camera=None):
        """Update dictionary of settings with actual values from supplied
        camera object."""
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
        """Enable power to LCD display."""
        self._lcd_led.value = True

    def LCD_LED_Off(self):
        """Disable power to LCD display."""
        self._lcd_led.value = False

    def disp_clear(self):
        """Clear the display."""
        self._disp.clear()
        self._disp.show()

    def disp_image(self, image):
        """Display the supplied image."""
        self._disp.image(image)
        self._disp.show()

    def get_lcd_size(self):
        """Return the width and height of the LCD screen as a tuple."""
        return LCD._LCDWIDTH, LCD._LCDHEIGHT

    def disp_msg(self, msg, font=FONT_SMALL):
        """Display the supplied message on the screen. An optional
        font can be supplied.
        """
        fw,fh = font.getsize(" ")    # font width and height
        cx = LCD._LCDWIDTH // fw       # max characters per line
        cy = LCD._LCDHEIGHT // fh      # max number of lines

        lines = [ msg[i:i+cx] for i in range(0, len(msg), cx) ]

        LCD_DRAW.rectangle(WHOLE_SCREEN, outline=0, fill=0)
        y = 0
        for line in lines:
            LCD_DRAW.text((0,y), line, font=FONT_SMALL, fill=255)
            y += fh
        self.disp_image(LCD_IMAGE)

    def disp_big_msg(self, msg, location=BIG_MSG):
        """Display the supplied message on the screen using large text.
        An optional location can be specified.
        """
        LCD_DRAW.rectangle(WHOLE_SCREEN, outline=0, fill=0)
        LCD_DRAW.text(location, msg, font=FONT_LARGE, fill=255)
        self.disp_image(LCD_IMAGE)

    #---------------------------------------------------------------
    #                  B  U  T  T  O  N  S
    #---------------------------------------------------------------
    @property
    def buttons(self):
        return tuple([b.value for b in self._buttons])

    @property
    def button_up(self):
        return not self._button_up.value

    @property
    def button_down(self):
        return not self._button_down.value

    @property
    def button_left(self):
        return not self._button_left.value

    @property
    def button_right(self):
        return not self._button_right.value

    @property
    def button_sel(self):
        return not self._button_sel.value

#--------------------------------------------------------------------
# M A I N
#--------------------------------------------------------------------
if __name__ == '__main__':
    print("I'm just a class, nothing to do...")
