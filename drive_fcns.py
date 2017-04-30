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
import copy
import operator


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


def update_row(curr_row, direction):
	if direction == "N":
		curr_row = curr_row - 1
	elif direction == "S":
		curr_row = curr_row + 1
	return curr_row

def update_col(curr_col, direction):
	if direction == "W":
		curr_col = curr_col - 1
	elif direction == "E":
		curr_col = curr_col + 1
	return curr_col
# Line following code goes here!
# This function follows a line straight until an intersection is reached
def line_follow(curr_orient, direction):
    # Start moving forward
    #motors.setSpeeds(v2, v2)
    #cal = calibrate()
    saw_white = 0
    moving = "S"
    #dir = "right"
    desired_orient = direction
    color = []

    motors.setSpeeds(v2, v2)
    time.sleep(0.4)

#    print("in line follow")

    while color != [2,2,2,2,2,2]: # Main loop
        # Repeat this loop every delay seconds
        #print("in line f while")
        time.sleep (delay)
        color = get_color()
	if color == [2,2,2,2,2,2]:
	    break
        #print(color)

	#roll up past intersection


        if (curr_orient != desired_orient):
	    if curr_orient == "N":
		src = 1
	    elif curr_orient == "E":
		src = 2
	    elif curr_orient == "S":
		src = 3
	    else:
		src = 4
	    if desired_orient == "N":
		dst = 1
	    elif desired_orient == "E":
		dst = 2
	    elif desired_orient == "S":
		dst = 3
	    else:
		dst = 4

	    while (dst - src) != 0:
	        if (abs(dst-src) < 3):
		    if (dst-src) < 0:
		    	#rotate left
		    	turn("left")
		   	src -= 1
	            elif (dst-src) > 0:
		    	#rotate right
		    	turn("right")
		    	src += 1
		else:
		    if ((dst-src) < 0):
			turn("right")
			src -= 3
		    else:
			turn("left")
			src += 3

            curr_orient = desired_orient

        if (color == [0,0,0,0,0,0]):
            if (saw_white == 0):
                print("off grid. not stopping")
                saw_white = 1
            else:
                motors.setSpeeds(0,0)
                print("stop! off grid")
                return 1
        else:
            saw_white = 0

        if (moving != "S") and (color[3]== 0) and (color[4] == 0): #middle is white
            # Departure from left curve: narrow radius
            if moving == "L":
                motors.setSpeeds(-v1, v2)
                moving = "L"
#                print("off grid, go left!")
            # Departure from right curve: narrow radius
            elif moving == "R":
                motors.setSpeeds(v2, -v1)
                moving = "R"
#                print("off grid, go right!")

        # Swang to the right: turn left
        elif (color[0:3] == [0, 2, 2]) or (color[0:3] == [2, 2, 0]) \
              or (color[0:3] == [0, 2, 0]) or (color[0:3] == [2, 0, 0]): #left side (pins 1-3) sees $
            #print("turn left")
            motors.setSpeeds(v1, v2)
            moving = "L"

        # Swang to the left: turn right
        elif (color[3:6] == [2, 2, 0]) or (color[3:6] == [0, 2, 2]) \
              or (color[3:6] == [0, 2, 0]) or (color[3:6] == [0, 0, 2]): #right side (pins 6-8) sees$
            #print("turn right")
            motors.setSpeeds(v2, v1)
            moving = "R"

        # Else: go forward
        else:
            #print("go straight")
            motors.setSpeeds(v2, v2)
            moving = "S"

        color = [] #clear color array

    #print("intersection reached")
    motors.setSpeeds(0,0)
    return 0

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
def get_color():
    color = []
    #read sensor values
    color.append(read_sensor(pin1))
    color.append(read_sensor(pin2))
    color.append(read_sensor(pin3))
    color.append(read_sensor(pin4))
    color.append(read_sensor(pin5))
    color.append(read_sensor(pin6))
    return color

