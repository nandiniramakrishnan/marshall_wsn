#!/usr/bin/python
# ========================================================
# Python script for PiBot-A: maze solver
# Version 1.0 - by Thomas Schoch - www.retas.de
# ========================================================

# ----------------- TERMINOLOGY OF NODES -----------------
#
#   --|--   crossing, +
#
#   --|     T-junction, T
#
#   --.     turn
#     |
#
#   --      dead end
#
#   --O     disk (target)
#
# ----------------- TERMINOLOGY OF MOVES -----------------
#
#   L = left (at + or T or turn)
#   R = right (at + or T or turn)
#   S = straight (at + or T)
#   T = turn (at dead end)
#
# --------------------------------------------------------

from __future__ import print_function
from pololu_drv8835_rpi import motors, MAX_SPEED
from time import sleep
from sys import exit, argv
import RPi.GPIO as GPIO

# Signal handler for SIGTERM
import signal
def sigterm_handler(signal, frame):
    motors.setSpeeds(0, 0)
    exit(0) 
signal.signal(signal.SIGTERM, sigterm_handler)

# --------------------------------------------------------
# Some constants
# --------------------------------------------------------

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
delay = 0.001

# ========================================================
# Functions
# ========================================================

# If an argument is given, print some diagnostic values
# and pause until a key is hit.
def pause(*args):

    if pausing:
        motors.setSpeeds(0, 0)
        print(way, *args)
        raw_input(read_sensors())

# --------------------------------------------------------
# Read sensor input
def read_sensors(*sensor):

    L = GPIO.input(GPIO_left)
    M = GPIO.input(GPIO_middle)
    R = GPIO.input(GPIO_right)

    if len(sensor) == 0: return (L, M, R)

    elif sensor[0] == "left":   return L
    elif sensor[0] == "middle": return M
    elif sensor[0] == "right":  return R

# --------------------------------------------------------
# Drive some distance, time to sleep is calculated from
# given value (val) and result of calibration (cal).
def drive(val):

    sec = val * cal/500
    sleep (sec)

# --------------------------------------------------------
# Calibrate: Drive two 180 degree turns in both directions
# and measure time needed.
def calibrate():

    tl1 = turn("left")
    tl2 = turn("left")
    tr1 = turn("right")
    tr2 = turn("right")
    cal = (tl1 + tl2 + tr1 + tr2) / 4
    print ("CAL:", tl1, tl2, tr1, tr2, "=>", cal)

    return cal

# --------------------------------------------------------
# Turn left or right: at first leave the black line just
# under the sensors (if there is a line), then continue
# turning until the black line is reached again.
def turn(dir):

    if dir == "left":
        motors.setSpeeds(-v3, v3)
    else:
        motors.setSpeeds(v3, -v3)

    # Start with a short turn to ensure that we will
    # leave the line under (or next to) the sensors.
    sleep (100 * delay)

    # Count loops while turning (for calibration)
    turn = 100

    # Turn until line is lost
    while read_sensors("middle") == 1:
        turn += 1
        sleep (delay)

    # Turn until line is reached again
    while read_sensors("middle") == 0:
        turn += 1
        sleep (delay)

    return turn

# --------------------------------------------------------
# Drive some distance until the node is under the axle.
def axle_to_node():

    # Number of loops depend on calibration
    cnt = (cal - 100) / 2

    # Correct drifts to the left or right while driving
    while cnt:
        (L, M, R) = read_sensors()
        if L == 1 and R == 0:
            motors.setSpeeds(v1, v2)
        elif R == 1 and L == 0:
            motors.setSpeeds(v2, v1)
        else:
            motors.setSpeeds(v2, v2)
        sleep (delay)
        cnt -= 1

    motors.setSpeeds(v2, v2)

# --------------------------------------------------------
# Show lists of nodes and moves.
def show_steps(nodes, moves):

    print ("------------------")
    for i in range (0, len(nodes)):
        print ("%2d  %-12s %s" % (i, nodes[i], moves[i]))
    print ("------------------")

# --------------------------------------------------------
# Finish: stop moving.
def finish(*result):

    # Stand still for a moment
    print (*result)
    motors.setSpeeds(0, 0)
    sleep (0.5)

    # Depending on success ("HOORAY!") or failure ...
    f = 1 if result[0] == "HOORAY!" else -1

    # ... nod or shake your head 4 times.
    for x in range (0, 4):
        motors.setSpeeds(f * -v1, -v1)
        drive (0.1)
        motors.setSpeeds(f * v1, v1)
        drive (0.1)
    motors.setSpeeds(0, 0)

    # Loop forever
    while True: sleep (1)

