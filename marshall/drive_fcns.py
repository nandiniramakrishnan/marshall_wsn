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
import signal
import atexit


# GPIO pins of sensors
GPIO.setmode(GPIO.BCM)
#select pins to read sensor values from
pin1 = 17
pin2 = 27
pin3 = 22 #0
pin4 = 23 #1
pin5 = 16 #12
pin6 = 26 #13

# Three speed constants for different purposes
v3 = MAX_SPEED # = 480
v2 = 50 #380
v1 = 25 #150
speed = 50

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
        color = 2 #sees black
#    elif pulse_duration > gray_thresh:
#	color = "1" #sees gray
    else:
        color= 0 #sees white
    return color
    #print ("%-6s %2d/%d " % 
    #    (moving, ingap, black_cntr))
    #return (L, M, R)

"""# --------------------------------------------------------
# Drive some distance, time to sleep is calculated from
# given value (val) and result of calibration (cal).
def drive(val):

    sec = val * cal/500
    sleep (sec)

# --------------------------------------------------------
# Calibrate: Drive two 180 degree turns in both directions
# and measure time needed.
def calibrate():

    tl1 = turnCalib("left")
    tl2 = turnCalib("left")
    tr1 = turnCalib("right")
    tr2 = turnCalib("right")
    cal = (tl1 + tl2 + tr1 + tr2) / 4
    print ("CAL:", tl1, tl2, tr1, tr2, "=>", cal)

    return cal

# --------------------------------------------------------
# Turn left or right: at first leave the black line just
# under the sensors (if there is a line), then continue
# turning until the black line is reached again.
def turnCalib(dir):

    if dir == "left":
        motors.setSpeeds(-v3, v3)
    else:
        motors.setSpeeds(v3, -v3)

    # Start with a short turn to ensure that we will
    # leave the line under (or next to) the sensors.
    time.sleep (100 * delay)

    # Count loops while turning (for calibration)
    turn = 100

    # Turn until line is lost
    while read_sensors("middle") == 1:
        turn += 1
        time.sleep(delay)

    # Turn until line is reached again
    while read_sensors("middle") == 0:
        turn += 1
        time.sleep(delay)

    return turn
"""
def rotate(curr_orient, desired_orient):
    while (curr_orient != desired_orient):
	motors.setSpeeds(speed, -speed)
	time.sleep(0.5)
	color = []
    	#read sensor values
    	color.append(read_sensor(pin1))
    	color.append(read_sensor(pin2))
    	color.append(read_sensor(pin3))
    	color.append(read_sensor(pin4))
    	color.append(read_sensor(pin5))
    	color.append(read_sensor(pin6))
	while (color[2:4] != [2, 2]) and (color[2:4] != [0, 2]) and (color[2:4] != [2, 0]):
            motors.setSpeeds(speed, -speed)
            time.sleep(0.1)
            color = []
            #read sensor values
            color.append(read_sensor(pin1))
            color.append(read_sensor(pin2))
            color.append(read_sensor(pin3))
            color.append(read_sensor(pin4))
            color.append(read_sensor(pin5))
            color.append(read_sensor(pin6))
            print(color)
	motors.setSpeeds(0,0)
	if curr_orient == "N":
	    curr_orient = "E"
	elif curr_orient == "E":
	    curr_orient = "S"
	elif curr_orient == "S":
	    curr_orient = "W"
	elif curr_orient == "W":
	    curr_orient = "N"
	print(curr_orient)
    return


def turn(direction):
    motors.setSpeeds(v2, v2)
    time.sleep(0.5)
    color = []
    #read sensor values
    color.append(read_sensor(pin1))
    color.append(read_sensor(pin2))
    color.append(read_sensor(pin3))
    color.append(read_sensor(pin4))
    color.append(read_sensor(pin5))
    color.append(read_sensor(pin6))
    #while (color != [0,0,0,0,0,0]):
   # while (color[4:6] != [2, 2]) and (color[4:6] != [0, 2]) and (color[4:6] != [2, 0]) :    
    if direction == "left":
        motors.setSpeeds(-speed, speed)
    elif direction == "right":
        motors.setSpeeds(speed, -speed)
    else:
        return
    time.sleep(0.9)
    color = []
    #read sensor values
    color.append(read_sensor(pin1))
    color.append(read_sensor(pin2))
    color.append(read_sensor(pin3))
    color.append(read_sensor(pin4))
    color.append(read_sensor(pin5))
    color.append(read_sensor(pin6))
    #print(color)
    #print("off first line")
    while (color[2:4] != [2, 2]) and (color[2:4] != [0, 2]) and (color[2:4] != [2, 0]):
        
	if direction == "right":
	    motors.setSpeeds(speed, -speed)
	elif direction == "left":
	    motors.setSpeeds(-speed, speed)
        time.sleep(0.1)
        color = []
        #read sensor values
        color.append(read_sensor(pin1))
        color.append(read_sensor(pin2))
        color.append(read_sensor(pin3))
        color.append(read_sensor(pin4))
        color.append(read_sensor(pin5))
        color.append(read_sensor(pin6))
        print(color)

    motors.setSpeeds(0,0)
    return
