'''
Brandon Gant
Created: 2021-10-11
Updated: 2021-10-13

### Overview:
I am signed up for Hourly Electricity Pricing. I created this project
to charge the batteries in my electric vehicle when hourly prices are 
low and turn off charging when prices are high.

### Hardware:
TinyPICO (https://www.tinypico.com/buy) or any ESP32 device
FS1000A 433MHZ RF transmitter (https://www.amazon.com/dp/B01DKC2EY4)
Dewenwils RC-042 433MHz Relay (https://www.amazon.com/dp/B07W53C4FQ)

### Wiring:
TinyPICO GND <--> FS1000A GND
TinyPICO  23 <--> FS1000A Data (middle pin)
TinyPICO 3V3 <--> FS1000A VCC 
20Amp 120V Wall Outlet <--> 15Amp 433MHz Dewenwils Relay <--> 12Amp Chevy Volt car charger

### Software Installation:
mkdir ~/micropython-build
cd ~/micropython-build

python3 -m pip install pyvenv
python3 -m venv ~/micropython-env
source micropython-env/bin/activate
python3 -m pip list | egrep -v "Package|----" | awk '{print $1}' | xargs -I {} python3 -m pip install --upgrade {}
python3 -m pip install esptool
python3 -m pip install mpremote

wget https://micropython.org/resources/firmware/tinypico-20210902-v1.17.bin
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 tinypico-20210902-v1.17.bin

wget https://github.com/micropython/micropython-lib/raw/master/micropython/urllib.urequest/urllib/urequest.py
mpremote cp urequest.py :

git clone https://github.com/peterhinch/micropython-remote
cd micropython-remote/
mpremote cp -r tx/ :

cd ../
git clone https://github.com/bgant/micropython-wifi
cd micropython-wifi/
mpremote cp key_store.py :
mpremote cp timezone.py :
mpremote cp soft_wdt.py :
mpremote cp TinyPICO_RGB.py :
mpremote cp boot.py :
mpremote  <-- to enter REPL
from machine import reset
reset()
<enter your Wifi SSID and Password and make sure it connects>
<if you made a mistake run import key_store and key_store.init() to change SSID and Password>
<Ctrl+] to exit REPL>

cd ../
git clone https://github.com/bgant/micropython-power-price
cd micropython-power-price/
mpremote cp 433MHz_Dewenwils_RC-042_E211835.json :
mpremote cp main.py :

mpremote  <-- to enter REPL
reset()   <-- boot.py and main.py should run
'''

############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
import re
from machine import reset
from sys import exit

# A chance to hit Ctrl+C in REPL for Debugging
print('main.py: Press CTRL+C to enter REPL...')
print()
time.sleep(2) 

# Downloaded Micropython Modules
import urequest
from timezone import tz
from tx import TX
from tx.get_pin import pin


############################################
# Define Functions
############################################

# Download Power Smart Pricing data (after 5:30PM you get tomorrow's data)
def psp_download():
    response = urequest.urlopen('https://www.ameren.com/account/retail-energy')
    psp_file = open('retail-energy.html', 'wt')
    print(response.read(), file=psp_file)
    psp_file.close()
    print(f'{timestamp()} New retail-energy.html file written to disk... Rebooting in one minute...')
    time.sleep(65)
    reset()

# Check that retail-energy.html data is for today
def check_date():
    psp_file_day = re.search('<td id="Date">(.*?)</td>', html)
    if psp_file_day is None:
        print(f'{timestamp()} retail-energy.html is bad... Check URL manually... Exiting...')
        exit()
    elif int(psp_file_day.group(1).split('-')[2]) > time.localtime(tz())[2]:
        print(f'{timestamp()} Accessing the site after 5:30PM gets tomorrows data... Exiting...')
        exit()
    elif int(psp_file_day.group(1).split('-')[2]) < time.localtime(tz())[2]:
        psp_download()
    elif int(psp_file_day.group(1).split('-')[2]) == time.localtime(tz())[2]:
        print(f"{timestamp()} retail-energy.html file is on disk and matches today's date ({psp_file_day.group(1)})")
    else:
        print(f'{timestamp()} Something went wrong... Exiting...')
        exit()

