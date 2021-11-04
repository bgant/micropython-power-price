
############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
from machine import reset
from sys import exit

# Downloaded Micropython Modules
from timezone import tz
import urequests


############################################
# Define Functions
############################################

# Download Power Smart Pricing data in JSON via API
def download():
    url = 'https://www.ameren.com/api/ameren/promotion/RtpHourlyPricesbyDate'
    date = {"SelectedDate":date_today()}
    headers = {'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.post(url, headers=headers, json=date)
    if response.status_code is 200:
        data = response.json()
        print(f'{timestamp()} New JSON data downloaded... Waiting one minute before continuing...')
    else:
        print(f'{timestamp()} Download failed with HTTP Status Code {response.status_code}... Not sure what to do...')
    response.close()
    time.sleep(65)
    return data

# Check that JSON data is for today
def check_date():
    global raw_data
    date_json = raw_data['hourlyPriceDetails'][0]['date'].strip('T00:00:00')   # YYYY-MM-DD
    if date_json != date_today():
        raw_data = download()
        reset()
    elif date_json == date_today():
        print(f"{timestamp()} JSON data today's date ({date_today()})")
    else:
        print(f'{timestamp()} Something went wrong... Exiting...')
        exit()

# Parse JSON data
#    NOTES: Hours are in Eastern Standard Time (UTC -5)
#           HE in the original MISO data stands for "Hour Ending", so "HE 8" is from 7AM-8AM
def parse():
    global raw_data
    today = {}
    for n in range(0,24):
        hour = raw_data['hourlyPriceDetails'][n]['hour']
        price = raw_data['hourlyPriceDetails'][n]['price']
        if tz(format='bool'):
            today[int(hour)-1] = float(price)  # -1 for HE / -0 for CDT (UTC -5) since it is the same as EST (UTC -5)
        else:
            today[int(hour)-2] = float(price)  # -1 for HE / -1 for CST (UTC -6) since it is one hour less than EST (UTC -5)
    return today

# Today's Date in YYYY-MM-DD format
def date_today():
    today = time.localtime(tz())
    tomorrow = time.localtime(tz()+86400)
    # CDT/EST data or CST/EST data but not 11PM
    if tz(format='bool') or (not tz(format='bool') and today[3] != 23):
        return f'{today[0]}-{today[1]:02}-{today[2]:02}'
    # CST/EST Hour 23 (11PM) is in tomorrow's data (hour -1)
    elif (not tz(format='bool')) and (today[3] == 23):
        return f'{tomorrow[0]}-{tomorrow[1]:02}-{tomorrow[2]:02}'
    else:
        print("Something went wrong with the date_today() function...")
        exit()

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'


############################################
# Initialize JSON Data
############################################

raw_data = download()  # Access from main.py with psp.raw_data


