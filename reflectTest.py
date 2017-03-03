""" Raspberry Pi Python Code for QTR-1RC IR Sensor
    by tobyonline copyleft 2016 robot-resource.blogspot.com
http://tobyonline.co.uk """

import RPi.GPIO as GPIO
import time
GPIO.setmode(GPIO.BCM)

color_thresh = 0.00035

pin1 = 22 #assumes you've connected the IR Out wire to GPIO19
pin2 = 23 #assumes you've connected the IR Out wire to GPIO20
pin3 = 0 #assumes you've connected the IR Out wire to GPIO21
pin4 = 1
pin5 = 5
pin6 = 6
pin7 = 12
pin8 = 13

def irsensor(pin): #function to get value from IR sensor
    GPIO.setup(pin, GPIO.OUT) #Set your chosen pin to an output
    #GPIO.setup(pin_middle, GPIO.OUT) #Set your chosen pin to an output
    #GPIO.setup(pin_left, GPIO.OUT) #Set your chosen pin to an output
    GPIO.output(pin, GPIO.HIGH) #turn on the power 5v to the sensor
    #GPIO.output(pin_middle, GPIO.HIGH) #turn on the power 5v to the sensor
    #GPIO.output(pin_left, GPIO.HIGH) #turn on the power 5v to the sensor
    time.sleep(0.01) #charge the tiny capacitor on the sensor for 0.1sec
    pulse_start = time.time() #start the stopwatch
    pulse_end = pulse_start

    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set pin to pull down to ground 0v
    #GPIO.setup(pin_middle, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set pin to pull down to ground 0v
    #GPIO.setup(pin_left, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # set pin to pull down to ground 0v
    while GPIO.input(pin)> 0:
        pass #wait while the capacitor discharges to zero
    if  GPIO.input(pin)==0:
        pulse_end = time.time() #when it hits zero stop the stopwatch
    pulse_duration = pulse_end - pulse_start
    print "duration:", pulse_duration #print the time so you can adjust sensitivity
    if pulse_duration > color_thresh: #adjust this value to change the sensitivity
        color = 1
    else:
        color= 0
    return color

color = []
while True:
    color.append(irsensor(pin1)) #call the function and get the output colour_seen
    color.append(irsensor(pin2))
    color.append(irsensor(pin3))
    color.append(irsensor(pin4))
    color.append(irsensor(pin5))
    color.append(irsensor(pin6))
    color.append(irsensor(pin7))
    color.append(irsensor(pin8))

    print color
    time.sleep(1) #pause for 1 second before repeating, use ctrl+z to stop
    color = []

GPIO.cleanup() #always good practice to clean-up the GPIO settings at the end :) tobyonline
