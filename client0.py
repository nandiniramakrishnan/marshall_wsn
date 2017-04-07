from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO

# Server address
server_address = ('128.237.202.197', 10000)

# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
class DriverThread(Thread):
    def __init__(self, curr_row, curr_col, curr_orient, dest_row, dest_col, queue):
        Thread.__init__(self)
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.dest_row = int(row)
        self.dest_col = int(col)
        self.queue = queue

    def run(self):
        # Obtain directions to the destination and store in path
        path = DF.path_plan(curr_row, curr_col, self.row, self.col)

        #follow path to destination
        #follows E/W and then N/S
        while (self.curr_col != self.dest_col):
            if (path['E'] > 0):
                if (DF.line_follow(self.curr_orient, "E") == 0):
                    path['E'] = path['E']-1	
                    self.curr_col = self.curr_col + 1
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "E"
            elif (path['W'] > 0):
                if (DF.line_follow(self.curr_orient, "W") == 0):
                    path['W'] = path['W'] - 1
                    self.curr_col = self.curr_col - 1
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "W"
            queue.put((self.curr_row, self.curr_col, self.curr_orient))

        while (self.curr_row != dest_row):
            if (path['N'] > 0):
                if (DF.line_follow(curr_orient, "N") == 0):
                    path['N'] = path['N']-1
                    self.curr_row = self.curr_row - 1
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "N"
            elif (path['S'] > 0):
                if (DF.line_follow(curr_orient, "S") == 0):
                    path['S'] = path['S']-1
                    self.curr_row = self.curr_row + 1
                else:
                    print("went off grid, mission failed")
                    return
                self.curr_orient = "S"
            queue.put((self.curr_row, self.curr_col, self.curr_orient))
        return

class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient):
        self.sock = None
        self.thread_list = []
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
        
        # Send CHK message to reveal yourself to the Marshall
        print 'Sending "%s"' % chk_msg
        sock.sendall(chk_msg)
        print "Waiting for ACK..."

        # Look for the ACK from marshall
        while not received_ack:
            data = self.sock.recv(16)
            if data:
                received_ack = True
                print 'Received "%s"' % data
    
        # Now you're ready to receive commands and drive around
        while True:
            # if socket connection is not alive, try to get it back
            
            # Listen data
            data = sock.recv(16)
            # You received a command!
            if data != None and len(data) == 3:
                print 'Received "%s"' % data
                dest_row = data[1]
                dest_col = data[2]
                command_queue.put((dest_row, dest_col))

            if self.drivingState == False and not command_queue.empty():
                (dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.curr_row, self.curr_col, self.curr_orient, dest_row, dest_col, drive_comms_queue)
                self.thread_list.append(drivingThread)
                self.drivingState = True
                drivingThread.start()

            for thread in self.thread_list:
                if not thread.isAlive():
                    self.drivingState = False
                    self.thread_list.remove(thread)
                    thread.join()

            if not drive_comms_queue.empty():
                new_pos = drive_comms_queue.get()
                self.curr_row = new_pos[0]
                self.curr_col = new_pos[1]
                self.curr_orient = new_pos[2]
                new_buf = [ str(self.node_id), str(self.curr_row), str(self.curr_col) ]
                new_msg = ''.join(new_buf)
                self.sock.sendall(new_msg)
    
        print 'Closing socket'
        self.sock.close()
        motors.setSpeeds(0, 0)
        GPIO.cleanup()

if "__main__" == __name__:
    node = Node(0, False, 0, 0, 'E')
    node.run()
    print "\nTerminated"
    os._exit(0)

