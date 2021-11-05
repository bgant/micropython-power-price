
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

# Download Power Smart Pricing data in html table
def download():
    if time.localtime(tz())[3] >= 16:
        print("Downloading data after 4:30PM Central Time gets tomorrow's pricing... Exiting...")
        exit()
    url = 'https://www.ameren.com/account/retail-energy'
    headers = {'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.get(url, headers=headers)
    psp_file = open(filename, 'wt')
    print(response.content, file=psp_file)
    psp_file.close()
    response.close()
    print(f'{timestamp()} New {filename} file written to disk... Waiting for one minute...')
    time.sleep(65)
    #reset()

# Check that html data is for today
def check_date():
    psp_file_day = re.search('<td id="Date">(.*?)</td>', raw_data)
    if psp_file_day is None:
        print(f'{timestamp()} {filename} is bad... Check URL manually... Exiting...')
        exit()
    elif psp_file_day.group(1) != date_today():
        download()
    #elif psp_file_day.group(1) == date_today():
    #    print(f"{timestamp()} {filename} file is on disk and matches today's date ({psp_file_day.group(1)})")
    #else:
    #    print(f'{timestamp()} Something went wrong... Exiting...')
    #    exit()

# Parse HTML for table data
def parse():
    tbody = re.search('<tbody>(.*?)</tbody>', raw_data)
    td = tbody.group(1).replace('\\n','\n')
    td = td.replace('</td>\n                            ','</td>')
    today = {}
    for line in td.split('\n'):
        hour = re.search('<td id="Hour">(.*?)</td>', line)
        price = re.search('<td id="Price">(.*?)</td>', line)
        if hour is not None:  # <tr>, </tr>, or blank lines
            if isDST():
                today[int(hour.group(1))-1] = float(price.group(1))  # -1 for HE / -0 for CDT (UTC -5) since it is the same as EST (UTC -5)
            else:
                today[int(hour.group(1))-2] = float(price.group(1))  # -1 for HE / -1 for CST (UTC -6) since it is one hour less than EST (UTC -5)
    #print(f"Hour and Price data from today's {filename} file:")
    #print(today)
    return today

# Today's Date in YYYY-MM-DD format
def date_today():
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

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'


############################################
# Initialize HTML Data
############################################

filename = 'psp-data.html'
try:
    psp_file = open(filename, 'rt')
    raw_data = psp_file.read()
    psp_file.close()
except:
    download()

