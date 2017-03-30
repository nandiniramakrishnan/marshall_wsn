import socket
from threading import Thread
import sys

def drive(row, col):
    print "Row = %c and col = %c" % (row, col)
    # DRIVING CODE GOES HERE



# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('localhost', 10000)
print >>sys.stderr, 'Connecting to %s port %s' % server_address
sock.connect(server_address)

try:
    # Send data
    message = 'CHK2'
    print >>sys.stderr, 'Sending "%s"' % message
    sock.sendall(message)
    print "Waiting for ACK..."

    # Look for the response
    received = False
    while not received:
        data = sock.recv(16)
        if data:
            received = True
            print >>sys.stderr, 'Received "%s"' % data

    while True:
        data = sock.recv(16)
        if data:
            print >>sys.stderr, 'Received "%s"' % data
            if len(data) == 3:
                row = data[1]
                col = data[2]
                thread = Thread(target = drive, args = (row, col))
                thread.start()
                thread.join()

finally:
    print >>sys.stderr, 'Closing socket'
    sock.close()

