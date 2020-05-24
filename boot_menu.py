#!/usr/bin/env python
#===========================================================================
# boot_menu.py
#
# Run at boot to pick how to bring up camera:
#  * pick a wifi option
#  * run appropriate program(s)
#
# 2014-4-23
# Carter Nelson
#===========================================================================
import time
import os

import campi

camera = campi.Campi()
camera.LCD_LED_On()

selection = 1

          #01234567890123
BLANK   = ' [ ] '
CHECKED = ' [X] '
MENU1   =      'AP WIFI  '
MENU2   =      'HOME WIFI'
MENU3   =      'EXIT     '
MENU4   =      'EXIT     '

cursor = {}
cursor['1'] = BLANK
cursor['2'] = BLANK
cursor['3'] = BLANK
cursor['4'] = BLANK

menu = {}
menu['1'] = MENU1
menu['2'] = MENU2
menu['3'] = MENU3
menu['4'] = MENU4

def clear_cursor():
    for key in cursor:
        cursor[key]= BLANK

def set_cursor():
    clear_cursor()
    cursor['%i'%selection] = CHECKED

def update_menu():
    set_cursor()
    msg = ''
    for l in [1,2,3,4]:
        key = '%s'%l
        msg += '%s%s' % (cursor[key],menu[key])
    camera.disp_msg(msg)

#===========================
# MAIN
#===========================
while True:
    if camera.button_up:
        selection -= 1
        if selection < 1:
            selection = 4
    if camera.button_down:
        selection += 1
        if  selection > 4:
            selection = 1
    if camera.button_sel:
        print('selection = %i' % selection)
        if selection == 1:
            # start access point and time lapse web server
            camera.disp_msg(' access point '+\
                            ' starting.... ')
            os.system('sudo systemctl start wpa_supplicant@ap0.service')
            os.system('cd /home/pi/photos')
            os.system('python3 /home/pi/rpi-camera/camera_server.py')
        elif selection == 2:
            # start home wifi
            camera.disp_msg(' home wifi    '+\
                            ' starting.... ')
            os.system('sudo systemctl start wpa_supplicant@wlan0.service')
        elif selection == 3:
            # do nothing, just exit
            pass
        elif selection == 4:
            # do nothing, just exit
            pass
        camera.disp_msg('     DONE')
        exit()
    update_menu()
    time.sleep(0.1)
