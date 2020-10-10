import time
import os
import board
from digitalio import DigitalInOut, Direction, Pull
import adafruit_pcd8544 as LCD

# GPIO pins for 5 way navigation switch
BTN_UP              =   board.D19      # Up
BTN_DOWN            =   board.D16      # Down
BTN_LEFT            =   board.D26      # Left
BTN_RIGHT           =   board.D20      # Right
BTN_SEL             =   board.D21      # Select (push)

# GPIO pins for Nokia LCD display control
LCD_DC              =   board.D23      # Nokia LCD display D/C
LCD_CS              =   board.D8       # Nokia LCD display CS
LCD_RST             =   board.D24      # Nokia LCD displat Reset
LCD_LED             =   board.D22      # LCD LED enable pin (HIGH=ON, LOW=OFF)
LCD_CONTRAST        =   50             # LCD contrast 0-100

# the display
disp = LCD.PCD8544( board.SPI(),
                    DigitalInOut(LCD_DC),
                    DigitalInOut(LCD_CS),
                    DigitalInOut(LCD_RST) )
disp.fill(0)
disp.show()
disp.contrast = LCD_CONTRAST

# the backlight
backlight = DigitalInOut(LCD_LED)
backlight.direction = Direction.OUTPUT
backlight.value = True

# the nav switch buttons
button_up = DigitalInOut(BTN_UP)
button_down = DigitalInOut(BTN_DOWN)
button_left = DigitalInOut(BTN_LEFT)
button_right = DigitalInOut(BTN_RIGHT)
button_sel = DigitalInOut(BTN_SEL)
buttons = (button_up, button_down, button_left, button_right, button_sel)
for button in buttons:
    button.direction = Direction.INPUT
    button.pull = Pull.UP

def update_display(wifi):
    disp.fill(0)
    disp.text((" AP ", "WIFI")[wifi], 28, 20, 1)
    disp.show()

WIFI = 0
update_display(WIFI)

while True:

    while button_sel.value:
        if not button_left.value:
            backlight.value = True
            WIFI -= 1
            WIFI = WIFI if WIFI >= 0 else 1
            time.sleep(0.25)
            update_display(WIFI)
        if not button_right.value:
            backlight.value = True
            WIFI += 1
            WIFI = WIFI if WIFI <= 1 else 0
            time.sleep(0.25)
            update_display(WIFI)

    if WIFI == 0:
        os.system('sudo systemctl start wpa_supplicant@ap0.service')
    elif WIFI == 1:
        os.system('sudo systemctl start wpa_supplicant@wlan0.service')

    print("WIFI =", WIFI)
    backlight.value = False
