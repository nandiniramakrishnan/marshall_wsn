from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO
import os

#initialize node 0 values
# Server address
server_address = ('128.237.209.71', 10000)
STOPMSG = "STOP"
STOPREROUTEMSG = "STPR"
stop_needed = 0
red_light_list = []

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

class SendThread(Thread):
    def __init__(self, node_id, sock, send_queue):
        Thread.__init__(self)
        self.sock = sock
        self.node_id = node_id
        self.send_queue = send_queue

    def run(self):
        while True:
            if not self.send_queue.empty():
                new_pos = self.send_queue.get()
                curr_row = new_pos[0]
                curr_col = new_pos[1]
                curr_orient = new_pos[2]
                next_row = new_pos[3]
                next_col = new_pos[4]
                nextnextrow = new_pos[5]
                nextnextcol = new_pos[6]
                new_buf = [ str(self.node_id), str(curr_row), str(curr_col), str(curr_orient), str(next_row), str(next_col), str(nextnextrow), str(nextnextcol)]
                new_msg = ''.join(new_buf)
                self.sock.sendall(new_msg)

# This class sends messages to the Marshall while driving
class MarshallCommsThread(Thread):
    def __init__(self, sock, drive_comms_queue, node_id, command_queue, avoid_list_queue, red_light_queue):
        Thread.__init__(self)
        self.sock = sock
        self.drive_comms_queue = drive_comms_queue
        self.node_id = node_id
        self.command_queue = command_queue
        self.avoid_list_queue = avoid_list_queue
        self.red_light_queue = red_light_queue

    def run(self):
        while True:
                
            # Listen data
            try:
                data = self.sock.recv(4)
                
                if data != None and len(data) >= 4 and data[0:4] == "quit":
                    break
                # You received a command!
                if data != None and len(data) == 3 and data[0] == str(self.node_id):
                    print 'Received "%s"' % data
                    dest_row = data[1]
                    dest_col = data[2]
                    self.command_queue.put((dest_row, dest_col))
           
                if data != None and (data[0] == 'R') and (data[1] == 'R'):
                    print('             received red')
                    #handle red light
                    if (int(data[2]), int(data[3])) not in red_light_list:
                        # red_light_list.append((int(data[2]),int(data[3])))
                        self.red_light_queue.put(("R", int(data[2]),int(data[3])))

                if data != None  and len(data)==4 and (data[0] == 'A' or data[0] == 'R'):
                    print ("Received add or Remove from marshall!")
                    print(data)
                    new_buf = (data[0], data[1], data[2], data[3])
                    self.avoid_list_queue.put(new_buf)

                if data != None and data == "STOP":
                    print "Received ",
                    print data
                    #print("stopping!")
                    #motors.setSpeeds(0,0)
                    stop_needed = 1
                    new_buf = (data[0], data[1], data[2], data[3])
                    self.avoid_list_queue.put(new_buf)
                    #time.sleep(5)

                if data != None and data[0] == "S" and data[1] == "R":
                    print "Received %s" % data
                    print("Stop Rerouting!")
                    # motors.setSpeeds(0,0)
                    new_buf = (data[0], data[1], data[2], data[3])
                    self.avoid_list_queue.put(new_buf)
                    #time.sleep(3)

                if data != None  and (data[0] == 'G' and data[1] == 'O'):
                    print ("Received GOOO!")
                    stop_needed = 0
                    #new_buf = (data[0], data[1], data[2], data[3])
                    #self.avoid_list_queue.put(new_buf)

                if data != None and (data[0] == 'G') and (data[1] == 'G'):
                    print('             received green')
                    #handle green light
                    if (int(data[2]), int(data[3])) in red_light_list:
                        self.red_light_queue.put(("G", int(data[2]), int(data[3])))
                    buf = ("S", "D", data[2], data[3])
                    self.avoid_list_queue.put(buf)


            
            except socket.error as ex:
                if str(ex) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.01)
                    continue
                elif str(ex) == "[Errno 54] Connection reset by peer":
                    print "Connection reset. Maybe the original client ended. Try again?"
                    continue
                elif str(ex) == "[Errno 32] Broken pipe":
                    print "broken pipe"
                    break
                raise ex

        print "closing sock in mct" 
        self.sock.close()
        return


