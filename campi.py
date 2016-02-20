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
import io, os, time

from fractions import Fraction

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

# Root directory where app was launched
root_dir = os.getcwd()

# Load fonts
font_small = ImageFont.load_default()
font_large = ImageFont.truetype("5Identification-Mono.ttf",12)

# Image draw buffer for writing to LCD display
disp_image = Image.new('1', (LCD.LCDWIDTH, LCD.LCDHEIGHT))
disp_draw  = ImageDraw.Draw(disp_image)

# Display locations
WHOLE_SCREEN    = ((0,0),(LCD.LCDWIDTH, LCD.LCDHEIGHT))
BIG_MSG         = (0,12)         

class Campi():
        
    def __init__(self):
        self._sensor_mode = 2               # 0 (auto), 2 (1-15fps), 3 (0.1666-1fps) (see doc)
        self._resolution = (2592,1944)      # full resolution 2592 x 1944
        self._iso = 0                       # 0(auto), 100, 200, 320, 400, 500, 640, 800
        self._shutter_speed = 0             # 0(auto), value in microseconds
        self._framerate = Fraction(30,1)    # NOTE: this limits max shutter speed
        self._brightness = 50               # 0 - 100 (50)
        self._contrast = 0                  # -100 - 100 (0)
        self._sharpness = 0                 # -100 - 100 (0)
        self._saturation = 0                # -100 - 100 (0)
        self._awb_mode = 'auto'             # auto white balance mode (see doc)
        self._exposure_mode = 'auto'        # exposure mode (see doc)
        self._hvflip = (True, True)         # horizontal/vertical flip
        self._quality = 100                 # 0 - 100,  applies only to JPGs
        self._awb_gains = None
 
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
    # Raspberry Pi Camera functions
    #---------------------------------------------------------------
    def capture(self, filename):
        with picamera.PiCamera(sensor_mode=2) as camera:
            print "updating camera..."
            camera = self.__update_camera__(cam=camera)
            print "capturing image..."
            camera.capture(filename, quality=self._quality)
            settings = {}
            settings['iso'] = camera.iso
            settings['shutter_speed'] = camera.shutter_speed
            settings['exposure_speed'] = camera.exposure_speed
            settings['framerate'] = camera.framerate
            settings['brightness'] = camera.brightness
            settings['contrast'] = camera.contrast
            settings['sharpness'] = camera.sharpness
            settings['saturation'] = camera.saturation
            settings['awb_mode'] = camera.awb_mode
            settings['exposure_mode'] = camera.exposure_mode
            settings['hvflip'] = (camera.hflip,camera.vflip)
            return settings
            
    def capture_with_wait(self, filename, wait=None):
        return None
        # TODO: deprecate this thing
        '''
        with picamera.PiCamera() as camera:
            camera = self.__update_camera__(cam=camera)
            camera.start_preview()
            if wait == None:
                wait = 2.0*(1.0 / camera.framerate)
            time.sleep(wait)
            camera.capture(filename, quality=self._quality)
        '''
                                                             
    def capture_stream(self, ios=None, size=None):
        if ios == None:
            return
        if size == None:
            size = (400,225)
        with picamera.PiCamera(sensor_mode=5) as camera:
            camera = self.__update_camera__(cam=camera, use_video_port=True)
            camera.capture(ios, 'jpeg', use_video_port=True, resize=size)
                    
    def set_cam_config(self,    resolution = None,
                                iso = None,
                                shutter_speed = None,
                                framerate = None,
                                brightness = None,
                                contrast = None,
                                sharpness = None,
                                saturation = None,
                                awb_mode = None,
                                exposure_mode = None,
                                hvflip = None,
                                quality = None,
                                ):
        if not resolution==None:
            self._resolution = resolution
        if not iso==None:
            self._iso = iso        
        if not shutter_speed==None:
            if shutter_speed != 0:
                # force settings to support non-zero (non-auto) shutter_speed
                self._exposure_mode = 'off'                     # shutter speed ignored otherwise
                if shutter_speed > 6000000:                     # global max is 6 secs
                    shutter_speed = 6000000
                if shutter_speed > 1000000:                     # sensor mode 2 or 3 for stills
                    self._sensor_mode = 3                       # 6 secs max (0.1666-1fps)
                    self._framerate = min(Fraction(1),Fraction(1.e6/shutter_speed))
                else:
                    self._sensor_mode = 2                       # 1 sec max (1-15fps)
                    self._framerate = min(Fraction(15),Fraction(1.e6/shutter_speed))
                self._shutter_speed = shutter_speed             # and finally, set shutter speed
                print self._framerate, float(self._framerate)
                print self._shutter_speed
                print self._sensor_mode
            else:
                self._exposure_mode = 'auto'
                self._shutter_speed = shutter_speed          
        if not framerate == None:
            if self._shutter_speed != 0:
                # force framerate to a value that will support shutter_speed
                self._framerate = Fraction(1.e6/self._shutter_speed)
            else:
               self._framerate = framerate 
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
        if not exposure_mode==None:
            self._exposure_mode = exposure_mode
        if not hvflip==None:
            self._hvflip = hvflip
        if not quality==None:
            self._quality = quality
            
    def capture_with_histogram(self, filename, fill=False):
        # capture then open in PIL image
        hname = 'hist_' + time.strftime("%H%M%S", time.localtime()) + '.jpg'
        #self.capture_with_wait(hname)
        settings = self.capture(hname)
        im_in   = Image.open(hname)
        im_out  = Image.new('RGBA', im_in.size)
        im_out.paste(im_in)
        
        # compute histogram, scaled for image size
        hist = im_in.histogram()
        rh = hist[0:256]
        gh = hist[256:512]
        bh = hist[512:768]
        (width, height) = im_in.size
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
        draw = ImageDraw.Draw(im_out)
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
        (fw,fh) = font.getsize(" ")
        lines = []
        lines.append("EXP_MODE %s" % settings['exposure_mode'])
        lines.append("EXP_SPEED %f" % (settings['exposure_speed'] / 1.e6))
        lines.append("ISO %d" % settings['iso'])
        N = 0
        for line in lines:
            draw.text((10,10+N*fh), line, font=font)
            N += 1

        # save it and clean up 
        im_out.save(filename, quality=95)
        os.remove(hname)
            
    def __update_camera__(self, cam=None, use_video_port=False):
        if cam==None:
            return
        cam.sensor_mode = self._sensor_mode
        cam.framerate = self._framerate             # set this before shutter_speed
        cam.exposure_mode = self._exposure_mode     # set this before shutter_speed
        cam.resolution = self._resolution
        cam.iso =  self._iso
        cam.awb_mode = self._awb_mode
        cam.shutter_speed = self._shutter_speed
        cam.brightness = self._brightness
        cam.constrast = self._contrast
        cam.sharpness = self._sharpness
        cam.saturation = self._saturation
        cam.hflip = self._hvflip[0]
        cam.vflip = self._hvflip[1]
        if use_video_port:
            cam.framerate = Fraction(30,1)
            cam.exposure_mode = 'auto'
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
        
    def disp_big_msg(self, msg, location=BIG_MSG):
        # Display a message using large font
        disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        disp_draw.text(location, msg, font=font_large)
        self.disp_image(disp_image)
               
    #---------------------------------------------------------------
    # Button functions
    #---------------------------------------------------------------
    def __get_raw_button(self, btn=None):
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
            if (self.__get_raw_button(btn)==0):
                return True
            else:
                return False
        else:
            return None
        
    def get_buttons(self, ):
        state = {}
        for B in BUTTONS:
            state[B] = self.is_pressed(B)
        return state
   
#--------------------------------------------------------------------
# MAIN 
#--------------------------------------------------------------------
if __name__ == '__main__':
    print "I'm just a class, nothing to do..."