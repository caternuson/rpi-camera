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
BIG4_1          = (31,0)
BIG4_2          = (31,18)
BIG_MSG         = (0,12)         
BIG4_1_LABEL    = (4,5)
BIG4_2_LABEL    = (4,23)
TIME_1          = (4,36)
TIME_2          = (2,36)
TOT_IMG         = (60,36)
OK_CONFIRM      = (4,14)
PROG_BAR_H      = 31
PROG_BAR_W      = 14
PROG_BAR_LOC    = (8,4)
PROG_BAR_BOX    = (PROG_BAR_LOC,(PROG_BAR_LOC[0]+PROG_BAR_W,PROG_BAR_LOC[1]+PROG_BAR_H))

# Timelapse information
tl_info = {}
tl_info['name'] = None
tl_info['total_imgs'] = 0
tl_info['delta_time'] = 0
tl_info['total_time'] = tl_info['delta_time'] * (tl_info['total_imgs']-1)
tl_info['image_count'] = 0
tl_info['start_time'] = 0
tl_info['finish_time'] = 0
tl_info['time_remaining'] = 0
tl_info['time_to_next'] = 0

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
        self._exposure_mode = 'auto'    # exposure mode (see doc)
        self._hvflip = (True, True)     # horizontal/vertical flip
        self._quality = 100             # 0 - 100,  applies only to JPGs
        self._awb_gains = None
 
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
            
    def capture_with_wait(self, filename, wait=2):
        with picamera.PiCamera() as camera:
            camera = self.__update_camera__(cam=camera)
            camera.framerate = 30
            camera.start_preview()
            time.sleep(wait)
            camera.capture(filename, quality=self._quality)
            
    def capture_timelapse2(self, total_imgs=None, delta_time=None):
        tl_info['total_imgs'] = total_imgs
        tl_info['delta_time'] = delta_time
        tl_info['total_time'] = tl_info['delta_time'] * (tl_info['total_imgs']-1)
        tl_info['start_time'] = time.time()
        tl_info['finish_time'] = tl_info['start_time'] + tl_info['total_time']
        tl_info['image_count'] = 1
        tl_info['name'] = time.strftime("%Y%m%d_%H%M",time.localtime())
        os.mkdir(tl_info['name'])
        os.chdir(tl_info['name'])
        tl_info['acquire_start'] = time.time()
        while (tl_info['image_count'] <= tl_info['total_imgs']):
            self.disp_big_msg(" TAKE ")
            self.capture_with_wait(tl_info['name']+'_%04d.jpg'%tl_info['image_count'])
            self.__timelapse_wait__()
            tl_info['image_count'] += 1
        os.chdir(root_dir)
            
    def capture_timelapse(self, total_imgs=None, delta_time=None):
        tl_info['total_imgs'] = total_imgs
        tl_info['delta_time'] = delta_time
        tl_info['total_time'] = tl_info['delta_time'] * (tl_info['total_imgs']-1)
        tl_info['start_time'] = time.time()
        tl_info['finish_time'] = tl_info['start_time'] + tl_info['total_time']
        
        with picamera.PiCamera() as camera:
            # set camera parameters
            camera = self.__update_camera__(cam=camera)
            
            # let gains auto adjust, then freeze values
            camera.framerate = 30
            camera.start_preview()
            time.sleep(2)
            camera.exposure_mode = 'off'
            g = camera.awb_gains
            camera.awb_mode = 'off'
            camera.awb_gains = g
            
            # actual time lapse loop
            tl_info['image_count'] = 0
            tl_info['name'] = time.strftime("%Y%m%d_%H%M",time.localtime())
            os.mkdir(tl_info['name'])
            os.chdir(tl_info['name'])
            tl_info['acquire_start'] = time.time()
            self.disp_big_msg(" TAKE ")
            for filename in camera.capture_continuous(tl_info['name']+'_{counter:04d}.jpg'):
                tl_info['image_count'] += 1
                if (tl_info['image_count'] >= tl_info['total_imgs']):
                    break;
                self.__timelapse_wait__()
                self.disp_big_msg(" TAKE ")
                tl_info['acquire_start'] = time.time()
            
        os.chdir(root_dir)
                        
    def __timelapse_wait__(self, ):
        keep_waiting = True
        while keep_waiting:
            time.sleep(0.250)
            tl_info['time_to_next'] = tl_info['acquire_start'] + tl_info['delta_time'] - time.time()
            tl_info['time_remaining'] = tl_info['time_to_next'] + tl_info['delta_time']*(tl_info['total_imgs']-tl_info['image_count']-1)
            self.disp_show_tl_status()
            if (tl_info['time_to_next'] <= 0 ):
                keep_waiting = False
                        
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
                                exposure_mode = None,
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
        if not exposure_mode==None:
            self._exposure_mode = exposure_mode
        if not hvflip==None:
            self._hvflip = hvflip
        if not quality==None:
            self._quality = quality
            
    def capture_with_histogram(self, filename):
        # capture image to PIL object
        stream = io.BytesIO()
        with picamera.PiCamera() as camera:
            camera = self.__update_camera__(cam=camera)
            # let gains auto adjust, then freeze values
            camera.framerate = 30
            time.sleep(2)
            camera.exposure_mode = 'off'
            g = camera.awb_gains
            camera.awb_mode = 'off'
            camera.awb_gains = g
            camera.capture(stream, 'jpeg', quality=self._quality)
        stream.seek(0)
        im = Image.open(stream)
        
        # compute histogram, scaled for image size
        hist = im.histogram()
        rh = hist[0:256]
        gh = hist[256:512]
        bh = hist[512:768]
        (width, height) = im.size
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
        #im_hist = Image.new('RGB',size,'black')
        draw = ImageDraw.Draw(im)
        draw.line(rl, fill='red', width=5)
        draw.line(gl, fill='green', width=5)
        draw.line(bl, fill='blue', width=5)
        im.save(filename,quality=95)      
            
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
        cam.exposure_mode = self._exposure_mode
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
        
    def disp_big_msg(self, msg, location=BIG_MSG):
        # Display a message using large font
        disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        disp_draw.text(location, msg, font=font_large)
        self.disp_image(disp_image)

    def disp_show_tl_status(self, ):
        disp_draw.rectangle(WHOLE_SCREEN, outline=255, fill=255)
        disp_draw.rectangle(PROG_BAR_BOX, outline=0, fill=255)
        #progress = int(float(PROG_BAR_H) * ( float(image_count)/float(total_imgs)))
        progress = int(float(PROG_BAR_H) * ((tl_info['total_time']-tl_info['time_remaining'])/tl_info['total_time']))
        PROG_BAR_FILL = ((PROG_BAR_LOC[0], PROG_BAR_LOC[1]+PROG_BAR_H-progress),
                        (PROG_BAR_LOC[0]+PROG_BAR_W,PROG_BAR_LOC[1]+PROG_BAR_H))
        disp_draw.rectangle(PROG_BAR_FILL, outline=0, fill=0)
        disp_draw.text(BIG4_2, "%04d" % (tl_info['image_count']), font=font_large)
        disp_draw.text(BIG4_1,"%04d" % (tl_info['time_to_next']), font=font_large)
        disp_draw.text(TIME_2, time.strftime("%H:%M:%S", time.gmtime(tl_info['time_remaining'])), font=font_small)
        disp_draw.text(TOT_IMG, "%04d" % (tl_info['total_imgs']), font=font_small)
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