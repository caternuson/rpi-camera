#!/usr/bin/env python
#===========================================================================
# camera_server.py
#
# Web interface.
#
# 2015-04-06
# Carter Nelson
#===========================================================================
import os
import time
import json

import tornado.httpserver
import tornado.websocket
import tornado.web

import campi
import timelapser

ROOT_DIR = os.getcwd()
PORT = 8080

camera = campi.Campi()
camera.set_cam_config("resolution",(1920, 1080))

# timelapse control thread
timelapse = None

# global config
config = {'delta_time':10,
          'total_imgs':5,
          'shutter_speed':0,
          'iso':0,
        }

class MainHandler(tornado.web.RequestHandler):
    """Handler for server root."""
    
    def get(self, ):
        print "Root get."
        tl_running = False
        if not timelapse == None:
            if timelapse.is_alive():
                tl_running = True
        if tl_running:
            print "timelapse"
            self.render("timelapse.html")
        else:
            print "configure"
            self.render("configure.html")                
        
class TimelapseHandler(tornado.web.RequestHandler):
    """Handler for starting a timelapse."""
        
    def get(self, ):
        global timelapse
        if not timelapse == None:
            if not timelapse.is_alive():
                timelapse = None
        if timelapse == None:
            print "Starting timelapse."
            self.__start_timelapse()
        self.render("timelapse.html")
              
    def __start_timelapse(self, ):
        global timelapse
        if not timelapse == None:
            if timelapse.t.is_alive():
                return
        timelapse = timelapser.TimeLapser(kwargs={
            'camera': camera,
            'delta_time': config['delta_time'],
            'total_imgs': config['total_imgs'],
            })
        timelapse.start()
        
    def __stop_timelapse(self, ):
        global timelapse
        if not timelapse == None:
            timelapse.stop()
            timelapse = None
            
class TimelapseStatusHandler(tornado.websocket.WebSocketHandler):
    """Serve up timelapse status via websocket."""
    
    def initialize(self, ):
        self.status_loop = None
    
    def open(self, ):
        """Callback for when websocket is opened."""
        self.status_loop = tornado.ioloop.PeriodicCallback(self.send_status, 500)
        self.status_loop.start()
    
    def on_close(self, ):
        """Callback for when websocket is closed."""
        if not self.status_loop == None:
            self.status_loop.stop()
            self.status_loop = None
    
    def send_status(self, ):
        if timelapse == None:
            return
        status = timelapse.get_status()
        camera.disp_msg("Timelapse Running. {0} of {1}".format(
            status['image_count'], status['total_imgs']))
        self.write_message(json.dumps(status))

class TimelapseCancelHandler(tornado.web.RequestHandler):
    """Cancel timelapse if running and redirect to configuration."""
    
    def get(self, ):
        if not timelapse == None:
            timelapse.stop();
            timelapse.join();
            self.redirect("/");
    
class AjaxConfig(tornado.web.RequestHandler):
    """Handle AJAX for configuration."""
    
    def post(self, ):
        print "Updating config."
        json_data = json.loads(self.request.body)
        resp = self.__process_json(json_data)
        for k in config:
            camera.set_cam_config(setting=k, value=config[k])
        self.write(resp)
        
    def __process_json(self, json_data):
        try:
            config['delta_time'] = int(json_data['delta_time'])
        except ValueError:
            pass
        try:
            config['total_imgs'] = int(json_data['total_imgs'])
        except ValueError:
            pass
        try:
            config['shutter_speed'] = int(json_data['shutter_speed'])
        except ValueError:
            pass
        try:
            config['iso'] = int(json_data['iso'])
        except ValueError:
            pass
        resp_data = config
        resp_data['total_time'] = self.__total_time_str()
        return json.dumps(resp_data)
    
    def __total_time_str(self, ):
        total_secs = config['delta_time'] * config['total_imgs']
        hours = total_secs / 3600
        minutes = (total_secs % 3600) / 60
        seconds = total_secs % 60
        return "{:2}:{:02}:{:02}".format(hours,minutes,seconds) 
    
class AjaxCapture(tornado.web.RequestHandler):
    """Handle AJAX for image capture."""

    def post(self, ):
        print "Capturing image."
        filename = 'static/preview.jpg'
        camera.capture_with_histogram(filename)
        url = "{0}?{1}".format(filename, time.time())  # prevent using cached image
        resp = {'url':url}
        self.write(json.dumps(resp))
        '''
        with open(filename, "rb") as f:
            img_data = base64.b64encode(f.read())
        self.write({
            "img_data": img_data,
        })
        '''
        print "Done."

class AjaxSetDate(tornado.web.RequestHandler):
    """Handle AJAX for setting time and date."""

    def post(self, ):
        print "Setting date."
        json_data = json.loads(self.request.body)
        os.system('date -s "{}"'.format(json_data['date']))

class MJPGStream(tornado.web.RequestHandler):
    """Server a MJPG stream."""
    
    def post(self, ):
        print "mjpgstream post"
        json_data = json.loads(self.request.body)
        command = json_data['command']
        resp = {}
        if "START" in command.upper():
            camera.mjpgstream_start()
            addr = self.request.host.partition(":")[0]
            resp['url'] = "http://" + addr + ":8081/"
            print "START"
        elif "STOP" in command.upper():
            camera.mjpgstream_stop()
            print "STOP"
        self.write(json.dumps(resp))
            
class MainServerApp(tornado.web.Application):
    """Main Server application."""
    
    def __init__(self):
        handlers = [
            (r"/",                  MainHandler),
            (r"/timelapse",         TimelapseHandler),
            (r"/timelapse_status",  TimelapseStatusHandler),
            (r"/cancel",            TimelapseCancelHandler),
            (r"/ajaxconfig",        AjaxConfig),
            (r"/capture",           AjaxCapture),
            (r"/mjpgstream",        MJPGStream),   
            (r"/setdate",           AjaxSetDate),
        ]
        
        settings = {
            "static_path": os.path.join(os.path.dirname(__file__), "static"),
            "template_path": os.path.join(os.path.dirname(__file__), "templates"),
        }
        
        tornado.web.Application.__init__(self, handlers, **settings)

#--------------------------------------------------------------------
# M A I N 
#--------------------------------------------------------------------
if __name__ == '__main__':
    tornado.httpserver.HTTPServer(MainServerApp()).listen(PORT)
    print "Server started on port {0}.".format(PORT)
    tornado.ioloop.IOLoop.instance().start()