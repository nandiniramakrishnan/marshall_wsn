from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO
import os

#initialize node 0 values
node_id = 0
curr_row = 0
curr_col = 0
curr_orient = 'E'
next_row = 0
next_col = 0
avoid_list = []

# Server address
server_address = ('128.237.193.177', 10000)
STOPMSG = "STOP"
STOPREROUTEMSG = "STOPR"

class QuitThread(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            command = raw_input("")
            if command == 'q':
                print "put quit in queue"
                self.queue.put(command)
                break
        return


# This class sends messages to the Marshall while driving
class MarshallCommsThread(Thread):
    def __init__(self, sock, queue, node_id):
        Thread.__init__(self)
        self.sock = sock
        self.queue = queue
        self.node_id = node_id

    def run(self):
        while True:
            if not self.queue.empty():
                new_pos = self.queue.get()
                curr_row = new_pos[0]
                curr_col = new_pos[1]
                new_buf = [ str(self.node_id), str(curr_row), str(curr_col) ]
                new_msg = ''.join(new_buf)
                self.sock.sendall(new_msg)
        return


# This is the DRIVING CLASS. Only DRIVING to happen here.
# Communication with MARSHALL_COMMS_THREAD will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
class DriverThread(Thread):
    def __init__(self, curr_row, curr_col, curr_orient, next_row, next_col, dest_row, dest_col, avoid_list, queue):
        Thread.__init__(self)
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.next_row = next_row
        self.next_col = next_col
        self.dest_row = int(dest_row)
        self.dest_col = int(dest_col)
        self.avoid_list = avoid_list
        self.queue = queue

    def run(self):

        rerouting = False
        # Obtain directions to the destination and store in path
        (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
        
        self.next_row = path_coords[1][0]
        self.next_col = path_coords[1][1]
        self.queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col))

        while ((self.curr_col != self.dest_col) or (self.curr_row != self.dest_row)) and (len(path_coords) > 1):
            if rerouting == True:
                self.avoid_list.remove(reroute_coord)
                rerouting = False

            msg = self.queue.get()
            #new avoid_list message
            if (msg[0] == 'A' and msg[1] != str(node_id)): 
                self.avoid_list.append((int(msg[2]), int(msg[3]))) #add row,col pair to list
                (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
            elif (msg[0] == 'R' and msg[1] != str(node_id)):
                self.avoid_list.remove((int(msg[2]), int(msg[3]))) #remove row,col pair from list
                (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
            elif (msg == 'STOP'):
                time.sleep(3)
            elif (msg == 'STOPR'):
                time.sleep(3) #reroute
                #reroute....
                rerouting = True
                reroute_coord = path_coords[1]; #potential collision at next (row, col)
                self.avoid_list.append(reroute_coord)
                (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)

            
            next_orient = path_dirs[0] #will be "N" "S" "E" or "W"
            if (DF.line_follow(self.curr_orient, next_orient) == 0):
                #update curr and next locs
                self.curr_row = path_coords[0][0]
                self.curr_col = path_coords[0][1]
                self.next_row = path_coords[1][0]
                self.next_col = path_coords[1][1]
                self.curr_orient = path_dirs[0]
                #update path coords and dirs
                path_coords = path_coords[1:]
                path_dirs = path_dirs[1:]
                self.queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col))
            else:
                #move was unsuccessful
                print "went off grid, mission failed"
                return
        #reached destination, update next and curr locs            
        self.curr_row = path_coords[0][0]
        self.curr_col = path_coords[0][1]
        self.next_row = path_coords[0][0]
        self.next_col = path_coords[0][1]
        return
        '''
        #follow path to destination
        #while the destination has not been reached
        while ((self.curr_col != self.dest_col) or (self.curr_row != self.dest_row)) and (len(path) > 0):
			direction = path[0][0] #will be "N" "S" "E" or "W"
			length = int(path[0][1]) #some number of roads to drive in direction
			while (length > 0):
				if (DF.line_follow(self.curr_orient, direction) == 0):
					#move was successful, update position and direction
					length = length - 1
					self.curr_row = DF.update_row(self.curr_row, direction)
					self.curr_col = DF.update_col(self.curr_col, direction)
					self.curr_orient = direction
					self.queue.put((self.curr_row, self.curr_col, self.curr_orient))
				else:
					#move was unsuccessful
					print "went off grid, mission failed"
					return
			#update path once movement in direction is complete by removing first element
			path = path[1:]
        #return
        '''
       
