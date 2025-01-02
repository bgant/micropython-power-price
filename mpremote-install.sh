#!/bin/bash
#
# This script copies all the files needed for this project onto a TinyPICO or TinyS3.
# 
TTY=u0

mpremote $TTY mip install --target= github:bgant/micropython-power-price
mpremote $TTY mip install --target= github:bgant/micropython/modules/key_store.py
mpremote $TTY mip install --target= github:bgant/micropython/modules/wifi.py
mpremote $TTY mip install --target= github:bgant/micropython/modules/webdis.py
mpremote $TTY mip install --target= github:bgant/micropython/modules/timezone.py
mpremote $TTY mip install --target= github:bgant/micropython/modules/TinyPICO_RGB.py
mpremote $TTY mip install --target=tx github:peterhinch/micropython_remote/tx/__init__.py
mpremote $TTY mip install --target=tx github:peterhinch/micropython_remote/tx/get_pin.py
mpremote $TTY mip install --target=tx github:peterhinch/micropython_remote/tx/rp2_rmt.py

