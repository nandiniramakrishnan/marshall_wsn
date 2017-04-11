from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO
import os

# Server address
server_address = ('128.237.138.97', 10000)

class MarshallCommsThread(Thread):
    def __init__(self, sock, queue):
        Thread.__init__(self)
        self.queue = queue
        self.sock = sock

    def run(self):
        while True:
            if not self.queue.empty():
                print "drive queue is not empty!"
                new_pos = self.queue.get()
                curr_row = new_pos[0]
                curr_col = new_pos[1]
                self.curr_orient = new_pos[2]
                new_buf = [ str(self.node_id), str(self.curr_row), str(self.curr_col) ]
                new_msg = ''.join(new_buf)
                print new_msg
                self.sock.sendall(new_msg)
            
        return


# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
class DriverThread(Thread):
    def __init__(self, curr_row, curr_col, curr_orient, dest_row, dest_col, queue):
        Thread.__init__(self)
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.dest_row = int(dest_row)
        self.dest_col = int(dest_col)
        self.queue = queue

    def run(self):
        # Obtain directions to the destination and store in path
        path = DF.path_plan(self.curr_row, self.curr_col, self.dest_row, self.dest_col)

        #follow path to destination
        #follows E/W and then N/S
        while (self.curr_col != self.dest_col):
            if (path['E'] > 0):
                if (DF.line_follow(self.curr_orient, "E") == 0):
                    path['E'] = path['E']-1	
                    self.curr_col = self.curr_col + 1
                    self.queue.put((self.curr_row, self.curr_col, self.curr_orient))
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "E"
            elif (path['W'] > 0):
                if (DF.line_follow(self.curr_orient, "W") == 0):
                    path['W'] = path['W'] - 1
                    self.curr_col = self.curr_col - 1
                    self.queue.put((self.curr_row, self.curr_col, self.curr_orient))
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "W"

        while (self.curr_row != self.dest_row):
            if (path['N'] > 0):
                if (DF.line_follow(self.curr_orient, "N") == 0):
                    path['N'] = path['N']-1
                    self.curr_row = self.curr_row - 1
                    self.queue.put((self.curr_row, self.curr_col, self.curr_orient))
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "N"

            elif (path['S'] > 0):
                if (DF.line_follow(self.curr_orient, "S") == 0):
                    path['S'] = path['S']-1
                    self.curr_row = self.curr_row + 1
                    self.queue.put((self.curr_row, self.curr_col, self.curr_orient))
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "S"
        print "drivings done in drivethread"
	return

class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient):
        self.sock = None
        self.node_id = node_id
        self.drivingState = drivingState
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient

    def run(self):
        # Create a TCP/IP Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print 'Connecting to %s port %s' % server_address
        self.sock.connect(server_address)

        chk_msg = 'CHK'+str(self.node_id)+str(self.curr_row)+str(self.curr_col)
        received_ack = False
        drive_comms_queue = Queue.Queue()
        command_queue = Queue.Queue()
        send_thread = MarshallCommsThread(self.sock, drive_comms_queue)  
        send_thread.start()
        # Send CHK message to reveal yourself to the Marshall
        print 'Sending "%s"' % chk_msg
        self.sock.sendall(chk_msg)
        print "Waiting for ACK..."

        # Look for the ACK from marshall
        while not received_ack:
            data = self.sock.recv(4)
            if data.lower() == "ack":
                received_ack = True
                print 'Received "%s"' % data
    
        while True:
            # Listen data
            data = self.sock.recv(16)
            
            # You received a command!
            if data != None and len(data) == 3 and data[0] == str(self.node_id):
                print 'Received "%s"' % data
                dest_row = data[1]
                dest_col = data[2]
                command_queue.put((dest_row, dest_col))

            if self.drivingState == False and not command_queue.empty():
                print "gonna start driving!"
                (dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.curr_row, self.curr_col, self.curr_orient, dest_row, dest_col, drive_comms_queue)
                self.drivingState = True
                drivingThread.start()
                drivingThread.join()        
                self.drivingState = False

        print 'Closing socket'
        send_thread.join()
        self.sock.close()
        motors.setSpeeds(0, 0)
        GPIO.cleanup()

if "__main__" == __name__:
    node = Node(0, False, 0, 0, 'E')
    node.run()
    print "\nTerminated"
    os._exit(0)

