# MicroPython controlled 433MHz Power Relay using Hourly Electricity Pricing
At my home, I have hourly electricity rates with the Ameren Illinois [Power Smart Pricing](https://www.ameren.com/illinois/account/customer-service/bill/power-smart-pricing) program. 

Ever since signing up for these rates, I have wanted to create a device that would utilize the [hourly pricing data](https://www.ameren.com/illinois/account/customer-service/bill/power-smart-pricing/prices) to automatically turn off a device when rates are high and turn it on again when rates are low. I have finally put together hardware and scripts for charging the batteries in my [Chevrolet Volt](https://en.wikipedia.org/wiki/Chevrolet_Volt).

![Image](images/power.png)

Detailed instructions for setting up an ESP32 or TinyPICO with these script are in the top of the main.py script. 

Everything is written for Central Daylight Time (CDT) and Central Standard Time (CST).
