#!/usr/bin/env python3
#===========================================================================
# camera_server.py
#
# Web interface.
#
# 2020-07-05
# Carter Nelson
#===========================================================================
import os
import time
import json

import tornado.ioloop
import tornado.web
import tornado.websocket

import campi

camera = campi.Campi()
camera.resolution = (1920, 1080)

class MainHandler(tornado.web.RequestHandler):

    # subclasses should not override __init__ (override initialize instead).
    # def initialize(self):
    #     super().initialize()
    #     print("initialize")

    def get(self):
        print("GET")
        self.render("timelapse.html", **camera.timelapse_status)

    def post(self):
        json_data = json.loads(self.request.body.decode('utf-8'))
        command = json_data.get('command')
        print(command)
        if command == 'debug':
            #TODO: add some debug dump info
            pass
        elif command == 'start_timelapse':
            self._start_timelapse()
        elif command == 'stop_timelapse':
            self._stop_timelapse()
        elif command == 'get_status':
            self._get_status()
        elif command == 'update_config':
            self._update_config()
        elif command == 'get_preview':
            self._capture_still()
        elif command == 'start_liveview':
            self._start_liveview()
        elif command == 'stop_liveview':
            self._stop_liveview()
        elif command == 'set_date':
            self._set_date(json_data.get('date'))
        else:
            print("Unknown command:", command)

    def _set_date(self, date):
        if date:
            print("Date:", date)
            os.system('sudo date -s "{}"'.format(date))

    def _start_timelapse(self):
        camera.start_timelapse()

    def _stop_timelapse(self):
        camera.stop_timelapse()

    def _get_status(self):
        self.write(json.dumps(camera.timelapse_status))

    def _update_config(self):
        json_data = json.loads(self.request.body.decode('utf-8'))
        if 'delta_time' in json_data:
            camera.timelapse_interval = int(json_data['delta_time'])
        if 'total_imgs' in json_data:
            camera.timelapse_length = int(json_data['total_imgs'])
        if 'shutter_speed' in json_data:
            camera.shutter_speed = int(json_data['shutter_speed'])
        if 'iso' in json_data:
            camera.iso = int(json_data['iso'])

    def _capture_still(self):
        filename = 'static/preview.jpg'
        camera.capture(filename)
        url = "{0}?{1}".format(filename, time.time())  # prevent using cached image
        resp = {'url':url}
        self.write(json.dumps(resp))

    def _start_liveview(self):
      camera.start_mjpeg_stream(port=8081)
      addr = self.request.host.partition(":")[0]
      resp = {"url" : "http://" + addr + ":8081/"}
      self.write(json.dumps(resp))

    def _stop_liveview(self):
      camera.stop_mjpeg_stream()

class TimelapseStatusHandler(tornado.websocket.WebSocketHandler):
    """Serve up timelapse status via websocket."""

    def initialize(self):
        self.status_loop = tornado.ioloop.PeriodicCallback(self.send_status, 500)

    def open(self):
        """Callback for when websocket is opened."""
        self.status_loop.start()

    def on_close(self):
        """Callback for when websocket is closed."""
        self.status_loop.stop()

    def send_status(self):
        self.write_message(json.dumps(camera.timelapse_status))


#--------------------------------------------------------------------
# M A I N
#--------------------------------------------------------------------
if __name__ == "__main__":
    print("Setting up server...")
    app = tornado.web.Application(
        [
        (r"/", MainHandler),
        (r"/ws", TimelapseStatusHandler)
        ],
        static_path = os.path.join(os.path.dirname(__file__), "static"),
        template_path = os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.listen(8080)
    print("Server started.")
    tornado.ioloop.IOLoop.current().start()