# This is the DRIVING CLASS. Only DRIVING to happen here.
# Communication with MARSHALL_COMMS_THREAD will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
class DriverThread(Thread):
    def __init__(self, node_id, red_light_queue, red_light_list,  curr_row, curr_col, curr_orient, next_row, next_col, dest_row, dest_col, avoid_list, drive_comms_queue, update_node_queue, avoid_list_queue, send_queue, nextnextrow, nextnextcol):
        Thread.__init__(self)
        self.node_id = node_id
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.next_row = next_row
        self.next_col = next_col
        self.dest_row = int(dest_row)
        self.dest_col = int(dest_col)
        self.avoid_list = avoid_list
        self.drive_comms_queue = drive_comms_queue
        self.update_node_queue = update_node_queue
        self.avoid_list_queue = avoid_list_queue
        self.send_queue = send_queue
        self.nextnextrow = nextnextrow
        self.nextnextcol = nextnextcol
        self.red_light_queue = red_light_queue

        self.red_light_list = red_light_list
    
    def run(self):
        rerouting = False
        trapped = False
        # Obtain directions to the destination and store in path
        (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
        if (path_coords == "Null" or len(path_coords) <2):
            print("No path found")
            trapped = True
            #path_coords = [(self.curr_row, self.curr_col)]
            #path_dirs = []
        #if len(path_coords) < 2:
            #self.next_row = path_coords[0][0]
            #self.next_col = path_coords[0][1]
            #self.nextnextrow = path_coords[0][0]
            #self.nextnextcol = path_coords[0][1]
        else:
            self.next_row = path_coords[1][0]
            self.next_col = path_coords[1][1]
            #nextDir = DF.getDir((self.curr_row, self.curr_col), (self.next_row, self.next_col))
            #if nextDir == "Null":
            #    nextDir = self.curr_orient
            if len(path_coords) > 2:
                self.nextnextrow = path_coords[2][0]
                self.nextnextcol = path_coords[2][1]
            else:
                self.nextnextrow = self.next_row
                self.nextnextcol = self.next_col
        print "initial path coords = ",
        print path_coords
        print "initial path dirs = ",
        print path_dirs
        self.send_queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, self.nextnextrow, self.nextnextcol))
        msg = 'null'
        while ((self.curr_col != self.dest_col) or (self.curr_row != self.dest_row)) and ((len(path_coords) > 1) or trapped == True):
            #time.sleep(1)
            print "in while loop"
            
            if rerouting == True:
                self.avoid_list.remove(reroute_coords)
                rerouting = False

            while not self.avoid_list_queue.empty():
                print "drive comms queue not empty!"
                msg = self.avoid_list_queue.get()
                #new avoid_list message
            
                print msg
                #while 
                if (msg[0] == 'S' and msg[1] == 'T'):
                    print("                 in stop")
                    motors.setSpeeds(0,0)
                    time.sleep(2)
                    while stop_needed == 1:
                        continue
                    #while self.avoid_list_queue.empty()
                    #go_msg = self.avoid_list_queue.get()
                    #while (go_msg[0] != 'G'):
                    #    motors.setSpeeds(0,0)
                    #    time.sleep(2)


                elif (msg[0] == 'A'):
                    print ("adding")
                    if (msg[1] != str(self.node_id) or msg[1] == 'D'):
                        if ((int(msg[2]), int(msg[3])) not in self.avoid_list):
                            print ("adding to avoid list")
                            self.avoid_list.append((int(msg[2]), int(msg[3]))) #add row,col pair to list
                            (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
                            print("path after adding",)
                            print(path_coords)
                            if path_coords == "Null":
                                print("No path found")
                                trapped = True
                                path_coords = [(self.curr_row, self.curr_col)]
                                path_dirs = []
                                self.next_row = path_coords[0][0]
                                self.next_col = path_coords[0][1]
                                self.nextnextrow = path_coords[0][0]
                                self.nextnextcol = path_coords[0][1]
                            else:
                                self.next_row = path_coords[1][0]
                                self.next_col = path_coords[1][1]
                                if len(path_coords) > 2:
                                    self.nextnextrow = path_coords[2][0]
                                    self.nextnextcol = path_coords[2][1]
                                else:
                                    self.nextnextrow = self.next_row
                                    self.nextnextcol = self.next_col
                elif (msg[0] == 'R'):
                    print ("removing")
                    if (msg[1] != str(self.node_id) or msg[1] == 'D'):
                        if (self.avoid_list == [] or ((int(msg[2]), int(msg[3])) not in self.avoid_list)):
                            #do nothing
                            print("nothing to remove in avoidlist")
                            self.avoid_list = self.avoid_list
                        else:
                            print ("removing from avoid list")
                            self.avoid_list.remove((int(msg[2]), int(msg[3]))) #remove row,col pair from list
                            (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
                            self.next_row = path_coords[1][0]
                            self.next_col = path_coords[1][1]
                            if len(path_coords) > 2:
                                self.nextnextrow = path_coords[2][0]
                                self.nextnextcol = path_coords[2][1]
                            else:
                                self.nextnextrow = self.next_row
                                self.nextnextcol = self.next_col
                #elif (msg[0] == 'S' and msg[1] == 'T'):
                #    print("                 in stop")
                #    motors.setSpeeds(0,0)
                #    time.sleep(2)
    
                elif (msg[0] == 'S' and msg[1] =='R'):
                    print("in stopr")
                    #motors.setSpeeds(0,0)
                    #time.sleep(3) #reroute
                    #reroute....
                    #reroute_coord = path_coords[1]; #potential collision at next (row, col)
                    reroute_coords = (int(msg[2]), int(msg[3]))
                    if ((int(msg[2]), int(msg[3])) not in self.avoid_list) and not (int(msg[2]) == self.dest_row and int(msg[3]) == self.dest_col):
                        self.avoid_list.append(reroute_coords)
                        rerouting = True
                    elif (int(msg[2]) == self.dest_row and int(msg[3]) == self.dest_col):
                        motors.setSpeeds(0,0)
                        time.sleep(2)
                    (path_coords, path_dirs) = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col, self.avoid_list)
                    self.next_row = path_coords[1][0]
                    self.next_col = path_coords[1][1]
                    if len(path_coords) > 2:
                        self.nextnextrow = path_coords[2][0]
                        self.nextnextcol = path_coords[2][1]
                    else:
                        self.nextnextrow = self.next_row
                        self.nextnextcol = self.next_col
            
            print "avoid_list", 
            print self.avoid_list
            print "path coords = ",
            print path_coords
            print "path dirs = ",
            print path_dirs
            if path_dirs == []:
                next_orient = self.curr_orient
            else:
                next_orient = path_dirs[0] #will be "N" "S" "E" or "W"

            while not self.red_light_queue.empty():
                msg = self.red_light_queue.get()
                #print("     red light msg:")
                #print msg
                if msg[0] == "R":
                    self.red_light_list.append((msg[1], msg[2]))
                if msg[0] == "G":
                    if (msg[1],msg[2]) in self.red_light_list:
                        self.red_light_list.remove((msg[1], msg[2]))

            #print("red lgiht list:")
            #print self.red_light_list
            #handle red lights
            while (self.curr_row, self.curr_col) in self.red_light_list:
                #motors.setSpeeds(0,0)
                #time.sleep(0.001)
                #print self.red_light_list
                while not self.red_light_queue.empty():
                    msg = self.red_light_queue.get()
                    #print("     red light msg:")
                    #print msg
                    if msg[0] == "R":
                        self.red_light_list.append((msg[1], msg[2]))
                    if msg[0] == "G":
                        if (msg[1],msg[2]) in self.red_light_list:
                            self.red_light_list.remove((msg[1], msg[2]))
                
            if len(path_coords) > 1:
                trapped = False
                if (DF.line_follow(self.curr_orient, next_orient) == 0):
                    #update curr and next locs
                    if len(path_coords) == 2:
                        self.next_row = path_coords[1][0]
                        self.next_col = path_coords[1][1]
                    else:
                        self.next_row = path_coords[2][0]
                        self.next_col = path_coords[2][1]
                    self.curr_row = path_coords[1][0]
                    self.curr_col = path_coords[1][1]
                    self.curr_orient = path_dirs[0]
                    
                    if len(path_coords) > 3:
                        self.nextnextrow = path_coords[3][0]
                        self.nextnextcol = path_coords[3][1]
                    else:
                        self.nextnextrow = self.next_row
                        self.nextnextcol = self.next_col
                    #nextDir = DF.getDir((self.curr_row, self.curr_col), (self.next_row, self.next_col))
                    #if nextDir == "Null":
                    #    nextDir = self.curr_orient
                    #update path coords and dirs
                    path_coords = path_coords[1:]
                    path_dirs = path_dirs[1:]

                    #self.drive_comms_queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, nextnextrow, nextnextcol))
                    self.send_queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, self.nextnextrow, self.nextnextcol))
                else:
                    #move was unsuccessful
                    print "went off grid, mission failed"
                    return
        #reached destination, update next and curr locs            
        self.curr_row = path_coords[0][0]
        self.curr_col = path_coords[0][1]
        self.next_row = path_coords[0][0]
        self.next_col = path_coords[0][1]
        self.nextnextrow = path_coords[0][0]
        self.nextnextcol = path_coords[0][1]
        self.update_node_queue.put((self.curr_row, self.curr_col, self.curr_orient))
        return
       
