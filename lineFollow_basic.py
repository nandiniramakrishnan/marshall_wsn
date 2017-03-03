#!/usr/bin/python
# ========================================================
# Python script for PiBot-A: line follower
# Version 1.0 - by Thomas Schoch - www.retas.de
# ========================================================

from __future__ import print_function
from pololu_drv8835_rpi import motors, MAX_SPEED
from time import sleep
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
GPIO_right  = 21
GPIO_middle = 20
GPIO_left   = 19
GPIO.setup(GPIO_right, GPIO.IN)
GPIO.setup(GPIO_middle, GPIO.IN)
GPIO.setup(GPIO_left, GPIO.IN)

# Three speed constants for different purposes
v3 = MAX_SPEED # = 480
v2 = 380
v1 = 150

# Loop period
delay = 0.05

# Maximum loop cycles when track is lost
# before emergency stop
max_ingap = 10

# Read sensor input and print some diagnostics
def read_sensors():
    R = GPIO.input(GPIO_right)
    M = GPIO.input(GPIO_middle)
    L = GPIO.input(GPIO_left)
    LC = "#" if L else " "
    MC = "#" if M else " "
    RC = "#" if R else " "
    print ("%-6s %2d/%d   |%c%c%c|" % 
        (moving, ingap, black_cntr, LC, MC, RC))
    return (L, M, R)

# 180 degrees turn on black disc
def turn_180():
    # speed-up and slow-down for smooth movement
    sleep (0.2)
    motors.setSpeeds(-v1, v1)
    sleep (0.1)
    motors.setSpeeds(-v3, v3)
    sleep (0.5)
    motors.setSpeeds(-v1, v1)
    # After ca. 165 degrees: snap the track
    (L, M, R) = read_sensors()
    while M == 0:
        (L, M, R) = read_sensors()
        sleep (delay)

# MAIN
try:
    # Start moving forward
    motors.setSpeeds(v2, v2)

    # Assumption: starting out of track
    moving = "search" # current movement (fwd, left ...)
    ingap = 1         # in gap (else: on track)
    black_cntr = 0    # counter for all sensors black
    in_course = 0     # in course (else: still searching)

    while True: # Main loop

        # Repeat this loop every delay seconds
        sleep (delay)
        (L, M, R) = read_sensors()

        # Found track first time? Then we are in_course
        if M == 1:
            in_course = 1
        elif in_course == 0:
            continue

        # In gap? Increment counter and stop if necessary
        if L == 0 and M == 0 and R == 0:
            if moving == "gap":
                ingap += 1
                if ingap > max_ingap:
                    print ("STOP WHITE")
                    exit (0)
        else: # reset counter
            ingap = 0

        # All sensors black? Increment counter
        # and turn on black disc.
        if L == 1 and M == 1 and R == 1:
            motors.setSpeeds(v2, v2)
            black_cntr += 1
            if black_cntr > 2:
                turn_180()
            continue
        else:
            black_cntr = 0 # reset counter

        if M == 0:
            # Departure from left curve: narrow radius
            if moving[0:4] == "left":
                motors.setSpeeds(-v1, v2)
                moving = "left)"

            # Departure from right curve: narrow radius
            elif moving[0:5] == "right":
                motors.setSpeeds(v2, -v1)
                moving = "right)"

            # Got into gap
            else:
                motors.setSpeeds(v2, v2)
                moving = "gap"

        # Swang to the right: turn left
        elif L == 1:
            motors.setSpeeds(v1, v2)
            moving = "left"

        # Swang to the left: turn right
        elif R == 1:
            motors.setSpeeds(v2, v1)
            moving = "right"

        # Else: go forward
        else:
            motors.setSpeeds(v2, v2)
            moving = "fwd"

finally:
    # Stop motors in case of <Ctrl-C> or SIGTERM:
    motors.setSpeeds(0, 0)

