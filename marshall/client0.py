import time 
import socket
from threading import Thread
import Queue


# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
def drive(row, col, queue):

    # DRIVING CODE GOES HERE
    print "Row = %c and col = %c" % (row, col)
    
    # Intersection pass. Update row and col
    # Example
    row = ord(row) - ord('0') + 1  
    col = ord(col) - ord('0') + 1

    # Send update to main thread for transmitting to Marshall
    queue.put((row, col))

# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('localhost', 10000)
print 'Connecting to %s port %s' % server_address
sock.connect(server_address)

try:
    driving = False
    # Send data
    message = 'CHK0'
    print 'Sending "%s"' % message
    sock.sendall(message)
    print "Waiting for ACK..."

    # Look for the response
    received_ack = False
    ack_iter_count = 0
    while not received_ack:
        data = sock.recv(16)
        if data:
            received_ack = True
            print 'Received "%s"' % data
    drive_comms_queue = Queue.Queue()
    command_queue = Queue.Queue()
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

