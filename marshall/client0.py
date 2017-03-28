import time 
import socket
from threading import Thread
import Queue

#initialize client0 at location (0,0) facing East
curr_row = 0
curr_col = 0
curr_orient = "E" 

# Line following code goes here!
# This function follows a line straight until an intersection is reached
def line_follow(direction):
    # Start moving forward
    #motors.setSpeeds(v2, v2)
    #cal = calibrate()
    saw_white = 0
    moving = "S"
    #dir = "right"
    desired_orient = direction
    color = []
    while color != [2,2,2,2,2,2]: # Main loop
        # Repeat this loop every delay seconds
        time.sleep (delay)
        color = get_color()
        print(color)

        if (curr_orient != desired_orient):
            rotate(curr_orient, desired_orient)
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

            #if (color == [2,2,2,2,2,2]):
            #   print("reached intersection")
            #   if dir == "left":
            #       turn("left")
            #   elif dir == "right":
            #       turn("right")
            #   else:
            #       print("passing intersection")

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
              or (color[0:3] == [0, 2, 0]) or (color[0:3] == [2, 0, 0]): #left side (pins 1-3) sees $
            print("turn left")
            motors.setSpeeds(v1, v2)
            moving = "L"

        # Swang to the left: turn right
        elif (color[3:6] == [2, 2, 0]) or (color[3:6] == [0, 2, 2]) \
              or (color[3:6] == [0, 2, 0]) or (color[3:6] == [0, 0, 2]): #right side (pins 6-8) sees$
            print("turn right")
            motors.setSpeeds(v2, v1)
            moving = "R"

        # Else: go forward
        else:
            print("go straight")
            motors.setSpeeds(v2, v2)
            moving = "S"

        color = [] #clear color array

    print("intersection reached")
    return 0

# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
def drive(row, col, queue):
    path = path_plan(curr_row, curr_col, row, col)
    
    #follow path to destination
    #follows E/W and then N/S
    while (curr_row != row) and (curr_col != col):   

        if (path['E'] > 0):
	    if (line_follow("E") == 0):
	        path['E'] = path['E']-1	
   	        cur_col = col_col + 1
	    else:
		print("went off grid, mission failed")
		return

        elif (path['W'] > 0):
	    if (line_follow("W") == 0):
	        path['W'] = path['W']-1
	        cur_col = cur_col-1
	    else:
		print("went off grid, mission failed")
		return    

        elif (path['N'] > 0):
	    if (line_follow("N") == 0):
	    	path['N'] = path['N']-1
	        cur_row = cur_row-1
	    else:
		print("went off grid, mission failed")
		return
    
        elif (path['S'] > 0):
	    if (line_follow("S") == 0):
	        path['S'] = path['S']-1
	        cur_row = cur_row+1
	    else:
		print("went off grid, mission failed")
		return
    
    #num_intersections_hor = abs(row - curr_row)
    #num_intersections_ver = abs(col - curr_col)
       
         print "Row = %c and col = %c" % (row, col)
    

    # Send update to main thread for transmitting to Marshall
    queue.put((row, col))
    return


# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('128.237.191.52', 10000)
print 'Connecting to %s port %s' % server_address
sock.connect(server_address)

driving = False
node_id = 'CHK000'
received_ack = False
drive_comms_queue = Queue.Queue()
command_queue = Queue.Queue()
try:
    # Send data
    print 'Sending "%s"' % node_id
    sock.sendall(node_id)
    print "Waiting for ACK..."

    # Look for the response
    while not received_ack:
        data = sock.recv(16)
        if data:
            received_ack = True
            print 'Received "%s"' % data
    while True:
        data = sock.recv(16)
        if data:
            print 'Received "%s"' % data
            
            if len(data) == 3:
                row = data[1]
                col = data[2]
                command_queue.put((row, col))



                if driving == False:
                    (drive_row, drive_col) = command_queue.get()
                    # Send "ready for path" message to Marshall
                    # Receive directions and keep pushing into drive_comms_queue
                    
                    thread = Thread(target = drive, args = (drive_row, drive_col, drive_comms_queue))
                    driving = True
                    thread.start()
                    thread.join()
                    driving = False
                    new_pos = drive_comms_queue.get()
		    new_buf = [ 'P', str(new_pos[0]), str(new_pos[1]) ]
		    new_msg = ''.join(new_buf)
		    sock.sendall(new_msg)
finally:
    print 'Closing socket'
    sock.close()
    motors.setSpeeds(0, 0)
    GPIO.cleanup()

