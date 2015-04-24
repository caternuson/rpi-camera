#!/usr/bin/python
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
import picamera
import RPi.GPIO as GPIO
import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

import Image
import ImageDraw
import ImageFont

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

# Load fonts
font_small = ImageFont.load_default()

# Image draw buffer for writing to LCD display
WHOLE_SCREEN    = ((0,0),(LCD.LCDWIDTH, LCD.LCDHEIGHT))
disp_image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
disp_draw  = ImageDraw.Draw(disp_image)

class Campi():
        
    def __init__(self):          
        self._resolution = (2592,1944)  # full resolution 2592 x 1944
        self._iso = 0                   # 0(auto), 100, 200, 320, 400, 500, 640, 800
        self._shutter_speed = 0         # 0(auto), value in microseconds
        self._brightness = 50           # 0 - 100 (50)
        self._contrast = 0              # -100 - 100 (0)
        self._sharpness = 0             # -100 - 100 (0)
        self._saturation = 0            # -100 - 100 (0)
        self._awb_mode = 'auto'         # auto white balance mode (see doc)
        self._hvflip = (True, True)     # horizontal/vertical flip
        self._quality = 100             # 0 - 100,  applies only to JPGs
 
        self._disp = LCD.PCD8544(LCD_DC,
                                 LCD_RST,
                                 spi=SPI.SpiDev(LCD_SPI_PORT,
                                                LCD_SPI_DEVICE,
                                                max_speed_hz=4000000)
                                 )
        self._disp.begin(contrast=35)
        self._disp.clear()
        self._disp.display()
        
        self._gpio = GPIO
        self._gpio.setwarnings(False)
        self._gpio.setmode(GPIO.BCM)
        for B in BUTTONS:
            GPIO.setup(B, GPIO.IN , pull_up_down=GPIO.PUD_UP)
        GPIO.setup(LCD_LED, GPIO.OUT, initial=GPIO.LOW)
        
    #---------------------------------------------------------------
    # Raspberry Pi Camera functions
    #---------------------------------------------------------------
    def capture(self, filename):
        with picamera.PiCamera() as camera:
            camera = self.__update_camera__(cam=camera)
            camera.capture(filename, quality=self._quality)
     
    def capture_stream(self, ios):
        with picamera.PiCamera() as camera:
            camera = self.__update_camera__(cam=camera)
            camera.capture(ios, 'jpeg', use_video_port=True, resize=(400,225))
                    
    def set_cam_config(self,    resolution = None,
                                iso = None,
                                shutter_speed = None,
                                brightness = None,
                                contrast = None,
                                sharpness = None,
                                saturation = None,
                                awb_mode = None,
                                hvflip = None,
                                quality = None,
                                ):
        if not resolution==None:
            self._resolution = resolution
        if not iso==None:
            self._iso = iso        
        if not shutter_speed==None:
            self._shutter_speed = shutter_speed
        if not brightness==None:
            self._brightness = brightness
        if not contrast==None:
            self._contrast = contrast
        if not sharpness==None:
            self._sharpness = sharpness
        if not saturation==None:
            self._saturation = saturation
        if not awb_mode==None:
            self._awb_mode = awb_mode
        if not hvflip==None:
            self._hvflip = hvflip
        if not quality==None:
            self._quality = quality

    def __update_camera__(self, cam=None):
        if cam==None:
            return
        cam.resolution = self._resolution
        cam.iso =  self._iso
        cam.shutter_speed = self._shutter_speed
        cam.brightness = self._brightness
        cam.constrast = self._contrast
        cam.sharpness = self._sharpness
        cam.saturation = self._saturation
        cam.awb_mode = self._awb_mode
        cam.hflip = self._hvflip[0]
        cam.vflip = self._hvflip[1]
        return cam
    
    #---------------------------------------------------------------
    # Nokia LCD Display functions
    #---------------------------------------------------------------
    def LCD_LED_On(self):
        self._gpio.output(RpiCamera.LCD_LED, GPIO.HIGH)
        
    def LCD_LED_Off(self):
        self._gpio.output(RpiCamera.LCD_LED, GPIO.LOW)
        
    def disp_clear(self):
        self._disp.clear()
        self._disp.display()
    
    def disp_image(self, image):
        self._disp.image(image)
        self._disp.display()
        
    def get_lcd_size(self):
        return (LCD.LCDWIDTH, LCD.LCDHEIGHT)
    
    def disp_msg(self, msg, font=font_small):
        (fw,fh) = font.getsize(" ")  # font width and height
        cx = LCD.LCDWIDTH / fw       # max characters per line
        cy = LCD.LCDHEIGHT / fh      # max number of lines

        lines = [ msg[i:i+cx] for i in range(0, len(msg), cx) ]
        
        disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        y = 0
        for line in lines:
            disp_draw.text((0,y), line, font=font_small)
            y += fh
        self.disp_image(disp_image)
                
    #---------------------------------------------------------------
    # Button functions
    #---------------------------------------------------------------
    def get_button(self, btn=None):
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
        if (btn in BUTTONS):
            if (self.get_button(btn)==0):
                return True
            else:
                return False
        else:
            return None
   
#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
if __name__ == '__main__':
    print "I'm just a class, nothing to do..."