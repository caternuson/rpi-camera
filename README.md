# rpi-camera
![thumbnail](http://caternuson.github.io/rpi-camera/static/rpi-camera-thumb.jpg)<br/>
Python 2.7 software for Raspberry Pi based camera.

# Hardware
* [Raspberry Pi Model A+](https://www.raspberrypi.org/products/model-a-plus/)
* [Raspberry Pi Camera Module v1](https://www.raspberrypi.org/products/camera-module/)
* [Adafruit USB wifi dongle](https://www.adafruit.com/products/814)
* [Adafruit Nokia LCD display](https://www.adafruit.com/products/338)
* [Adafruit PowerBoost 500 Charger](https://www.adafruit.com/products/1944)
* [Adafruit 2200mAh lion battery](https://www.adafruit.com/products/1781)
* [Adafruit 5 way navigation switch](https://www.adafruit.com/products/504)
* Canon WP-DC20 Waterproof Case

# Software
A brief description of the various software components.
* ```camera_server.py``` - provides a web interface for performing timelapses
* ```campi.pi``` - defines a class for interfacing with the hardware
* ```timelapser.py``` - defines a thread class for performing a timelapse
* ```mjpgstream_thread.py``` - defines a thread class for serving a MJPEG stream
* ```boot_menu.py``` - can be run at boot to bring camera up in various modes

# Dependencies
*  ```picamera``` for Python access to camera module
    * https://picamera.readthedocs.io
*  ```Adafruit Nokia LCD library``` for LCD display
    * https://github.com/adafruit/Adafruit_Nokia_LCD
*  ```Adafruit Python GPIO``` - for GPIO access
    * https://github.com/adafruit/Adafruit_Python_GPIO

# Wifi Access Point Setup
This project uses **hostapd** to run the wifi in access point mode. The
USB wifi donlge I used had the RTL8188CUS chipset, which required a custom
build of hostapd. Here's what I did:
* Download zip file from [here](http://www.realtek.com.tw/downloads/downloadsView.aspx?Langid=1&PNid=21&PFid=48&Level=5&Conn=4&DownTypeID=3&GetDown=false)
    * Choose RTL8188CUS, click GO, download Unix (Linux) driver
    * filename: RTL8188C_8192C_USB_linux_v4.0.2_9000.20130911.zip
* unzip that file
* go to  /RTL8188C_8192C_USB_linux_v4.0.2_9000.20130911/wpa_supplicant_hostapd/wpa_supplicant_hostapd-0.8_rtw_r7475.20130812/hostapd
* make and install by running
```
make
sudo make install
```
* this should put the files **hostapd** and **hostapd_cli** in **/usr/local/bin**
* rename existing hostapd and add links to custom build
```
sudo mv /usr/sbin/hostapd /usr/sbin/hostapd.bak 
sudo ln -s /usr/local/bin/hostapd /usr/sbin/hostapd 
sudo chown root:root /usr/sbin/hostapd 
sudo chmod 755 /usr/sbin/hostapd
```
* then configure by editting the file **/etc/hostapd/hostapd.conf** to have
contents similar to:
```
interface=wlan0
ssid=picamera
hw_mode=g
channel=6
auth_algs=1
wmm_enabled=0
```

# DHCP Server Setup
I initially tried **udchpd** but could not get it to work. I switched to
**isc-dhcp-server** which worked. Luckily, this is easy to install:
```
sudo apt-get install isc-dhcp-server
```
Then update the following line in file **/etc/default/isc-dhcp-server**:
```
INTERFACES="wlan0"
```

# Start AP and DHCP Services
Once the above have been installed and configured, start them:
```
sudo service hostapd start
sudo service isc-dhcp-server start
```
**NOTE:** this is sysv init style, systemd will be different.

# Installing rpi-camera
Once you've installed the above dependencies and have them working,
simply clone this repo and run the server:
```
$ git clone https://github.com/caternuson/rpi-camera.git
$ cd rpi-camera
$ sudo python camera_server.py
```