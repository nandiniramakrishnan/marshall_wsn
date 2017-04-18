from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO
import os

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
                print "put quit in queu"
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
                if curr_row == 'q' and curr_col == 'u':
                    print "got quit"
                    break
                new_buf = [ str(self.node_id), str(curr_row), str(curr_col) ]
                new_msg = ''.join(new_buf)
                self.sock.sendall(new_msg)
        print "closing sock in mct" 
        self.sock.close()
        return


# This is the DRIVING CLASS. Only DRIVING to happen here.
# Communication with MARSHALL_COMMS_THREAD will happen with argument "queue".
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
        path = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col)

        #follow path to destination
        #by following the elements in path from left to right
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
       
# This is the Node class
class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient):
        self.sock = None
        self.node_id = node_id
        self.drivingState = drivingState
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.thread_list = []

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
        self.thread_list.append(quit_thread)
        quit_thread.start()
        send_thread = MarshallCommsThread(self.sock, drive_comms_queue, self.node_id)  
        self.thread_list.append(send_thread)
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

                if data != None and len(data) >= 3 and data[0:3] == "ACK":
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
                
                if data != None and len(data) >= 4 and data[0:4] == "quit":
                    break
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
                drive_comms_queue.put("qu")
                break

            if self.drivingState == False and not command_queue.empty():
                print "gonna start driving!"
                (dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.curr_row, self.curr_col, self.curr_orient, dest_row, dest_col, drive_comms_queue)
                self.drivingState = True
                self.thread_list.append(drivingThread)
                drivingThread.start()
                drivingThread.join() 
                self.thread_list.remove(drivingThread)
                self.drivingState = False

        for thread in self.thread_list:
            thread.join()
        print "Joining any driving threads..."
        quit_thread.join()
        print "Joining quit thread.."
        self.sock.close()
        print 'Closing socket'
        motors.setSpeeds(0, 0)
        print "Shutting motors..."
        GPIO.cleanup()
        print "GPIO cleanup... done."
        send_thread.join()
        print "Joining send thread.."
        return


if "__main__" == __name__:
    node = Node(0, False, 0, 0, 'E')
    node.run()
    print "\nTerminated"
    os._exit(0)

