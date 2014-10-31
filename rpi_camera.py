#!/usr/bin/python
#===========================================================================
# rpi_camera.py
#
# Python class to represent RPi based camera.
#
# 2014-10-30
# Carter Nelson
#===========================================================================
import picamera
import RPi.GPIO as GPIO
import Adafruit_Nokia_LCD as LCD
import Adafruit_GPIO.SPI as SPI

# Control Buttons
BTN_1               =   25
BTN_2               =   18
BTN_3               =   17
BTN_4               =   27
BTN_5               =   22

# Nokia LCD Display
LCD_DC              =   23      # Nokia LCD display D/C
LCD_RST             =   24      # Nokia LCD displat Reset
LCD_SPI_PORT        =   0       # Hardware SPI port to use
LCD_SPI_DEVICE      =   0       # Hardware SPI device (determines chip select pin used)
LCD_LED             =   4       # LCD LED enable pin (HIGH=ON, LOW=OFF)

class RpiCamera():
        
    def __init__(self):          
        self._camera = picamera.PiCamera()
        
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
        
    def get_camera(self):
        return self._camera
    
    def get_button(self, btn):
        if (btn in [BTN_1, BTN_2, BTN_3, BTN_4, BTN_5]):
            return self._gpio.input(btn)
        else:
            return None
        
    def get_lcd_size(self):
        return (LCD.LCDWIDTH, LCD.LCDHEIGHT)
      
#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
if __name__ == '__main__':
    print "I'm just a class, nothing to do..."
    