# This is the Node class
class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient, next_row, next_col, avoid_list):
        self.sock = None
        self.node_id = node_id
        self.drivingState = drivingState
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.next_row = next_row
        self.next_col = next_col
        self.avoid_list = avoid_list

    def run(self):
        # Create a TCP/IP Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print 'Connecting to %s port %s' % server_address
        self.sock.connect(server_address)

        chk_msg = 'CHK'+str(self.node_id)+str(self.curr_row)+str(self.curr_col)
        received_ack = False
        drive_comms_queue = Queue.Queue()
        command_queue = Queue.Queue()
        quit_queue = Queue.Queue()
        quit_thread = QuitThread(quit_queue)
        quit_thread.start()
        send_thread = MarshallCommsThread(self.sock, drive_comms_queue, self.node_id)  
        send_thread.start()
        # Send CHK message to reveal yourself to the Marshall
        print 'Sending "%s"' % chk_msg
        self.sock.sendall(chk_msg)
        print "Waiting for ACK..."

        # Look for the ACK from marshall
        while not received_ack:
            try:
                data = self.sock.recv(16)
                if not quit_queue.empty():
                    break

                if data.lower() == "ack":
                    received_ack = True
                    print 'Received "%s"' % data
            except socket.error as ex:
                if str(ex) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.01)
                    continue
                elif str(ex) == "[Errno 54] Connection reset by peer":
                    print "Connection reset. Maybe the original client ended. Try again?"
                    continue
                elif str(ex) == "[Errno 9] Bad file descriptor":
                    print "Client's dead.. ending this thread."
                    break
                elif str(ex) == "[Errno 32] Broken pipe":
                    print "broken pipe"
                    break
                raise ex
        
        while True:
            # Listen data
            try:
                data = self.sock.recv(16)
            
                # You received a command!
                if data != None and len(data) == 3 and data[0] == str(self.node_id):
                    print 'Received "%s"' % data
                    dest_row = data[1]
                    dest_col = data[2]
                    command_queue.put((dest_row, dest_col))
            
                if data == STOPMSG:
                    print "Received ",
                    print data

                if data == STOPREROUTEMSG:
                    print "Received %s" % data
            except socket.error as ex:
                if str(ex) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.01)
                    continue
                elif str(ex) == "[Errno 54] Connection reset by peer":
                    print "Connection reset. Maybe the original client ended. Try again?"
                    continue
                elif str(ex) == "[Errno 9] Bad file descriptor":
                    print "Client's dead.. ending this thread."
                    break
                elif str(ex) == "[Errno 32] Broken pipe":
                    print "broken pipe"
                    break
                raise ex
            if not quit_queue.empty():
                if drivingThread != None:
                    drivingThread.join()
                break

            if self.drivingState == False and not command_queue.empty():
                print "gonna start driving!"
                (dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, dest_row, dest_col, self.avoid_list, drive_comms_queue)
                self.drivingState = True
                drivingThread.start()
                drivingThread.join()        
                self.drivingState = False

        print 'Closing socket'
        quit_thread.join()
        send_thread.join()
        self.sock.close()
        motors.setSpeeds(0, 0)
        GPIO.cleanup()

if "__main__" == __name__:
    node = Node(node_id, False, curr_row, curr_col, curr_orient, next_row, next_col, avoid_list)
    node.run()
    print "\nTerminated"
    os._exit(0)

