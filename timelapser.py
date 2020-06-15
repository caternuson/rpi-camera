#===========================================================================
# timelapser.py
#
# Runs a timelapse capture using provided camera object.
#
# 2016-07-16 (orig)
# 2020-06-14 (update)
# Carter Nelson
#===========================================================================
import threading
import time
import os

class TimeLapser(threading.Thread):
    """A thread class for performing timelapse using supplied camera instance."""

    def __init__(self, **kwargs):
        super().__init__()

        self._camera = kwargs.get('camera', None)
        self._interval = kwargs.get('interval', 0)
        self._length = kwargs.get('length', 0)

        self._dir = None

        self._start_time = None
        self._finish_time = None
        self._time_to_next = None
        self._time_to_finish = None
        self._taken = None
        self._remaining = 0
        self._keep_running = False
        self._name = None
        self._waiter = threading.Event()

    def run(self):
        # create directory for images
        self._name = time.strftime("%Y%m%d_%H%M",time.localtime())
        self._dir = os.path.join(os.getcwd(), self._name)
        try:
            os.mkdir(self._dir)
        except OSError:
            # directory exist
            # not likely in real world scenario ?
            # ignore and overwrite, for now
            pass

        # dump meta info to file
        infofile = self._name+"_info.txt"
        infofile = os.path.join(self._dir, infofile)
        with open(infofile, "w") as file:
            file.write("TIMELAPSE NAME = {0}\n".format(self._name))
            file.write("TOTAL IMGS = {0}\n".format(self._length))
            file.write("DELTA TIME = {0}\n".format(self._interval))
            file.write("-"*15+"\n")
            file.write("Camera Settings\n")
            file.write("-"*15+"\n")
            for k in self._camera.settings:
                txt = "{0} = {1}\n".format(k,self._camera.settings[k])
                file.write(txt)

        # initialize
        self._taken = 0
        self._start_time = time.time()
        self._time_to_finish = self._interval * (self._length - 1)
        self._finish_time = self._start_time + self._time_to_finish

        # main timelapse loop
        self.keep_running = True
        while self.keep_running:
            # take an image
            self._taken += 1
            filename = self._name+"_%04d.jpg" % self._taken
            filename = os.path.join(self._dir, filename)
            acquire_start = time.time()
            self._camera.capture(filename)
            acquire_finish = time.time()
            acquire_time = acquire_finish - acquire_start
            self._remaining = self._length - self._taken
            self._time_to_next = self._interval - acquire_time
            # stop if no more images left to take
            if self._remaining <= 0:
                self.keep_running = False
                self._time_to_finish = 0
                self._time_to_next = 0
            # wait interval
            while self.keep_running and self._time_to_next > 0:
                self._time_to_next = self._interval - (time.time() - acquire_start)
                self._time_to_finish = self._time_to_next + self._interval * self._remaining
                self._waiter.wait(0.25)

        # all done
        self.keep_running = False

    def stop(self):
        """Stop the timelapse and terminate the thread."""
        self.keep_running = False
        self._waiter.set()

    @property
    def interval(self):
        """Time in seconds between each image capture."""
        return self._interval

    @interval.setter
    def interval(self, val):
        self._interval = val

    @property
    def length(self):
        """Total number of images to acquire."""
        return self._length

    @length.setter
    def length(self, val):
        self._length = val