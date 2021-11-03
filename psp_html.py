
############################################
# Import Modules
############################################

# Built-in Micropython Modules
import time
import re
from machine import reset
from sys import exit

# Downloaded Micropython Modules
from timezone import tz
import urequests


############################################
# Data already on Disk?
############################################

filename = 'psp-data.html'
try:
    psp_file = open(filename, 'rt')
    raw_data = psp_file.read()
    psp_file.close()
except:
    download()


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
    print(f'{timestamp()} New {filename} file written to disk... Rebooting in one minute...')
    time.sleep(65)
    reset()

# Check that html data is for today
def check_date():
    psp_file_day = re.search('<td id="Date">(.*?)</td>', raw_data)
    if psp_file_day is None:
        print(f'{timestamp()} {filename} is bad... Check URL manually... Exiting...')
        exit()
    elif int(psp_file_day.group(1).split('-')[2]) != time.localtime(tz())[2]:
        download()
    elif int(psp_file_day.group(1).split('-')[2]) == time.localtime(tz())[2]:
        print(f"{timestamp()} {filename} file is on disk and matches today's date ({psp_file_day.group(1)})")
    else:
        print(f'{timestamp()} Something went wrong... Exiting...')
        exit()

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
