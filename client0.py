import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
#initialize client0 at location (0,0) facing East
curr_row = 0
curr_col = 0
curr_orient = "E" 


# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
def drive(row, col, queue, curr_row, curr_col, curr_orient):
    path = DF.path_plan(curr_row, curr_col, row, col)
    
    #follow path to destination
    #follows E/W and then N/S
    while (curr_row != row) and (curr_col != col):   

        if (path['E'] > 0):
	        if (DF.line_follow(curr_orient, "E") == 0):
	            path['E'] = path['E']-1	
   	            curr_col = curr_col + 1
		    queue.put((curr_row, curr_col, curr_orient))
    	        
		else:
		        print("went off grid, mission failed")
		        return

        elif (path['W'] > 0):
	        if (DF.line_follow(curr_orient, "W") == 0):
	            path['W'] = path['W']-1
	            curr_col = curr_col-1
		    queue.put((curr_row, curr_col, curr_orient))
    
	        else:
		        print("went off grid, mission failed")
		        return    

        elif (path['N'] > 0):
	        if (DF.line_follow(curr_orient, "N") == 0):
	    	    path['N'] = path['N']-1
	            curr_row = curr_row-1
		queue.put((curr_row, curr_col, curr_orient))
    
	        else:
		        print("went off grid, mission failed")
		        return
    
        elif (path['S'] > 0):
	        if (DF.line_follow(curr_orient, "S") == 0):
	            path['S'] = path['S']-1
	            curr_row = curr_row+1
		queue.put((curr_row, curr_col, curr_orient))
  
	        else:
		        print("went off grid, mission failed")
		        return

    # Send update to main thread for transmitting to Marshall
    return


# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('128.237.197.18', 10000)
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
                    
                    thread = Thread(target = drive, args = (drive_row, drive_col, drive_comms_queue, curr_row, curr_col, curr_orient))
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