# --------------------------------------------------------
# Determine type of node by comparing sensors at the node
# with sensors behind the node. Example: (0, 1, 1) at node
# and (0, 1, 0) behind node results in: T-junction right.
def type_of_node(sensors):

    # Status at node
    if   sensors == (0, 1, 1): at_node = "line_right"
    elif sensors == (1, 1, 0): at_node = "line_left"
    elif sensors == (1, 1, 1): at_node = "line_xing"
    else:
        finish("UNEXPECTED NODE:", sensors)
    pause("AT_NODE:", at_node)

    # Drive until node is under the axle
    axle_to_node()

    # Read sensors behind the node
    sensors = read_sensors()

    if   sensors == (0, 0, 0): behind_node = "blank"
    elif sensors == (1, 1, 1): behind_node = "black"
    else:                      behind_node = "line"

    # Determine type of node
    n = (at_node, behind_node)
    if behind_node == "black": node = "disk"

    elif n == ("line_right", "blank"): node = "turn_right"
    elif n == ("line_left",  "blank"): node = "turn_left"
    elif n == ("line_xing",  "line"):  node = "crossing"
    elif n == ("line_xing",  "blank"): node = "T_straight"
    elif n == ("line_right", "line"):  node = "T_right"
    elif n == ("line_left",  "line"):  node = "T_left"

    return (node)

# --------------------------------------------------------
# Calculate shortest path: make a copy of lists "nodes"
# and "moves" with values of the shortest path ("nodes_sp"
# and "moves_sp").
def calculate_path():

    global remaining_turns

    # Remove turns, but remember the number of turns
    # before first node is reached (remaining_turns),
    # needed for the second last section of the way back.
    behind_first_node = False
    for i in range (0, len(nodes)):
        if nodes[i] == "turn_left" \
        or nodes[i] == "turn_right":
            if not behind_first_node:
                remaining_turns += 1
        else:
            behind_first_node = True
            moves_sp.append(moves[i])
            nodes_sp.append(nodes[i])
    print ("AFTER REMOVING TURNS:")
    show_steps (nodes_sp, moves_sp)

    # Remove dead ends by substituting each sequence
    # of moves that contains a turn at a dead end (T)
    # by an adequate sequence that does not.
    while "T" in moves_sp:
        i = moves_sp.index("T")
        seq = "".join(moves_sp[i-1:i+2])
        if   seq == "STL": subst = "R"
        elif seq == "STR": subst = "L"
        elif seq == "LTL": subst = "S"
        elif seq == "RTR": subst = "S"
        elif seq == "LTS": subst = "R"
        elif seq == "RTL": subst = "T"
        elif seq == "LTR": subst = "T"
        elif seq == "STS": subst = "T"
        else:
            finish("UNEXPECTED SEQ:", seq)
        print ("SUBST:", i, seq, "=>", subst)
        moves_sp[i-1] = subst
        del moves_sp[i:i+2]
        del nodes_sp[i:i+2]
    print ("SHORTEST PATH:")
    show_steps (nodes_sp, moves_sp)
    print ("REMAINING TURNS:", remaining_turns)
    print ("REMAINING LOOPS:", remaining_loops)

# ========================================================
# MAIN
# ========================================================

# If an argument is given, pause at pause()
pausing = True if len(argv) == 2 else False

nodes = []           # list of nodes on way to disk
moves = []           # list of moves on way to disk
nodes_sp = []        # list of nodes in shortest path
moves_sp = []        # list of moves in shortest path
remaining_turns = 0  # turns after last + or T node
remaining_loops = 0  # loops (main loop) after last turn

way = "to_first_node"  # current way
moving = "straight"    # current moving

