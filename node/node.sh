#!/bin/bash
sudo arp-scan -l | grep "a4:5e:60:dc:8d:77" | awk '{ print $1 }' > config.txt
python node.py