# This is the Node class
class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient, next_row, next_col, avoid_list, red_light_list):
        self.sock = None
        self.node_id = node_id
        self.drivingState = drivingState
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.thread_list = []
        self.next_row = next_row
        self.next_col = next_col
        self.nextnextrow = next_row
        self.nextnextcol = next_col
        self.avoid_list = avoid_list
        self.red_light_list = red_light_list

    def run(self):
        # Create a TCP/IP Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print 'Connecting to %s port %s' % server_address
        self.sock.connect(server_address)

        chk_msg = 'CHK'+str(self.node_id)+str(self.curr_row)+str(self.curr_col)
        received_ack = False
        #
        drive_comms_queue = Queue.Queue()
        command_queue = Queue.Queue()
        quit_queue = Queue.Queue()
        update_node_queue = Queue.Queue()
        avoid_list_queue = Queue.Queue()
        send_queue = Queue.Queue()
        red_light_queue = Queue.Queue()
        #
        quit_thread = QuitThread(quit_queue)
        self.thread_list.append(quit_thread)
        quit_thread.start()
        #
        # Send CHK message to reveal yourself to the Marshall
        print 'Sending "%s"' % chk_msg
        self.sock.sendall(chk_msg)
        print "Waiting for ACK..."

        # Look for the ACK from marshall
        while not received_ack:
            try:
                data = self.sock.recv(3)
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
        
        
        marshall_comms_thread = MarshallCommsThread(self.sock, drive_comms_queue, self.node_id, command_queue, avoid_list_queue, red_light_queue)  
        self.thread_list.append(marshall_comms_thread)
        marshall_comms_thread.start()
        send_thread = SendThread(self.node_id, self.sock, send_queue)
        self.thread_list.append(send_thread)
        send_thread.start()

        while True:
            if not quit_queue.empty():
                #print "putting qu in drive comms queue"
                #drive_comms_queue.put("qu")
                break

            if self.drivingState == False and not command_queue.empty():
                print "gonna start driving!"
                (dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.node_id, red_light_queue, self.red_light_list,  self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, dest_row, dest_col, self.avoid_list, drive_comms_queue, update_node_queue, avoid_list_queue, send_queue, self.nextnextrow, self.nextnextcol)
                self.drivingState = True
                self.thread_list.append(drivingThread)
                drivingThread.start()
                drivingThread.join() 
                self.thread_list.remove(drivingThread)
                self.drivingState = False
                if not update_node_queue.empty():
                    updated_pos = update_node_queue.get()
                    self.curr_row = updated_pos[0]
                    self.curr_col = updated_pos[1]
                    self.curr_orient = updated_pos[2]

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
    node_id = 0
    curr_row = 0
    curr_col = 5
    curr_orient = 'W'
    next_row = 0
    next_col = 5
    avoid_list = []
    red_light_list = []
    node = Node(node_id, False, curr_row, curr_col, curr_orient, next_row, next_col, avoid_list, red_light_list)
    node.run()
    print "\nTerminated"
    os._exit(0)

