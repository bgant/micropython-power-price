
#-----------------
# Import Modules
#-----------------

# Built-in Micropython Modules
import time
import re
from machine import reset
from sys import exit

# Downloaded Micropython Modules
from timezone import tz, isDST
import urequests


#-------------------
# Define Functions
#-------------------

# Download Power Smart Pricing data in CSV Format from MISO
def download(date):
    url = f"https://docs.misoenergy.org/marketreports/{date.replace('-','')}_da_expost_lmp.csv"
    headers = {'Range': 'bytes=0-40000', 'User-Agent': 'https://github.com/bgant/micropython-power-price'}
    response = urequests.get(url, headers=headers)
    raw_data = str(response.content)  # Only downloaded the bytes Range needed to reducing processing time
    response.close()
    lines = raw_data.split('\\n')
    for line in lines:
        if '/' in line:
            miso_date = line
        elif 'AMIL.BGS5' in line:
            if 'Loadzone' in line:
                if 'LMP' in line:
                    csv = line 
    print(f'{timestamp()} New {date} MISO CSV data downloaded...')
    return f'{miso_date},{csv}'

# Parse MISO CSV Data
#    NOTES: Hours are in Eastern Standard Time (UTC -5)
#           HE in the original MISO data stands for "Hour Ending", so "HE 8" is from 7AM-8AM
def parse(raw_data, debug_time=None):
    price_data = {}
    items = raw_data.split(',')
    for n in range(0,24):
        if isDST(debug_time):
            price_data[n] = float(items[n+4])/1000  # -1 for HE / -0 for CDT (UTC -5) since it is the same as EST (UTC -5)
        else:
            price_data[n-1] = float(items[n+4])/1000  # -1 for HE / -1 for CST (UTC -6) since it is one hour less than EST (UTC -5)
    return price_data

# Are we using the correct data for this hour
def date_match(raw_data, date):
    items = raw_data.split(',')
    csv_date = items[0]
    csv_date = csv_date.split('/')
    csv_date = f'{csv_date[2]}-{csv_date[0]}-{csv_date[1]}'
    if csv_date == date:
        return True
    else:
        return False

# Timestamp for debugging
def timestamp():
    return f'[{time.localtime(tz())[3]:02}:{time.localtime(tz())[4]:02}:{time.localtime(tz())[5]:02}]'

