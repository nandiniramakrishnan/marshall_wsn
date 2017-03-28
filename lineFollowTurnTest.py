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

def turnoff_motor():
    motors.setSpeeds(0,0)
atexit.register(turnoff_motor)

# Signal handler for SIGTERM
import signal
def sigterm_handler(signal, frame):
    motors.setSpeeds(0, 0)
    exit(0) 
signal.signal(signal.SIGTERM, sigterm_handler)

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

def turn(direction):
    motors.setSpeeds(v2, v2)
    time.sleep(0.5)
    passed_init_line = 0
    reacheed_final_line = 0
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

# MAIN
try:
    # Start moving forward
    #motors.setSpeeds(v2, v2)
    #cal = calibrate()
    saw_white = 0
    moving = "S"
    dir = "right"
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
	print(color)
        
	if (color == [0,0,0,0,0,0]):
            if (saw_white == 0):
		print("off grid. not stopping")
	        saw_white = 1
   	    else:
		motors.setSpeeds(0,0)
		print("stop! off grid")
	   	break
	else:
	    saw_white = 0
	
	if (color == [2,2,2,2,2,2]):
	   print("reached intersection")
	   if dir == "left":
               turn("left")
           elif dir == "right":
               turn("right")
           else:
               print("passing intersection")

	if (moving != "S") and (color[3]== 0) and (color[4] == 0): #middle is white
            # Departure from left curve: narrow radius
            if moving == "L":
                motors.setSpeeds(-v1, v2)
                moving = "L"
		print("off grid, go left!")
            # Departure from right curve: narrow radius
            elif moving == "R":
                motors.setSpeeds(v2, -v1)
                moving = "R"
		print("off grid, go right!")
		
        # Swang to the right: turn left
        elif (color[0:3] == [0, 2, 2]) or (color[0:3] == [2, 2, 0]) \
              or (color[0:3] == [0, 2, 0]) or (color[0:3] == [2, 0, 0]): #left side (pins 1-3) sees black
	    print("turn left")
            motors.setSpeeds(v1, v2)
            moving = "L"

        # Swang to the left: turn right
        elif (color[3:6] == [2, 2, 0]) or (color[3:6] == [0, 2, 2]) \
              or (color[3:6] == [0, 2, 0]) or (color[3:6] == [0, 0, 2]): #right side (pins 6-8) sees black
            print("turn right")
	    motors.setSpeeds(v2, v1)
            moving = "R"
         
        # Else: go forward
        else:
	    print("go straight")
            motors.setSpeeds(v2, v2)
            moving = "S"
	
	color = [] #clear color array

#except KeyboardInterrupt:
#    motors.setSpeeds(0,0)
#    GPIO.cleanup()
	
finally:
    # Stop motors in case of <Ctrl-C> or SIGTERM:
    motors.setSpeeds(0, 0)
    GPIO.cleanup()

