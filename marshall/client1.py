import socket
import sys

# Create a TCP/IP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server
server_address = ('localhost', 10000)
print >>sys.stderr, 'Connecting to %s port %s' % server_address
sock.connect(server_address)

try:
    # Send data
    message = 'CHK'
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

finally:
    print >>sys.stderr, 'Closing socket'
    sock.close()

# NEW CODE AFTER THIS POINT
'''
class LineFollower(Thread):
    itg

class Node:
    def __init__(self):

    def run():


if "__main__" == __name__:
    node = Node()
    node.run()
    print "Terminated"
'''
