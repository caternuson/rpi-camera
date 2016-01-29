#!/usr/bin/python
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
import campi
import time
import os

camera = campi.Campi()

selection = 1

          #01234567890123
BLANK   = ' [ ] '
CHECKED = ' [X] '
MENU1   =      'HOME WIFI'
MENU2   =      'AP WIFI  '
MENU3   =      'NO WIFI  '
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
    button_state = camera.get_buttons()
    if (button_state[campi.BTN_UP]):
        selection -= 1
        if (selection<1):
            selection = 4
    if (button_state[campi.BTN_DOWN]):
        selection += 1
        if (selection>4):
            selection = 1
    if (button_state[campi.BTN_SEL]):
        print 'selection = %i' % selection
        if (selection==1):
            # start home wifi
            camera.disp_msg(' home wifi    '+\
                            ' starting.... ')
            os.system('python /home/pi/start_homewifi.py')
        if (selection==2):
            # start access point and time lapse web server
            camera.disp_msg(' access point '+\
                            ' starting.... ')            
            os.system('python /home/pi/start_ap.py')
            os.system('cd /home/pi/rpi-camera')
            os.system('python /home/pi/rpi-camera/camera_server.py')
        if (selection==3):
            # start non-wifi menu driven time lapse
            os.system('python /home/pi/rpi-camera/camera_timelapse.py')
        if (selection==4):
            # do nothing, just exit
            pass
        camera.disp_msg('     DONE')
        exit()
    update_menu()    
    time.sleep(0.1)