try:
    # After calibration start driving straight ahead
    cal = calibrate()
    motors.setSpeeds(v3, v3)

    while True: # Main loop

        # Repeat this loop every delay seconds
        sleep (delay)

        # Read sensors at current position
        (L, M, R) = read_sensors()

        # ------------------------------------------------
        # Simply drive
        # ------------------------------------------------

        # Count loops until the first node is reached
        # (needed for the very last section of the way
        # back).
        if way == "to_first_node":
            remaining_loops += 1

        # Decrement remaining loops (see above) on the
        # last sestion of way back (behind the last node).
        elif way == "remaining_loops":
            remaining_loops -= 1
            if remaining_loops == 0:
                drive(0.15) # lenght of robot
                finish("HOORAY!")

        # Drive and correct drifts to the left or right

        if (L, M, R) == (0, 1, 0):
            # We are on the line: go straight ahead
            motors.setSpeeds(v3, v3)
            moving = "straight"
            continue

        elif L == 1 and R == 0:
            # Deviation to the right: correct to the left
            motors.setSpeeds(v1, v3)
            moving = "left"
            continue

        elif R == 1 and L == 0:
            # Deviation to the left: correct to the right
            motors.setSpeeds(v3, v1)
            moving = "right"
            continue

        # ------------------------------------------------
        # At some node
        # ------------------------------------------------

        # If we are in the very last section of way back:
        # ignore the node and just pass or cross it
        # (should be an exceptional case).
        if way == "remaining_loops":
            continue

        # If we were on the way to the first node: we are
        # now on the way to the disk.
        elif way == "to_first_node":
            way = "to_disk"

        # ------------------------------------------------
        # Dead end: drive axle over the node and turn
        # ------------------------------------------------

        if (L, M, R) == (0, 0, 0):
            axle_to_node()
            turn("left")
            nodes.append("dead_end")
            moves.append("T")
            motors.setSpeeds(v3, v3)
            moving = "straight"
            continue

        # ------------------------------------------------
        # Other type of node
        # ------------------------------------------------

        # All sensors are black. This can be a crossing
        # line (+ or T), or it is because lastly we made 
        # a correction after a deviation to left or right.
        # Then we have to sway to the opposite side and
        # read the outer sensor there. After that we have
        # to compensate these movements to adjust our
        # orientation to straight ahead again.
        (L1, M1, R1) = (L, M, R)
        if moving == "left":
            drive(0.04)
            motors.setSpeeds(v2, -v2)
            drive(0.1)
            R1 = read_sensors("right")
            motors.setSpeeds(-v2, v2)
            drive(0.07)

        elif moving == "right":
            drive(0.04)
            motors.setSpeeds(-v2, v2)
            drive(0.1)
            L1 = read_sensors("left")
            motors.setSpeeds(v2, -v2)
            drive(0.07)
        sensors = (L1, M1, R1)

        # Determine type of node
        node = type_of_node(sensors)

        # ------------------------------------------------
        # At disk: turn and calculate shortest path
        # ------------------------------------------------

        if node == "disk":
            drive(0.15)
            motors.setSpeeds(0, 0)
            sleep (1.0)
            turn("left")
            way = "back"
            print ("WAY TO DISK:")
            show_steps (nodes, moves)
            calculate_path()
            continue

        # ------------------------------------------------
        # Other node: decide on movement depending on way
        # ------------------------------------------------

        motors.setSpeeds(v3, v3)

        # ------------------------------------------------
        # On the way to the disk: search for the disk
        # following the left-hand rule and fill lists
        # "nodes" and "moves".
        if way == "to_disk":
            nodes.append(node)
            pause ("NODE:", node)
            if node == "turn_right":
                turn("right")
                moves.append("R")
            elif node != "T_right":
                turn("left")
                moves.append("L")
            else:
                moves.append("S")

        # ------------------------------------------------
        # On the way back to the start: drive along the
        # shortest path until the list "moves_sp" is
        # empty. (After that there may be remaining turns
        # and remaining loops.)
        elif way == "back":
            if   node == "turn_right": turn("right")
            elif node == "turn_left":  turn("left")
            else:
                dir = moves_sp.pop()
                if   dir == "L": turn("right")
                elif dir == "R": turn("left")
                elif dir == "S":
                    motors.setSpeeds(v3, v3)
                    drive (0.2)
                else:
                    finish("UNEXPECTED DIR:", dir)

                # List "moves_sp" is empty?
                if moves_sp == []:
                    # Are there still remaining turns?
                    if remaining_turns > 0:
                        # Drive the remaining turns
                        way = "remaining_turns"
                    else:
                        # Drive the remaining loops
                        way = "remaining_loops"

        # ------------------------------------------------
        # Driving the remaining turns at the second last
        # section of the way back
        elif way == "remaining_turns":
            if   node == "turn_right": turn("right")
            elif node == "turn_left":  turn("left")
            remaining_turns -= 1

            # No more remaining turns?
            if remaining_turns == 0:
                # Drive the remaining loops
                way = "remaining_loops"

        motors.setSpeeds(v3, v3)
        moving = "straight"

finally:
    # Stop motors in case of <Ctrl-C> or SIGTERM:
    motors.setSpeeds(0, 0)

