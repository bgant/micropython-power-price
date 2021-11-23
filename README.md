## MicroPython controlled 433MHz Power Relay using Hourly Electricity Pricing
At my home, I have hourly electricity rates with the Ameren Illinois [Power Smart Pricing](https://www.ameren.com/illinois/account/customer-service/bill/power-smart-pricing) program. 

Ever since signing up for these rates, I have wanted to create a device that would utilize the [hourly pricing data](https://www.ameren.com/illinois/account/customer-service/bill/power-smart-pricing/prices) to automatically turn off a device when rates are high and turn it on again when rates are low. I have finally put together hardware and scripts for charging the batteries in my [Chevrolet Volt](https://en.wikipedia.org/wiki/Chevrolet_Volt).

![Image](images/power.png)

Detailed instructions for setting up an ESP32 or TinyPICO with these script are in the top of the main.py script. 

Everything is written for Central Daylight Time (CDT) and Central Standard Time (CST).

## How I Use This Today

I drive to town almost every day. I am charging from a 120V outlet and with the car set to charge at 12 Amps, it takes about nine hours to fully charge. If I were using a 240V charger, it would take about 4 hours to charge and I could change the settings in the script accordingly to use only the lowest prices of the day.

## Future Plans

I hope to replace my Chevy Volt with a Ford F-150 Lightning. The truck comes with a 240V charger that can also act as a transfer switch to provide electricity to the house from the truck batteries when the main power is down. I would like to use a PLC or some other device with these scripts to transfer house power to the truck when prices are high and recharge the batteries when prices are low.

