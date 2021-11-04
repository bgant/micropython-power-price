
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
def parse():
    global raw_data
    today = {}
    for n in range(0,24):
        hour = raw_data['hourlyPriceDetails'][n]['hour']
        price = raw_data['hourlyPriceDetails'][n]['price']
        if tz(format='bool'):
            today[int(hour)] = float(price)    # CDT is the same as EST (UTC -5)
        else:
            today[int(hour)-1] = float(price)  # CST is one hour less than EST 
    return today

# Today's Date in YYYY-MM-DD format
def date_today():
    return f'{time.localtime(tz())[0]}-{time.localtime(tz())[1]:02}-{time.localtime(tz())[2]:02}'

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'


############################################
# Initialize JSON Data
############################################

raw_data = download()  # Access from main.py with psp.raw_data


