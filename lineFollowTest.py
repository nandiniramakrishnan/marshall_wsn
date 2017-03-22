#!/usr/bin/python
# ========================================================
# Python script for PiBot-A: line follower
# Version 1.0 - by Thomas Schoch - www.retas.de
# ========================================================

from __future__ import print_function
from pololu_drv8835_rpi import motors, MAX_SPEED
import time
from sys import exit
import wiringpi as wp2
import RPi.GPIO as GPIO

# Signal handler for SIGTERM
import signal
def sigterm_handler(signal, frame):
    motors.setSpeeds(0, 0)
    exit(0) 
signal.signal(signal.SIGTERM, sigterm_handler)

# GPIO pins of sensors
GPIO.setmode(GPIO.BCM)
#select pins to read sensor values from
pin1 = 22
pin2 = 23
pin3 = 0
pin4 = 1
pin5 = 12
pin6 = 13

# Three speed constants for different purposes
v3 = MAX_SPEED # = 480
v2 = 100 #380
v1 = 50 #150

#define gray and black thresholds
#color_thresh = 0.00035
gray_thresh = 0.0003
black_thresh = 0.00045

#Loop period
delay = 0.001 #0.05

# Read sensor input and print some diagnostics
def read_sensor(pin):
    GPIO.setup(pin, GPIO.OUT) #Set your chosen pin to an output
    GPIO.output(pin, GPIO.HIGH) #turn on the power 5v to the sensor
    time.sleep(0.01) #charge the tiny capacitor on the sensor for 0.1sec
    pulse_start = time.time() #start the stopwatch
    pulse_end = pulse_start

    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set pin to pull down$
    while GPIO.input(pin)> 0:
        pass #wait while the capacitor discharges to zero
    if  GPIO.input(pin)==0:
        pulse_end = time.time() #when it hits zero stop the stopwatch
    pulse_duration = pulse_end - pulse_start
    #print("duration:", pulse_duration) #print the time so you can adjust sensi$
    if pulse_duration > black_thresh: #adjust this value to change the sensitiv$
        color = "b" #sees black
    elif pulse_duration > gray_thresh:
	color = "g" #sees gray
    else:
        color= "w" #sees white
    return color
    #print ("%-6s %2d/%d " % 
    #    (moving, ingap, black_cntr))
    #return (L, M, R)

# MAIN
try:
    # Start moving forward
    motors.setSpeeds(v2, v2)
    moving = "S"
    color = [] #initialize color array
    while True: # Main loop

        # Repeat this loop every delay seconds
        time.sleep (delay)

	#read sensor values
        color.append(read_sensor(pin1)) 
        color.append(read_sensor(pin2))
        color.append(read_sensor(pin3))
        color.append(read_sensor(pin4))
        color.append(read_sensor(pin5))
        color.append(read_sensor(pin6))

        if (color[2]== 0) and (color[3] == 0): #middle is white
            # Departure from left curve: narrow radius
            if moving == "L":
                motors.setSpeeds(-v1, v2)
                moving = "L"
            # Departure from right curve: narrow radius
            elif moving == "R":
                motors.setSpeeds(v2, -v1)
                moving = "R"
	    else:
		print("Error! No valid moving value")

        # Swang to the right: turn left
        elif (color[0:3] == [0, 2, 2]) or (color[0:3] == [2, 2, 0]) \
              or (color[0:3] == [0, 2, 0]) or (color[0:3] == [2, 0, 0]) #left side (pins 1-3) sees black
            motors.setSpeeds(v1, v2)
            moving = "L"

        # Swang to the left: turn right
        elif (color[3:6] == [2, 2, 0]) or (color[3:6] == [0, 2, 2]) \
              or (color[3:6] == [0, 2, 0]) or (color[3:6] == [0, 0, 2]): #right side (pins 6-8) sees black
            motors.setSpeeds(v2, v1)
            moving = "R"

        # Else: go forward
        else:
            motors.setSpeeds(v2, v2)
            moving = "S"
	
	color = [] #clear color array

finally:
    # Stop motors in case of <Ctrl-C> or SIGTERM:
    motors.setSpeeds(0, 0)

