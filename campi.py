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
# 2014-10-30 (original)
# 2020-06-13 (next gen)
# Carter Nelson
#===========================================================================
import io
from fractions import Fraction
import mjpegger
import timelapser
from picamera import PiCamera
from PIL import Image

class Campi():
    """A class to provide an interface to the campi hardware."""

    def __init__(self):

        self._settings = {}
        self._settings['sensor_mode'] = 0               # 0 (auto), 2 (1-15fps), 3 (0.1666-1fps) (see doc)
        self._settings['resolution'] = (2592, 1944)     # full resolution 2592x1944 (v1)
        self._settings['iso'] = 0                       # 0 (auto), 100, 200, 320, 400, 500, 640, 800
        self._settings['shutter_speed'] = 0             # 0 (auto), value in microseconds
        self._settings['framerate'] = Fraction(30,1)    # NOTE: this limits max shutter speed
        self._settings['brightness'] = 50               # 0 - 100 (50)
        self._settings['contrast'] = 0                  # -100 - 100 (0)
        self._settings['sharpness'] = 0                 # -100 - 100 (0)
        self._settings['saturation'] = 0                # -100 - 100 (0)
        self._settings['awb_mode'] = 'auto'             # white balance mode (see doc)
        self._settings['exposure_mode'] = 'auto'        # exposure mode (see doc)
        self._settings['hvflip'] = (True, True)         # horizontal/vertical flip
        self._settings['quality'] = 100                 # 0 - 100, applies only to JPGs
        self._settings['awb_gains'] = None

        # helper threads
        self._mjpeg_thread = None
        self._timelapse_thread = None

    def capture(self, filename=None):
        """Capture an image using current settings and save to the specified
        filename. If no filename is specified, then return PIL Image object.
        """
        with PiCamera() as camera:
            camera = self._apply_camera_settings(camera)
            if filename:
                camera.capture(filename)
            else:
                stream = io.BytesIO()
                camera.capture(stream, format='jpeg')
                stream.seek(0)
                return Image.open(stream)

    def _apply_camera_settings(self, camera, use_video_port=False):
        """Apply current settings to supplied camera instance."""
        camera.framerate = self._settings['framerate']             # set this before shutter_speed
        camera.exposure_mode = self._settings['exposure_mode']     # set this before shutter_speed
        camera.resolution = self._settings['resolution']
        camera.iso =  self._settings['iso']
        camera.awb_mode = self._settings['awb_mode']
        camera.shutter_speed = self._settings['shutter_speed']
        camera.brightness = self._settings['brightness']
        camera.contrast = self._settings['contrast']
        camera.sharpness = self._settings['sharpness']
        camera.saturation = self._settings['saturation']
        camera.hflip = self._settings['hvflip'][0]
        camera.vflip = self._settings['hvflip'][1]
        if use_video_port:
            camera.framerate = Fraction(30,1)
            camera.exposure_mode = 'auto'
        return camera

    @property
    def settings(self):
        """A dictionary of camera settings."""
        return self._settings

    @property
    def framerate(self):
        """Framerate speified using a Fraction in frames per second.
        NOTE: this limits max shutter speed
        """
        return self._settings['framerate']

    @framerate.setter
    def framerate(self, val):
        self._settings['framerate'] = val

    @property
    def exposure_mode(self):
        return self._settings['exposure_mode']

    @exposure_mode.setter
    def exposure_mode(self, val):
        self._settings['exposure_mode'] = val

    @property
    def resolution(self):
        return self._settings['resolution']

    @resolution.setter
    def resolution(self, val):
        self._settings['resolution'] = val

    @property
    def iso(self):
        return self._settings['iso']

    @iso.setter
    def iso(self, val):
        self._settings['iso'] = val

    @property
    def awb_mode(self):
        return self._settings['awb_mode']

    @awb_mode.setter
    def awb_mode(self, val):
        self._settings['awb_mode'] = val

    @property
    def shutter_speed(self):
        return self._settings['shutter_speed']

    @shutter_speed.setter
    def shutter_speed(self, val):
        self._settings['shutter_speed'] = val

    @property
    def brightness(self):
        return self._settings['brightness']

    @brightness.setter
    def brightness(self, val):
        self._settings['brightness'] = val

    @property
    def contrast(self):
        return self._settings['contrast']

    @contrast.setter
    def constrast(self, val):
        self._settings['contrast'] = val

    @property
    def sharpness(self):
        return self._settings['sharpness']

    @sharpness.setter
    def sharpness(self, val):
        self._settings['sharpness'] = val

    @property
    def saturation(self):
        return self._settings['saturation']

    @saturation.setter
    def saturation(self, val):
        self._settings['saturation'] = val

    def start_timelapse(self, length=5, interval=10):
        """Start a timelapse capture with the given length and interval."""
        if self._timelapse_thread:
            if self._timelapse_thread.is_alive():
                return
            else:
                self._timelapse_thread = None
        self._timelapse_thread = timelapser.TimeLapser(camera=self,
                                                       length=length,
                                                       interval=interval)
        self._timelapse_thread.start()

    def stop_timelapse(self):
        if not self._timelapse_thread:
            return
        self._timelapse_thread.stop()
        self._timelapse_thread = None

    @property
    def timelapse_status(self):
        if self._timelapse_thread:
            status = {
                "tl_running" : self._timelapse_thread.is_alive(),
                "time_remaining" : self._timelapse_thread.time_remaining,
                "time_to_next" : self._timelapse_thread.time_to_next,
                "images_taken" : self._timelapse_thread.images_taken,
            }
        else:
            status = {
                "tl_running" : False
            }
        return status

    def start_mjpeg_stream(self, **kwargs):
        """Start serving an MJPEG stream on specified port."""
        if self._mjpeg_thread:
            if self._mjpeg_thread.is_alive():
                return
            else:
                self._mjpeg_thread = None
        camera = self._apply_camera_settings(PiCamera(sensor_mode=5))
        self._mjpeg_thread = mjpegger.MJPEGThread(camera=camera, **kwargs)
        self._mjpeg_thread.start()

    def stop_mjpeg_stream(self):
        """"Stop serving MJPEG stream."""
        if not self._mjpeg_thread:
            return
        self._mjpeg_thread.stop()
        self._mjpeg_thread = None
