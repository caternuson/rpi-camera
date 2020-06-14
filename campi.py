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
import mjpegger
from picamera import PiCamera
from PIL import Image

class Campi():
    """A class to provide an interface to the campi hardware."""

    def __init__(self):
        self._mjpeg_stream = None

    def capture(self, filename=None):
        """Capture an image using current settings and save to the specified
        filename. If no filename is specified, then return PIL Image object.
        """
        with PiCamera() as camera:
            if filename:
                camera.capture(filename)
            else:
                stream = io.BytesIO()
                camera.capture(stream, format='jpeg')
                stream.seek(0)
                return Image.open(stream)

    def start_mjpeg_stream(self, **kwargs):
        """Start serving an MJPEG stream on specified port."""
        if self._mjpeg_stream:
            return
        self._mjpeg_stream = mjpegger.MJPEGThread(camera=PiCamera(), **kwargs)
        self._mjpeg_stream.start()

    def stop_mjpeg_stream(self):
        """"Stop serving MJPEG stream."""
        if not self._mjpeg_stream:
            return
        self._mjpeg_stream.stop()
        self._mjpeg_stream = None
