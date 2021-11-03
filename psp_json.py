
############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
from machine import reset
from sys import exit
import json

# Downloaded Micropython Modules
from timezone import tz
import urequests


############################################
# Data already on Disk?
############################################

# Converting JSON to a string in a file and
# then converting it back again is too much work


############################################
# Define Functions
############################################

# Download Power Smart Pricing data in JSON via API
def download():
    url = 'https://www.ameren.com/api/ameren/promotion/RtpHourlyPricesbyDate'
    date = {"SelectedDate":"2021-11-03"}
    headers = {'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.post(url, headers=headers, json=date)
    if response.status_code == '200':
        raw_data = response.json()
        print(f'{timestamp()} New JSON data downloaded... Waiting one minute before continuing...')
        return raw_data
    else:
        print(f'{timestamp()} Download failed with HTTP Status Code {response.status_code}... Not sure what to do...')
    response.close()
    time.sleep(65)

# Check that JSON data is for today
def check_date():
    try: 
        date_json = raw_data['hourlyPriceDetails'][0]['date'].strip('T00:00:00')   # YYYY-MM-DD
    except:
        raw_data = download()
    date_today = f'{time.localtime(tz())[0]}-{time.localtime(tz())[1]}-{time.localtime(tz())[2]}'

    if date_json != date_today:
        raw_data = download()
    elif date_json == date_today:
        print(f"{timestamp()} JSON data today's date ({date_today})")
    else:
        print(f'{timestamp()} Something went wrong... Exiting...')
        exit()

# Parse JSON data
def parse():
    today = {}
    for line in td.split('\n'):
        hour = re.search('<td id="Hour">(.*?)</td>', line)
        price = re.search('<td id="Price">(.*?)</td>', line)
        if hour is not None:  # <tr>, </tr>, or blank lines
            if tz(format='bool'):
                today[int(hour.group(1))] = float(price.group(1))    # CDT is the same as EST (UTC -5)
            else:
                today[int(hour.group(1))-1] = float(price.group(1))  # CST is one hour less than EST 
    #print(f"Hour and Price data from today's {filename} file:")
    #print(today)
    return today

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'


raw_data = download()


#r.json()
#r.json()['isNextDay']
#r.json()['hourlyPriceDetails'][0]
