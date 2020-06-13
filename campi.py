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
from picamera import PiCamera

from PIL import Image

class Campi:
    """A class to provide an interface to the campi hardware."""

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
