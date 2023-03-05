'''
Brandon Gant
Created: 2021-10-11
Updated: 2023-03-03

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

### Software Installation on Linux:
mkdir ~/micropython-setup
cd ~/micropython-setup

python3 -m pip install pyvenv
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip list | egrep -v "Package|----" | awk '{print $1}' | xargs -I {} python3 -m pip install --upgrade {}
python3 -m pip install wheel esptool mpremote
sudo usermod -aG `stat -c "%G" /dev/ttyUSB0` $USER  <-- May need to reboot PC
mpremote connect /dev/ttyUSB0                       <-- test connection / Ctrl-] to exit
  --OR--
mpremote u0

wget https://micropython.org/resources/firmware/tinypico-20210902-v1.17.bin
esptool.py --chip esp32 --port /dev/ttyUSB0 erase_flash
esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 460800 write_flash -z 0x1000 tinypico-20210902-v1.17.bin

wget https://github.com/micropython/micropython-lib/raw/master/python-ecosys/urequests/urequests.py
mpremote u0 cp urequests.py :

git clone https://github.com/peterhinch/micropython-remote
cd micropython-remote/
mpremote u0 cp -r tx/ :

cd ../
git clone https://github.com/bgant/micropython-wifi
cd micropython-wifi/
mpremote u0 cp key_store.py :
mpremote u0 cp timezone.py :
mpremote u0 cp TinyPICO_RGB.py :
mpremote u0 cp boot.py :
mpremote u0  <-- to enter REPL
from machine import reset
reset()
<enter your Wifi SSID and Password and make sure it connects>
<if you made a mistake run import key_store and key_store.init() to change SSID and Password>
<Ctrl+] to exit REPL>

cd ../
git clone https://github.com/bgant/micropython-power-price
cd micropython-power-price/
mpremote u0 cp 433MHz_Dewenwils_RC-042_E211835.json :
mpremote u0 cp psp_csv.py :   <-- OR psp_json.py OR psp_html.py 
mpremote u0 cp main.py :

mpremote u0  <-- to enter REPL
reset()      <-- boot.py and main.py should run
'''


#-----------------------
# Script Configuration
#-----------------------

# How do you want to download data? [CSV, JSON, HTML]
download = 'CSV'

# How many Daily Price Averages do you want to use? [1-7]
days = 1

# Below what Price should power always be turned on?
min = 0.04

# Above what Price should power always be turned off?
max = 0.09

# By default, power is turned off if the Price is higher than the Average (50%).
# Do you want to cutoff the power at a higher or lower Percentage? [0-100]
percent = 60


#-----------------
# Import Modules
#-----------------

# Built-in Micropython Modules
from machine import reset, WDT
from sys import exit
import time
import json
import ntptime
import gc

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
if download.lower() is 'csv':
    import psp_csv as psp    # Original data from MISO source
elif download.lower() is 'json':
    import psp_json as psp  # Ameren API / No 11PM data during CST
elif download.lower() is 'html':
    import psp_html as psp  # Ameren Website / Tomorrow's data after 4:30PM / No 11PM data during CST
else:
    print(f'{download} is not a valid download mechanism... Exiting')
    exit()


#-------------------
# Define Functions
#-------------------

# Calculate Average Price for Today
def daily_average(price_data):
    average = 0.0
    for hour in price_data:
        average += float(price_data[hour])
    average /= len(price_data)  # Price easily affected by high/low outliers
    return average

# Update weekly_averages dictionary to key_store.db
def weekly_average_write(price_data):
    try:
        weekly_averages = key_store.get('weekly_averages')
        weekly_averages = json.loads(weekly_averages)
        weekly_averages[time.localtime(tz())[6]] = daily_average(price_data)  # Add Today's Average Price
    except:
        # Initialize variable if not in Key Store data
        weekly_averages = {}
        weekly_averages[time.localtime(tz())[6]] = daily_average(price_data)  # Add Today's Average Price
    key_store.set('weekly_averages', str(weekly_averages))

# Read weekly_averages dictionary from key_store.db and average
# the prices across X number of days where X is 1 to 7 days
def weekly_average_read(days=7, percentage=50):
    weekly_averages = key_store.get('weekly_averages')    
    weekly_averages = json.loads(weekly_averages)
    price = 0.0
    for n in range(0, days):
        if n == days: break
        price += weekly_averages[(time.localtime(tz())[6]-n)%7]
    price /= days
    price_with_percentage = (price * ((percentage - 50)/100)) + price
    return price_with_percentage

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

# TinyPICO has an RGB LED so let's use it
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
def power(price_data, hour, price_cutoff, min, max):
    if price_data[hour] <= min or price_data[hour] <= price_cutoff:
        print(f'{timestamp()} Hour {hour:02} Price {price_data[hour]:.3f} is  lower than {min:.3f} minimum or {price_cutoff:.3f} cutoff... Turning power ON')
        led('green')
        transmit('on')
    elif price_data[hour] > max or price_data[hour] > price_cutoff:
        print(f'{timestamp()} Hour {hour:02} Price {price_data[hour]:.3f} is higher than {max:.3f} maximum or {price_cutoff:.3f} cutoff... Turning power OFF')
        led('red')
        transmit('off')
    else:
        print(f'Not sure what happened with price {price_data[hour]}')
        led('off')
        transmit('off')

# Test a specific UTC date using a timestamp with psp_csv.py or psp_json.py (NOT psp_html.py) 
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
#debug(689428800)  # time.mktime((2021,11,5,12,0,0,0,0)) to get UTC timestamp


#---------------------
# Initialize on boot
#---------------------

# Load file containing 433MHz transmit codes
# Source: https://github.com/peterhinch/micropython_remote
try:
    transmit = TX(pin(), '433MHz_Dewenwils_RC-042_E211835.json')
except:
    print('JSON File containing 433MHz codes is missing... Exiting...')
    exit()

wdt = WDT(timeout=600000)                         # Set 10-minute Hardware Watchdog Timer
raw_data = psp.download(date())                   # Download the data on boot
price_data = psp.parse(raw_data)                  # Parse raw_data into hour:price dictionary

weekly_average_write(price_data)                  # Write Average Price to Key Store
price_cutoff = weekly_average_read(days, percent) # Use Weekly Average Price from Key Store

power(price_data, price_hour(), price_cutoff, min, max)  # Turn ON/OFF now at boot


#------------
# Main Loop
#------------

def handleInterrupt(timer):
    global weekly_average_write  # Now that this is a function, 
    global price_cutoff          # need to use the global values
    global raw_data              # for all variables instead of creating
    global price_data            # new ones each time this function runs
    global min
    global max
    if is_top_of_hour():
        # 1AM update weekly average data
        if price_hour() == 0:
            weekly_average_write(price_data)
            price_cutoff = weekly_average_read(days, percent)
        # 10PM fix daily clock drift
        if price_hour() == 22:
            ntptime.settime()
        # Download new data if current hour's date does not match data's date
        if not psp.date_match(raw_data, date()):
            raw_data = psp.download(date())
            price_data = psp.parse(raw_data)
        power(price_data, price_hour(), price_cutoff, min, max)
        gc.collect()  # Just in case
    else:
        #print('not top of hour yet')
        wdt.feed()    # Reset Hardware Watchdog Timer

# ESP32 has four hardware timers to choose from (0 through 3)
from machine import Timer
timer = Timer(0)

# period in milliseconds
timer.init(period=60000, mode=Timer.PERIODIC, callback=handleInterrupt)
# Stop with: timer.deinit()
# View with: timer.value()
# View list of variables in memory with: dir()
