#===========================================================================
# timelapser.py
#
# Timelapse thread class.
#
# 2016-07-16
# Carter Nelson
#===========================================================================
import threading
import time
import os

class TimeLapser(threading.Thread):
    """A class for performing timelapse capture in a separate thread."""
    
    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None):
        threading.Thread.__init__(self, group=group, target=target, name=name)

        self.dir = None
        
        self.camera = kwargs['camera']
        self.delta_time = kwargs['delta_time']
        self.total_imgs = kwargs['total_imgs']
        
        self.start_time = None
        self.finish_time = None
        self.wait_time = None
        self.remaining_time = None
        self.image_count = 0
        self.keep_running = False
        self.timelapse_name = None
        self.waiter = threading.Event()
        
    def run(self, ):
        """Take a series of images."""
        self.timelapse_name = time.strftime("%Y%m%d_%H%M",time.localtime())
        self.dir = os.path.join(os.getcwd(), self.timelapse_name)
        try:
            os.mkdir(self.dir)
        except OSError:
            # directory exist
            # not likely in real world scenario ?
            # ignore and overwrite, for now
            pass

        infofile = self.timelapse_name+"_info.txt"
        infofile = os.path.join(self.dir, infofile)
        with open(infofile, "w") as file:
            file.write("TIMELAPSE NAME = {0}\n".format(self.timelapse_name))
            file.write("TOTAL IMGS = {0}\n".format(self.total_imgs))
            file.write("DELTA TIME = {0}\n".format(self.delta_time))
            file.write("-"*15+"\n")
            file.write("Camera Settings\n")
            file.write("-"*15+"\n")
            for k in self.camera.settings:
                txt = "{0} = {1}\n".format(k,self.camera.settings[k])
                file.write(txt)
            
        self.start_time  = time.time()
        self.remaining_time = self.delta_time * (self.total_imgs - 1)
        self.finish_time = self.start_time + self.remaining_time

        self.keep_running = True
        self.image_count = 0
        
        while self.keep_running:
            self.image_count += 1
            filename = self.timelapse_name+"_%04d.jpg" % self.image_count
            filename = os.path.join(self.dir, filename)
            acquire_start = time.time()
            self.camera.capture(filename)
            acquire_finish = time.time()
            acquire_time = acquire_finish - acquire_start
            remaining_imgs = self.total_imgs - self.image_count
            self.wait_time = self.delta_time - acquire_time
            self.remaining_time = self.wait_time + self.delta_time * remaining_imgs
            if remaining_imgs == 0:
                self.keep_running = False
                self.remaining_time = 0
                self.wait_time = 0
            while self.keep_running and self.wait_time > 0: 
                self.wait_time = self.delta_time - (time.time() - acquire_start) 
                self.remaining_time = self.wait_time + self.delta_time * remaining_imgs
                self.waiter.wait(0.25)                        
        self.keep_running = False
                
    def stop(self, ):
        """Stop the timelapse and terminate the thread."""
        self.keep_running = False
        self.waiter.set()       
      
    def get_status(self, ):
        """Return current status of timelapse."""
        return {
            'timelapse_name'    : self.timelapse_name ,
            'image_count'       : self.image_count ,
            'delta_time'        : self.delta_time ,
            'total_imgs'        : self.total_imgs ,
            'start_time'        : self.start_time ,
            'finish_time'       : self.finish_time ,
            'wait_time'         : self.wait_time ,
            'remaining_time'    : self.remaining_time ,
            'is_alive'          : self.is_alive(),
        }