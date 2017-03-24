import time 
import socket
from threading import Thread
import Queue
from enum import Enum

class Orientation(Enum):
    NORTH = 1
    SOUTH = 2
    EAST = 3
    WEST = 4

curr_row = 0
curr_col = 0
curr_orientation = Orientation.NORTH

# Line following code goes here!
def line_following(direction):
    return

# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
def drive(row, col, queue):

    #num_intersections_hor = abs(row - curr_row)
    #num_intersections_ver = abs(col - curr_col)

    #while curr_row != row and curr_col != col:
    print "Row = %c and col = %c" % (row, col)
    
    # Intersection pass. Update row and col
    # Example
    row = ord(row) - ord('0') + 1  
    col = ord(col) - ord('0') + 1

    # DRIVE ACROSS ROWS

    # DRIVE ACROSS COLS

    # Send update to main thread for transmitting to Marshall
    queue.put((row, col))

# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('localhost', 10000)
print 'Connecting to %s port %s' % server_address
sock.connect(server_address)

driving = False
node_id = 'CHK0'
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
                    thread = Thread(target = drive, args = (drive_row, drive_col, drive_comms_queue))
                    driving = True
                    thread.start()
                    thread.join()
                    driving = False
                    print drive_comms_queue.get()
finally:
    print 'Closing socket'
    sock.close()

