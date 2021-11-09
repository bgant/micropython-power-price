
############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
import re
from machine import reset
from sys import exit

# Downloaded Micropython Modules
from timezone import tz, isDST
import urequests


############################################
# Define Functions
############################################

# Download Power Smart Pricing data in HTML Table
def download(date=None):
    if time.localtime(tz())[3] >= 16:
        print("WARNING: Downloading data after 4:30PM Central Time gets tomorrow's pricing...")
        exit()  # To avoid download loop because dates to not match
    url = 'https://www.ameren.com/account/retail-energy'
    headers = {'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.get(url, headers=headers)
    raw_data = response.content
    response.close()
    print(f'{timestamp()} New HTML Table downloaded...')
    return str(raw_data)

# Parse HTML Table
#    NOTES: Hours are in Eastern Standard Time (UTC -5)
#           HE in the original MISO data stands for "Hour Ending", so "HE 8" is from 7AM-8AM
def parse(raw_data):
    tbody = re.search('<tbody>(.*?)</tbody>', raw_data)
    td = tbody.group(1).replace('\\n','\n')
    td = td.replace('</td>\n                            ','</td>')
    price_data = {}
    for line in td.split('\n'):
        hour = re.search('<td id="Hour">(.*?)</td>', line)
        price = re.search('<td id="Price">(.*?)</td>', line)
        if hour is not None:  # <tr>, </tr>, or blank lines
            if isDST():
                price_data[int(hour.group(1))-1] = float(price.group(1))  # -1 for HE / -0 for CDT (UTC -5) since it is the same as EST (UTC -5)
            else:
                price_data[int(hour.group(1))-1] = float(price.group(1))  # -1 for HE / -0 for CST (UTC -6) since Ameren shifts data to one hour less than EST (UTC -5) / No 11PM data during CST
    return price_data

# Are we using the correct data for this hour
def date_match(raw_data, date):
    psp_file_day = re.search('<td id="Date">(.*?)</td>', raw_data)
    if psp_file_day is None:
        print(f'{timestamp()} {filename} is bad... Check URL manually... Exiting...')
        exit()
    elif psp_file_day.group(1) == date:
        return True
    else:
        return False

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'

