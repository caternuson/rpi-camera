#!/usr/bin/env python
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

import campi

camera = campi.Campi()

class MainHandler(tornado.web.RequestHandler):

    def get(self):
        self.render("timelapse.html")

    def post(self):
        json_data = json.loads(self.request.body.decode('utf-8'))
        command = json_data['command']
        print(command)
        if command == 'debug':
            #TODO: add some debug dump info
            pass
        elif command == 'update_config':
            self._update_config()
        elif command == 'get_preview':
            self._capture_still()
        elif command == 'start_liveview':
            self._start_liveview()
        elif command == 'stop_liveview':
            self._stop_liveview()

    def _update_config(self):
        json_data = json.loads(self.request.body.decode('utf-8'))
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

#--------------------------------------------------------------------
# M A I N
#--------------------------------------------------------------------
if __name__ == "__main__":
    app = tornado.web.Application(
        [
        (r"/", MainHandler),
        ],
        static_path = os.path.join(os.path.dirname(__file__), "static"),
        template_path = os.path.join(os.path.dirname(__file__), "templates"),
    )
    app.listen(8080)
    tornado.ioloop.IOLoop.current().start()
