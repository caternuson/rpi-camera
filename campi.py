#!/usr/bin/python
#===========================================================================
# campi.py
#
# Python class to represent RPi based camera.
# There are three main chunks of hardware:
#   * camera = rpi camera module
#   * display = Nokia LCD
#   * buttons = basic push buttons on GPIO
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

# Control button locations on GPIO
BTN_1               =   19
BTN_2               =   16
BTN_3               =   26
BTN_4               =   20
BTN_5               =   21

# Nokia LCD display control on GPIO
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
        self._brightness = 50           # 0 - 100
        self._awb_mode = 'auto'         # auto white balance mode (see doc)
        self._hvflip = (True, True)     # horizontal/vertical flip
        self._quality = 100             # 0 - 100,  applies only to JPGs
        
        self._disp = LCD.PCD8544(LCD_DC,
                                 LCD_RST,
                                 spi=SPI.SpiDev(LCD_SPI_PORT,
                                                LCD_SPI_DEVICE,
                                                max_speed_hz=4000000)
                                 )
        self._disp.begin(contrast=60)
        self._disp.clear()
        self._disp.display()
        
        self._gpio = GPIO
        self._gpio.setwarnings(False)
        self._gpio.setmode(GPIO.BCM)
        GPIO.setup(BTN_1,   GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(BTN_2,   GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(BTN_3,   GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(BTN_4,   GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(BTN_5,   GPIO.IN , pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(LCD_LED, GPIO.OUT, initial=GPIO.LOW)

    #---------------------------------------------------------------
    # Raspberry Pi Camera functions
    #---------------------------------------------------------------
    def capture(self, filename):
        with picamera.PiCamera() as camera:
            camera.resolution = self._resolution
            camera.iso =  self._iso
            camera.shutter_speed = self._shutter_speed
            camera.brightness = self._brightness
            camera.awb_mode = self._awb_mode
            camera.hflip = self._hvflip[0]
            camera.vflip = self._hvflip[1]
            camera.capture(filename, quality=self._quality)
     
    def capture_stream(self, ios):
        with picamera.PiCamera() as camera:
            camera.hflip = True
            camera.vflip = True 
            camera.start_preview()
            camera.capture(ios, 'jpeg', use_video_port=True, resize=(400,225))
                    
    def set_cam_config(self,    resolution = None,
                                iso = None,
                                shutter_speed = None,
                                brightness = None,
                                awb_mode = None,
                                hvflip = None,
                                quality = None,
                                ):
        if not resolution==None:
            self._resolution = resolution
        if not iso==None:
            self.iso = iso        
        if not shutter_speed==None:
            self.shutter_speed = shutter_speed
        if not brightness==None:
            self.brightness = brightness
        if not awb_mode==None:
            self.awb_mode = awb_mode
        if not hvflip==None:
            self.hvflip = hvflip
        if not quality==None:
            self._quality = quality

    
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
        cx = LCD.LCDWIDTH / fw       # characters per line
        cy = LCD.LCDHEIGHT / fh      # number of lines

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
            return (self._gpio.input(BTN_1),
                    self._gpio.input(BTN_2),
                    self._gpio.input(BTN_3),
                    self._gpio.input(BTN_4),
                    self._gpio.input(BTN_5))     
        elif (btn in [BTN_1, BTN_2, BTN_3, BTN_4, BTN_5]):
            return self._gpio.input(btn)
        else:
            return None
   
#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
if __name__ == '__main__':
    print "I'm just a class, nothing to do..."
    