def rotate(curr_orient, desired_orient):
    #robot must be directly on intersection
    while (curr_orient != desired_orient):
	motors.setSpeeds(speed, -speed)
	time.sleep(0.5)
	color = get_color()
	while (color[2:4] != [2, 2]) and (color[2:4] != [0, 2]) and (color[2:4] != [2, 0]):
            motors.setSpeeds(speed, -speed)
            time.sleep(0.1)
            color = get_color()
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
   #for use while driving
    color = get_color()    
    if direction == "left":
        motors.setSpeeds(-speed, speed)
    elif direction == "right":
        motors.setSpeeds(speed, -speed)
    else:
        return
    time.sleep(0.7)
    color = get_color()
    #print(color)
    #print("off first line")
    while (color[2:4] != [2, 2]) and (color[2:4] != [0, 2]) and (color[2:4] != [2, 0]):
        
	if direction == "right":
	    motors.setSpeeds(speed, -speed)
	elif direction == "left":
	    motors.setSpeeds(-speed, speed)
        time.sleep(0.1)
        color = get_color()
        #print(color)

    motors.setSpeeds(0,0)
    return

#old path_plan
def path_plan(curr_row, curr_col, new_row, new_col):
    path = {'N':0,'E':0,'W':0,'S':0}
    diff_row = new_row - curr_row
    diff_col = new_col - curr_col
    if (diff_row > 0):
	#drive South
	path['S'] = abs(diff_row)
    elif (diff_row < 0):
	#drive north
	path['N'] = abs(diff_row)
    if (diff_col > 0):
	#drive east
	path['E'] = abs(diff_col)
    elif (diff_col < 0):
	#drive west
	path['W'] = abs(diff_col)
    return path

'''
#new plan_path code
def plan_path(curr_row, curr_col, new_row, new_col):
    path = []
    diff_row = new_row - curr_row
    diff_col = new_col - curr_col
    if (diff_col > 0): #drive east
	    path.append(('E', abs(diff_col)))
    elif (diff_col < 0): #drive west
	    path.append(('W', abs(diff_col)))
    if (diff_row > 0): #drive South
	    path.append(('S', abs(diff_row)))
    elif (diff_row < 0): #drive north
	    path.append(('N', abs(diff_row)))
    return path
'''


gridSize = [4,6]

#avoidList = [(1,1), (2,3), (3,3)]

def findCoords(curr_row, curr_col, dest_row, dest_col, avoidList):
    path_found = 0
    paths = [[(curr_row, curr_col)]]
    paths_to_remove = []
    
    while path_found == 0:
        paths_queue = copy.deepcopy(paths)
        for path in paths_queue:
            if (dest_row, dest_col) in path:
                path_found = 1
                return path
            
            elif (dest_row, dest_col) not in path:
                tmp_path = path

                row = tmp_path[len(tmp_path)-1][0]
                col = tmp_path[len(tmp_path)-1][1]

                adjacents = []
                if col < (gridSize[1]-1): #east
                    adjacents.append((row, col+1))
                if col >= 1: #west
                    adjacents.append((row, col-1))
                if row >= 1: #north
                    adjacents.append((row-1, col))
                if row < (gridSize[0]-1): #south
                    adjacents.append((row+1, col))

                for i in range(len(adjacents)):
                    if (adjacents[i] not in avoidList) and (adjacents[i] not in tmp_path):
                        tmp_path.append(adjacents[i])
                        tmp_copy = copy.deepcopy(tmp_path)
                        paths.append(tmp_copy)
                        tmp_path.remove(adjacents[i])

def coordsToPath(coords):
    path = []
    for i in range(1, len(coords)):
        dir = getDir(coords[i-1], coords[i])
        path.append(dir)
    return path

def getDir(curLoc, nextLoc):
    move = tuple(map(operator.sub, nextLoc, curLoc))
    if move[0] == 1:
        dir = "S"
    elif move[0] == -1:
        dir = "N"
    elif move[1] == 1:
        dir = "E"
    elif move[1] == -1:
        dir = "W"
    else:
        dir = "Null"
    return dir

def plan_path(curr_row, curr_col, dest_row, dest_col, avoidList):
    path_coords = findCoords(curr_row, curr_col, dest_row, dest_col, avoidList)
    path_dirs = coordsToPath(path_coords)
    return (path_coords, path_dirs)