# Parse HTML for table data
def psp_parse():
    tbody = re.search('<tbody>(.*?)</tbody>', html)
    td = tbody.group(1).replace('\\n','\n')
    td = td.replace('</td>\n                            ','</td>')
    today = {}
    for line in td.split('\n'):
        hour = re.search('<td id="Hour">(.*?)</td>', line)
        price = re.search('<td id="Price">(.*?)</td>', line)
        if hour is not None:  # <tr>, </tr>, or blank lines
            today[int(hour.group(1))] = float(price.group(1))
    #print("Hour and Price data from today's retail-energy.html file:")
    print(today)
    return today

# Calculate Average Price for Today
def psp_average():
    average = 0.0
    for hour in today:
        average += float(today[hour])
    average /= len(today)  # Price easily affected by high/low outliers
    print(f'Average Price Today: {average:.3f}')
    return average

# Calculate Median (middle) Price for Today
def psp_median():
    median_list = []
    for hour in today:
        median_list.append(today[hour])
    median_list.sort()
    median = float(median_list[int(len(median_list)/2)])  # Price in center of sorted list of Prices
    print(f' Median Price Today: {median:.3f}')
    return median

# Turn 433MHz Power ON/OFF if less than Average, Median, and Max Price
def psp_power(max=0.7):
    if today[hour] < average and today[hour] < median and today[hour] < max:
        print(f'{timestamp()} Hour {hour:02} Price of {today[hour]:.3f} is  lower than Average, Median, and Max price... Turning power ON')
        transmit('on')
    else:
        print(f'{timestamp()} Hour {hour:02} Price of {today[hour]:.3f} is higher than Average, Median, and Max price... Turning power OFF')
        transmit('off')

# Align time.localtime midnight (0) to retail-energy.html midnight (24)
# (keep in mind that Hour 24 is actually midnight for the next day)
def midnight_fix():
    if time.localtime(tz())[3] == 0:
        hour = 24
    else:
        hour = time.localtime(tz())[3]
    return hour

# Download new data at 1AM
def is1AM():
    if time.localtime(tz())[3] == 1:
        return True
    else:
        return False

# Only turn Power ON/OFF at the top of each hour
def isTopOfHour():
    if time.localtime()[4] == 0:  # Minute 00 / No need for lftime CST/CDT hours
        return True
    else:
        return False

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'


############################################
# Initialize on boot
############################################

# Load file containing 433MHz transmit codes
# Source: https://github.com/peterhinch/micropython_remote
try:
    transmit = TX(pin(), '433MHz_Dewenwils_RC-042_E211835.json')
except:
    print('JSON File containing 433MHz codes is missing... Exiting...')
    print()
    exit()

# Read retail-energy.html file if it is already on disk
try:
    psp_file = open('retail-energy.html', 'rt')
    html = psp_file.read()
    psp_file.close()
except:
    psp_download()

check_date()             # Verify data in retail-energy.html is for today
today = psp_parse()      # Parse Table in retail-energy.html into dictionary
average = psp_average()  # Calculate Average Price Today
median = psp_median()    # Calculate Median (middle) Price Today
hour = midnight_fix()    # Align time.localtime (0) and retail-energy.html (24) midnight hours
psp_power()              # Turn Power ON/OFF Based on Current Hour Price
time.sleep(30)           # Wait a bit before jumping into While loop


############################################
# Main Loop
############################################

while True:
    if isTopOfHour():
        if is1AM():
            check_date()  # At 1:00AM download new data, reboot, and re-initialize variables
        hour = midnight_fix() 
        psp_power()
        time.sleep(65) 
    else:
        #print('sleep')
        time.sleep(30)

