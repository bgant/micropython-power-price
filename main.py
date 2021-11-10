'''
Brandon Gant
Created: 2021-10-11
Updated: 2021-11-09

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

wget https://github.com/micropython/micropython-lib/raw/master/python-ecosys/urequests/urequests.py
mpremote cp urequests.py :

git clone https://github.com/peterhinch/micropython-remote
cd micropython-remote/
mpremote cp -r tx/ :

cd ../
git clone https://github.com/bgant/micropython-wifi
cd micropython-wifi/
mpremote cp key_store.py :
mpremote cp timezone.py :
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
mpremote cp psp_csv.py :   <-- OR psp_json.py OR psp_html.py 
mpremote cp main.py :

mpremote  <-- to enter REPL
reset()   <-- boot.py and main.py should run
'''

############################################
# Import Modules
############################################

# Built-in Micropython Modules
from machine import reset, WDT
from sys import exit
import time
import json
import ntptime

# A chance to hit Ctrl+C in REPL for Debugging
print('main.py: Press CTRL+C to enter REPL...')
print()
time.sleep(2) 

# Downloaded Micropython Modules
from timezone import tz, isDST
from tx import TX
from tx.get_pin import pin
import TinyPICO_RGB

# Choose a single data download mechanism
import psp_csv as psp    # Original MISO source
#import psp_json as psp  # Ameren API / No 11PM data during CST
#import psp_html as psp  # Ameren Website / Tomorrow's data after 4:30PM / No 11PM data during CST


############################################
# Define Functions
############################################

# Calculate Average Price for Today
def price_average(price_data):
    average = 0.0
    for hour in price_data:
        average += float(price_data[hour])
    average /= len(price_data)  # Price easily affected by high/low outliers
    return average

# Update weekly Price average data to disk
def weekly_average_write(price_data):
    try:
        weekly_averages = key_store.get('weekly_averages')
        weekly_averages = json.loads(weekly_averages)
        weekly_averages[time.localtime(tz())[6]] = price_average(price_data)  # Add Today's Average Price
    except:
        # Initialize variable if not in Key Store data
        weekly_averages = {}
        weekly_averages[time.localtime(tz())[6]] = price_average(price_data)  # Add Today's Average Price
    key_store.set('weekly_averages', str(weekly_averages))

# Read weekly Price data from disk
def weekly_average_read():
    weekly_averages = key_store.get('weekly_averages')    
    weekly_averages = json.loads(weekly_averages)
    price = 0.0
    for day in weekly_averages:
        price += weekly_averages[day]
    price /= len(weekly_averages)
    return price

# Date in YYYY-MM-DD format
def date():
    today = time.localtime(tz())
    tomorrow = time.localtime(tz()+86400)
    # CDT/EST data or CST/EST data but not 11PM
    if isDST() or (not isDST() and today[3] != 23):
        return f'{today[0]}-{today[1]:02}-{today[2]:02}'
    # CST/EST Hour 23 (11PM) is in tomorrow's data (hour -1)
    elif (not isDST()) and (today[3] == 23):
        return f'{tomorrow[0]}-{tomorrow[1]:02}-{tomorrow[2]:02}'
    else:
        print("Something went wrong with the date_today() function...")
        exit()

# Align CST/CDT hours with price_data hours
def price_hour():
    if (not isDST()) and time.localtime(tz())[3] == 23:
        hour = -1  # Set 11PM CST to Hour -1 in price_data
    else:
        hour = time.localtime(tz())[3]  # All other CST/CDT hours line up with price_data
    return hour

# Only turn Power ON/OFF at the top of each hour
def is_top_of_hour():
    if time.localtime()[4] == 0:  # Minute 00 in any timezone
        return True
    else:
        return False

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'

def led(color):
    if color == 'yellow':
        TinyPICO_RGB.solid(100,100,0)
    elif color == 'green':
        TinyPICO_RGB.solid(0,100,0)
    elif color == 'red':
        TinyPICO_RGB.solid(100,0,0)
    else:
        TinyPICO_RGB.off()

# Turn 433MHz Power Relay ON/OFF
def power(price_data, hour, max=0.09):
    if price_data[hour] < weekly_average and price_data[hour] < max:
        print(f'{timestamp()} Hour {hour:02} Price {price_data[hour]:.3f} is  lower than {weekly_average:.3f} Weekly Average and {max:.3f} Max... Turning power ON')
        led('green')
        transmit('on')
    else:
        print(f'{timestamp()} Hour {hour:02} Price {price_data[hour]:.3f} is higher than {weekly_average:.3f} Weekly Average  or {max:.3f} Max... Turning power OFF')
        led('yellow')
        transmit('off')

def debug(timestamp):
    t = time.localtime(tz(timestamp))
    date = f'{t[0]}-{t[1]:02}-{t[2]:02}'
    print(f'DEBUG BEGIN: Timestamp {timestamp} for {date} isDST={isDST(timestamp)}')
    raw_data = psp.download(date)
    price_data = psp.parse(raw_data, debug_time=timestamp)
    print(price_data)
    print(f'DEBUG EXIT')
    print()
    exit()


############################################
# Initialize on boot
############################################

# Load file containing 433MHz transmit codes
# Source: https://github.com/peterhinch/micropython_remote
try:
    transmit = TX(pin(), '433MHz_Dewenwils_RC-042_E211835.json')
except:
    print('JSON File containing 433MHz codes is missing... Exiting...')
    exit()

#debug(689428800)                       # time.mktime((2021,11,5,12,0,0,0,0)) to get UTC timestamp
wdt = WDT(timeout=600000)               # 10-minute Hardware Watchdog Timer
raw_data = psp.download(date())         # Download the data on boot
price_data = psp.parse(raw_data)        # Parse raw_data into hour:price dictionary
weekly_average_write(price_data)        # Write Average Price to Key Store
weekly_average = weekly_average_read()  # Read Weekly list of Average Prices from Key Store
power(price_data, price_hour())         # Turn Power ON/OFF Based on Current Hour Price
time.sleep(65)                          # Wait a bit before jumping into While loop


############################################
# Main Loop
############################################

while True:
    if is_top_of_hour():
        if price_hour() == 1:  # 1AM update weekly average data
            weekly_average_write(price_data)
            weekly_average = weekly_average_read()
        if price_hour() == 22: # 10PM fix clock drift
            ntptime.settime()
        if not psp.date_match(raw_data, date()):
            raw_data = psp.download(date())
            price_data = psp.parse(raw_data)
        power(price_data, price_hour())
        time.sleep(65) 
    else:
        wdt.feed()  # Reset Hardware Watchdog Timer
        time.sleep(30)

