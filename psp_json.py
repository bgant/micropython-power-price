
############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
from machine import reset
from sys import exit

# Downloaded Micropython Modules
from timezone import tz, isDST
import urequests


############################################
# Define Functions
############################################

# Download Power Smart Pricing data in JSON via API
def download(date):
    url = 'https://www.ameren.com/api/ameren/promotion/RtpHourlyPricesbyDate'
    json = {"SelectedDate":date}
    headers = {'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.post(url, headers=headers, json=json)
    if response.status_code is 200:
        data = response.json()
        print(f'{timestamp()} New {date} JSON data downloaded...')
    else:
        print(f'{timestamp()} Download {date} failed with HTTP Status Code {response.status_code}... Not sure what to do...')
        exit()
    response.close()
    return data

# Parse JSON data
#    NOTES: Hours are in Eastern Standard Time (UTC -5)
#           HE in the original MISO data stands for "Hour Ending", so "HE 8" is from 7AM-8AM
def parse(raw_data, debug_time=None):
    price_data = {}
    for n in range(0,24):
        hour = raw_data['hourlyPriceDetails'][n]['hour']
        price = raw_data['hourlyPriceDetails'][n]['price']
        if isDST(debug_time):
            price_data[int(hour)-1] = float(price)  # -1 for HE / -0 for CDT (UTC -5) since it is the same as EST (UTC -5)
        else:
            price_data[int(hour)-1] = float(price)  # -1 for HE / -0 for CST (UTC -6) since Ameren shifts data to one hour less than EST (UTC -5) / No 11PM data during CST
    return price_data

# Are we using the correct data for this hour
def date_match(raw_data, date):
    date_json = raw_data['hourlyPriceDetails'][0]['date'].strip('T00:00:00')   # YYYY-MM-DD
    if date_json == date:
        return True
    else:
        return False

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'

