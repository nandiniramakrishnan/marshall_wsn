from __future__ import print_function
from pololu_drv8835_rpi import motors, MAX_SPEED
from sys import exit, argv
import RPi.GPIO as GPIO
import time
import signal
import atexit
GPIO.setmode(GPIO.BCM)

color_thresh = 0.00045
speed = 50

#set pins for reflectance sensor
pin1 = 22 #
pin2 = 23 #
pin3 = 0 #
pin4 = 1
pin5 = 12
pin6 = 13
#pin7 = 5
#pin8 = 6

def turnoff_motor():
    motors.setSpeeds(0,0)
atexit.register(turnoff_motor)

def sigterm_handler(signal, frame):
    motors.setSpeeds(0,0)
    exit(0)
signal.signal(signal.SIGTERM, sigterm_handler)

def irsensor(pin): #function to get value from IR sensor
    GPIO.setup(pin, GPIO.OUT) #Set your chosen pin to an output
    GPIO.output(pin, GPIO.HIGH) #turn on the power 5v to the sensor
    time.sleep(0.01) #charge the tiny capacitor on the sensor for 0.1sec
    pulse_start = time.time() #start the stopwatch
    pulse_end = pulse_start

    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set pin to pull down to ground 0v
    while GPIO.input(pin)> 0:
        pass #wait while the capacitor discharges to zero
    if  GPIO.input(pin)==0:
        pulse_end = time.time() #when it hits zero stop the stopwatch
    pulse_duration = pulse_end - pulse_start
    print("duration:", pulse_duration) #print the time so you can adjust sensitivity
    if pulse_duration > color_thresh: #adjust this value to change the sensitivity
        color = 1
    else:
        color= 0
    return color

try:
    color = []
    motors.setSpeeds(speed, speed)
    while True:
	color.append(irsensor(pin1)) #call the function and get the output colour_seen
    	color.append(irsensor(pin2))
    	color.append(irsensor(pin3))
	color.append(irsensor(pin4))
    	color.append(irsensor(pin5))
    	color.append(irsensor(pin6)) #don't use pin
   

    	time.sleep(0.005) #pause for 1 second before repeating, use ctrl+z to stop  
	motors.setSpeeds(speed, speed)	
	print("\t\t"),
	print(color)
	#motors.setSpeeds(speed, speed)
        if (color == [1, 1, 1, 1, 1, 1]): #all black, need to turn 90 degrees
            print("\t\tgo straight, both sides")
            motors.setSpeeds(speed, speed)
        elif (color == [0, 0, 1, 1, 0, 0]) or (color == [0, 0, 1, 0, 0, 0]) \
	      or (color == [0, 0, 0, 1, 0, 0]): #center pins
            print("\t\tgo straight")
            motors.setSpeeds(speed, speed)
        elif (color == [0, 0, 0, 1, 1, 0]) or (color == [0, 0, 0, 0, 1, 1]) \
	      or (color == [0, 0, 0, 0, 1, 0]) or (color == [0, 0, 0, 0, 0, 1]): #right side (pins 4-6)
            print("\t\tturn right")
            motors.setSpeeds(50, 100)
        elif (color == [0, 1, 1, 0, 0, 0]) or (color == [1, 1, 0, 0, 0, 0]):# \
	 #     or (color == [0, 1, 0, 0, 0, 0]) or (color == [1, 0, 0, 0, 0, 0]): #left side (pins 1-3)
            print("\t\tturn left")
            motors.setSpeeds(100, 50) #right, left motors 
        else: #all 0s or invalid values
	    print("\t\tOff the grid!")
            motors.setSpeeds(0,0)
        color = []    
finally:
    motors.setSpeeds(0,0)




