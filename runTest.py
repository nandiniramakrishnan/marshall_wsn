#from pololu_drv8835_rpi import motors
import time 
import socket
from threading import Thread
import Queue
import drive_fcns as DF
import RPi.GPIO as GPIO
import os

# Server address
server_address = ('128.237.160.61', 10000)

#Global Intersections to Avoid List
avoid_list = []

node_id = 0
max_row = 2
max_col = 3


# This is the target function of all DRIVING threads. Only DRIVING to happen here.
# Communication with DRIVING thread will happen with argument "queue".
# This function will call line following (all sensing and actuation code)
class DriverThread(Thread):
    def __init__(self, curr_row, curr_col, curr_orient, next_row, next_col, dest_row, dest_col, queue):
        Thread.__init__(self)
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.next_row = next_row
        self.next_col = next_col
        self.dest_row = int(dest_row)
        self.dest_col = int(dest_col)
       # self.queue = queue

    def detour(self, path, direction, length): 
        if (length == 1):
            #detour E
            if (direction == 'E'):
                if (self.curr_row == 0): #top boundary, can't go north
                    if ((self.next_row + 1, self.next_col) in avoid_list): #south location blocked too
                        if(self.curr_col == 0): #left boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go west
                            path = [('W', 1), ('S', 2)] + [('E', path[0][1] + 1)] + [('N', 2)]
                            self.next_col = self.next_col - 1
                    else: #go south
                        path = [('S', 1)] + path + [('N', 1)]
                        self.next_row = self.next_row + 1
                elif (self.curr_row == max_row): #bottom boundary, can't go south
                    if ((self.next_row - 1, self.next_col) in avoid_list): #north location blocked too
                        if(self.curr_col == 0): #left boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go west
                            path = [('W', 1), ('N', 2)] + [('E', path[0][1] + 1)] + [('S', 2)]
                            self.next_col = self.next_col - 1
                    else: #go north
                        path = [('N', 1)] + path + [('S', 1)]
                        self.next_row = self.next_row - 1
                else: #go north by default unless blocked too
                    if ((self.next_row - 1, self.next_col) in avoid_list): #north location blocked
                        path = [('S', 1)] + path + [('N', 1)] #go south
                        self.next_row = self.next_row + 1
                    else: #go north
                        path = [('N', 1)] + path + [('S', 1)]
                        self.next_row = self.next_row - 1
            #detour W
            elif (direction == 'W'):
                if (self.curr_row == 0): #top boundary, can't go north
                    if ((self.next_row + 1, self.next_col) in avoid_list): #south location blocked too
                        if(self.curr_col == max_col): #left boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                        
                            print("I'm stuck")
                        else: #go east
                            path = [('E', 1), ('S', 2)] + [('W', path[0][1] + 1)] + [('N', 2)]
                            self.next_col = self.next_col + 1
                    else: #go south
                        path = [('S', 1)] + path + [('N', 1)]
                        self.next_row = self.next_row + 1
                elif (self.curr_row == max_row): #bottom boundary, can't go south
                    if ((self.next_row - 1, self.next_col) in avoid_list): #north location blocked too
                        if(self.curr_col == max_col): #left boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go west
                            path = [('E', 1), ('N', 2)] + [('W', path[0][1] + 1)] + [('S', 2)]
                            self.next_col = self.next_col + 1
                    else: #go north
                        path = [('N', 1)] + path + [('S', 1)]
                        self.next_row = self.next_row - 1
                else: #go north by default unless blocked too
                    if ((self.next_row - 1, self.next_col) in avoid_list): #north location blocked
                        path = [('S', 1)] + path + [('N', 1)] #go south
                        self.next_row = self.next_row + 1
                    else: #go north
                        path = [('N', 1)] + path + [('S', 1)]
                        self.next_row = self.next_row - 1
            #detour N
            elif (direction == 'N'):
                if (self.curr_col == 0): #left boundary, can't go west
                    if ((self.next_row, self.next_col + 1) in avoid_list): #east location blocked too
                        if (self.curr_row == max_row): #bottom boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go south
                            path = [('S', 1), ('E', 2)] + [('N', path[0][1] + 1)] + [('W', 2)]
                            self.next_row = self.next_row + 1
                    else: #go east
                        path = [('E', 1)] + path + [('W', 1)]
                        self.next_col = self.next_col + 1
                elif (self.curr_col == max_col): #right boundary, can't go east
                    if ((self.next_row, self.next_col - 1) in avoid_list): #west location blocked too
                        if (self.curr_row == max_row): #bottom boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed? 
                             print("I'm stuck")
                        else: #go south
                            path = [('S', 1), ('W', 2)] + [('N', path[0][1] + 1)] + [('E', 2)]
                            self.next_row = self.next_row + 1
                    else: #go west
                        path = [('W', 1)] + path + [('E', 1)]
                        self.next_col = self.next_col - 1
                else: #go west by default unless blocked too
                    if ((self.next_row, self.next_col - 1) in avoid_list): #west location blocked
                        path = [('E', 1)] + path + [('W', 1)] #go east
                        self.next_col = self.next_col + 1
                    else: #go west
                        path = [('W', 1)] + path + [('E', 1)]
                        self.next_col = self.next_col - 1
            #detour S
            elif (direction == 'S'):
                if (self.curr_col == 0): #left boundary, can't go west
                    if ((self.next_row, self.next_col + 1) in avoid_list): #east location blocked too
                        if (self.curr_row == 0): #top boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go north
                            path = [('N', 1), ('E', 2)] + [('S', path[0][1] + 1)] + [('W', 2)]
                            self.next_row = self.next_row - 1
                    else: #go east
                        path = [('E', 1)] + path + [('W', 1)]
                        self.next_col = self.next_col + 1
                elif (self.curr_col == max_col): #right boundary, can't go east
                    if ((self.next_row, self.next_col - 1) in avoid_list): #west location blocked too
                        if (self.curr_row == 0): #top boundary
                            #keep original next loc
                            #send message that blocked in both directions??
                            #don't move until one blockage is removed?
                            print("I'm stuck")
                        else: #go north
                            path = [('N', 1), ('W', 2)] + [('S', path[0][1] + 1)] + [('E', 2)]
                            self.next_row = self.next_row - 1
                    else: #go west
                        path = [('W', 1)] + path + [('E', 1)]
                        self.next_col = self.next_col - 1
                else: #go west by default unless blocked too
                    if ((self.next_row, self.next_col - 1) in avoid_list): #west location blocked
                        path = [('E', 1)] + path + [('W', 1)] #go east
                        self.next_col = self.next_col + 1
                    else: #go west
                        path = [('W', 1)] + path + [('E', 1)]
                        self.next_col = self.next_col - 1

        elif (length == 2):
            if (direction == 'E'):
                if (self.curr_row == 0): #top boundary, try south first
                    if ((self.next_row + 1, self.next_col) in avoid_list): #check if south blocked
                        if (self.curr_col == 0): #left boundary
                            #stuck
                            print("I'm stuck")
                        else: #go west
                            if (path[1][1] == 1):
                                path = [('W', 1), ('S', 2)] + [('E', path[0][1] + 1)] + [('N', 1)]
                            else:
                                path = [('W', 1)] + [path[1]] + [('E', path[0][1] + 1)]
                            self.next_col = self.next_col - 1
                    else: #go south first, then east
                        path = [path[1], path[0]]
                        self.next_row = self.next_row + 1
                elif (self.curr_row == max_row): #bottom boundary, try north first
                    if ((self.next_row - 1, self.next_col) in avoid_list): #check if north blocked
                        if (self.curr_col == 0): #left boundary
                            #stuck
                            print("I'm stuck")
                        else: #go west
                            if (path[1][1] == 1):
                                path = [('W', 1), ('N', 2)] + [('E', path[0][1] + 1)] + [('S', 1)]
                            else:
                                path = [('W', 1)] + [path[1]] + [('E', path[0][1] + 1)]
                            self.next_col = self.next_col - 1
                    else: #go north first, then east
                        path = [path[1], path[0]]
                        self.next_row = self.next_row - 1
                else: #default N/S
                    if (path[1][0] == 'N'):
                        if ((self.next_row - 1, self.next_col) in avoid_list): #check if north blocked
                            #if ((self.next_row + 1, self.next_col) in avoid_list): #try south, add for cmd detours
                            if (path[0][1] > path[1][1]):# E > N, go south
                                if (path[0][1] == 1):
                                    path = [('S', 1),('E', 2)] + [('N', path[1][1] + 1)] + [('W', 1)]
                                else:
                                    path = [('S', 1)] + [path[0]] + [('N', path[1][1]+1)] #go south
                                self.next_row = self.next_row + 1
                            else: #go west
                                if (path[1][1] == 1):
                                    path = [('W', 1), ('N', 2)] + [('E', path[0][1] + 1)] + [('S', 1)]
                                else:
                                    path = [('W', 1)] + [path[1]] + [('E', path[0][1] + 1)]
                                self.next_col = self.next_col - 1
                        else: #go north first, then east
                            path = [path[1], path[0]]
                            self.next_row = self.next_row - 1
                    elif (path[1][0] == 'S'):
                        if ((self.next_row + 1, self.next_col) in avoid_list): #check if south blocked
                            #if ((self.next_row - 1, self.next_col) in avoid_list): #try north, add for cmd detours
                            if (path[0][1] > path[1][1]):# E > S, go north
                                if (path[0][1] == 1):
                                    path = [('N', 1),('E', 2)] + [('S', path[1][1] + 1)] + [('W', 1)]
                                else:
                                    path = [('N', 1)] + [path[0]] + [('S', path[1][1]+1)] #go north
                                self.next_row = self.next_row - 1
                            else: #go west
                                if (path[1][1] == 1):
                                    path = [('W', 1), ('S', 2)] + [('E', path[0][1] + 1)] + [('N', 1)]
                                else:
                                    path = [('W', 1)] + [path[1]] + [('E', path[0][1] + 1)]
                                self.next_col = self.next_col - 1
                        else: #go south first, then east
                            path = [path[1], path[0]]
                            self.next_row = self.next_row + 1
            elif (direction == 'W'):
                if (self.curr_row == 0): #top boundary, try south first
                    if ((self.next_row + 1, self.next_col) in avoid_list): #check if south blocked
                        if (self.curr_col == max_col): #right boundary
                            #stuck
                            print("I'm stuck")
                        else: #go east
                            if (path[1][1] == 1):
                                path = [('E', 1), ('S', 2)] + [('W', path[0][1] + 1)] + [('N', 1)]
                            else:
                                path = [('E', 1)] + [path[1]] + [('W', path[0][1] + 1)]
                            self.next_col = self.next_col + 1
                    else: #go south first, then west
                        path = [path[1], path[0]]
                        self.next_row = self.next_row + 1
                elif (self.curr_row == max_row): #bottom boundary, try north first
                    if ((self.next_row - 1, self.next_col) in avoid_list): #check if north blocked
                        if (self.curr_col == max_col): #left boundary
                            #stuck
                            print("I'm stuck")
                        else: #go east
                            if (path[1][1] == 1):
                                path = [('E', 1), ('N', 2)] + [('W', path[0][1] + 1)] + [('S', 1)]
                            else:
                                path = [('E', 1)] + [path[1]] + [('W', path[0][1] + 1)]
                            self.next_col = self.next_col + 1
                    else: #go north first, then west
                        path = [path[1], path[0]]
                        self.next_row = self.next_row - 1
                else: #default N/S
                    if (path[1][0] == 'N'):
                        if ((self.next_row - 1, self.next_col) in avoid_list): #check if north blocked
                            #if ((self.next_row + 1, self.next_col) in avoid_list): #try south, add for cmd detours
                            if (path[0][1] > path[1][1]):# W > N, go south
                                if (path[0][1] == 1):
                                    path = [('S', 1),('W', 2)] + [('N', path[1][1] + 1)] + [('E', 1)]
                                else:
                                    path = [('S', 1)] + [path[0]] + [('N', path[1][1]+1)] #go south
                                self.next_row = self.next_row + 1
                            else: #go east
                                if (path[1][1] == 1):
                                    path = [('E', 1), ('N', 2)] + [('W', path[0][1] + 1)] + [('S', 1)]
                                else:
                                    path = [('E', 1)] + [path[1]] + [('W', path[0][1] + 1)]
                                self.next_col = self.next_col + 1
                        else: #go north first, then west
                            path = [path[1], path[0]]
                            self.next_row = self.next_row - 1
                    elif (path[1][0] == 'S'):
                        if ((self.next_row + 1, self.next_col) in avoid_list): #check if south blocked
                            #if ((self.next_row - 1, self.next_col) in avoid_list): #try north, add for cmd detours
                            if (path[0][1] > path[1][1]):# W > S, go north
                                if (path[0][1] == 1):
                                    path = [('N', 1),('W', 2)] + [('S', path[1][1] + 1)] + [('E', 1)]
                                else:
                                    path = [('N', 1)] + [path[0]] + [('S', path[1][1]+1)] #go north
                                self.next_row = self.next_row - 1
                            else: #go east
                                if (path[1][1] == 1):
                                    path = [('E', 1), ('S', 2)] + [('W', path[0][1] + 1)] + [('N', 1)]
                                else:
                                    path = [('E', 1)] + [path[1]] + [('W', path[0][1] + 1)]
                                self.next_col = self.next_col + 1
                        else: #go south first, then west
                            path = [path[1], path[0]]
                            self.next_row = self.next_row + 1 
        return path

    def runTrial(self):
        # Obtain directions to the destination and store in path
        path = DF.plan_path(self.curr_row, self.curr_col, self.dest_row, self.dest_col)

        #msg = self.queue.get()
        '''
        #new avoid_list message
        if (msg[0] == 'A' and msg[1] != str(node_id)): 
            avoid_list.append((msg[2], msg[3])) #add row,col pair to list
        elif (msg[0] == 'R' and msg[1] != str(node_id)):
            avoid_list.remove((msg[2], msg[3])) #remove row,col pair from list
        '''
        #destination message
        if (0==1):
            #do nothing
            print("nothing")
        else:
            #follow path to destination
            #follows E/W and then N/S by default

            #put next location information in queue before moving
            if (len(path) > 0):
                if (path[0][0] == 'E'):
                    self.next_col = self.next_col + 1
                elif (path[0][0] == 'W'):
                    self.next_col = self.next_col - 1
                elif (path[0][0] == 'N'):
                    self.next_row = self.next_row - 1
                elif (path[0][0] == 'S'):
                    self.next_row = self.next_row + 1
            #self.queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col))

            if ((self.next_row, self.next_col) in avoid_list):
                if (self.next_row, self.next_col) != (self.dest_row, self.dest_col): #next location is not destination    
                    #undo next_row and next_col changes
                    if (path[0][0] == 'E'):
                        self.next_col = self.next_col - 1
                    elif (path[0][0] == 'W'):
                        self.next_col = self.next_col + 1
                    elif (path[0][0] == 'N'):
                        self.next_row = self.next_row + 1
                    elif (path[0][0] == 'S'):
                        self.next_row = self.next_row - 1
                    #change path
                    if (len(path) == 1): #moving in only one direction to destination
                        #detour E
                        if (path[0][0] == 'E'): #E loc blocked
                            path = self.detour('E', 1)
                        elif (path[0][0] == 'W'): #W loc blocked, go N/S first instead
                            path = self.detour('W', 1)
                        elif (path[0][0] == 'N'): #N blocked, go E/W first instead
                            path =self.detour('N', 1)
                        elif (path[0][0] == 'S'): #N/S blocked, go E/W first instead
                            path =self.detour('S', 1)
                    elif (len(path) == 2):
                        #E direction blocked
                        if (path[0][0] == 'E'):
                            path =self.detour('E', 2) 
                        #W direction blocked
                        if (path[0][0] == 'W'):
                            path =self.detour('W', 2) 
            #send initial next row and col to marshall
        #    self.queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col))

			
			#print path
            print(path)
            print(self.curr_row)
            print(self.curr_col)
            print(self.next_row)
            print(self.next_col)
            print('\n')

            '''
            while (len(path) > 0): #still traveling to destination
                if (len(path) == 1):
                    if (DF.line_follow(self.curr_orient, path[0][0]) == 0): #drive to next intersection
                        if (path[0][1] != 1): #update next location until last move
                            if (path[0][0] == 'E'):
                                self.next_col = self.next_col + 1
                            elif (path[0][0] == 'W'):
                                self.next_col = self.next_col - 1
                            elif (path[0][0] == 'N'):
                                self.next_row = self.next_row - 1
                            elif (path[0][0] == 'S'):
                                self.next_row = self.next_row + 1
                        path[0]=(path[0][0], path[0][1] - 1) #decrement direction number
                        #update curr_col
                        if (path[0][0] == 'E'):
                            self.curr_col = self.curr_col + 1
                        elif (path[0][0] == 'W'):
                            self.curr_col = self.curr_col - 1
                        elif (path[0][0] == 'N'):
                            self.curr_row = self.curr_row - 1
                        elif (path[0][0] == 'S'):
                            self.curr_row = self.curr_row + 1
                    else:
                        print("went off grid, mission failed")
                        return
                    self.curr_orient = path[0][0]
            
                elif (len(path) > 1):
                    if (DF.line_follow(self.curr_orient, path[0][0]) == 0): #drive to next intersection
                        if (path[0][1] != 1): #next_col changes until last east/west
                            if (path[0][0] == 'E'):
                                self.next_col = self.next_col + 1
                            elif (path[0][0] == 'W'):
                                self.next_col = self.next_col - 1
                        else: #last east/west, go north/south next
                            if (path[1][0] == 'N'):
                                self.next_row = self.next_row - 1
                            elif (path[1][0] == 'S'):
                                self.next_row = self.next_row + 1
                        path[0]=(path[0][0], path[0][1] - 1) #decrement direction number
                        #update curr_col
                        if (path[0][0] == 'E'):
                            self.curr_col = self.curr_col + 1
                        elif (path[0][0] == 'W'):
                            self.curr_col = self.curr_col - 1
                    else:
                        print("went off grid, mission failed")
                        return
                    self.curr_orient = path[0][0]
                
                #check next location is okay
                if ((self.next_row, self.next_col) in avoid_list):
                    #undo next_row and next_col changes
                    if (path[0][0] == 'E'):
                        self.next_col = self.next_col - 1
                    elif (path[0][0] == 'W'):
                        self.next_col = self.next_col + 1
                    elif (path[0][0] == 'N'):
                        self.next_row = self.next_row + 1
                    elif (path[0][0] == 'S'):
                        self.next_row = self.next_row - 1
                    #same detour method as above?
                    #...
                    #...
                    #...
                self.queue.put((self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col))

                if (path[0][1] == 0): #remove path instruction from list
                    path = path[1:] #remove first item in list

		'''

        print "drivings done in drivethread"
        return


class Node:
    def __init__(self, node_id, drivingState, curr_row, curr_col, curr_orient, next_row, next_col):
        self.sock = None
        self.thread_list = []
        self.node_id = node_id
        self.drivingState = drivingState
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.curr_orient = curr_orient
        self.next_row = next_row
        self.next_col = next_col

    def run(self):
        for self.curr_row in range(3):
            self.next_row = self.curr_row
            for self.curr_col in range(4):
                self.next_col = self.curr_col
                for self.dest_row in range(3):
                    for self.dest_col in range(4):
                        avoid_list = [(0,1)]
                        DriverThread(self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, dest_row, dest_col)
        '''
   
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
        self.sock.sendall(chk_msg)
        print "Waiting for ACK..."

        # Look for the ACK from marshall
        while not received_ack:
            data = self.sock.recv(16)
            if data:
                received_ack = True
                print 'Received "%s"' % data
    
        while True:
            # You received a command!
            if data != None and len(data) == 3:
                print 'Received "%s"' % data
                dest_row = data[1]
                dest_col = data[2]
                command_queue.put((dest_row, dest_col))

            if self.drivingState == False and not command_queue.empty():
                print "gonna start driving!"
		(dest_row, dest_col) = command_queue.get()
                drivingThread = DriverThread(self.curr_row, self.curr_col, self.curr_orient, self.next_row, self.next_col, dest_row, dest_col, drive_comms_queue)
                self.thread_list.append(drivingThread)
                self.drivingState = True
                drivingThread.start()

            for thread in self.thread_list:
                if not thread.isAlive():
		    print "threads dead"
                    self.drivingState = False
                    self.thread_list.remove(thread)
                    thread.join()

            #newcode
            if not drive_comms_queue.empty():
                print "drive queue is not empty!"
                #new_pos = drive_comms_queue.get()
        		msg = drive_comms_queue.get()
                if (msg[0] =='A' or msg[0] == 'R'): #update intersection avoidance list
                    new_buf = msg
                else: #new_pos
                    self.curr_row = new_pos[0]
                    self.curr_col = new_pos[1]
                    self.curr_orient = new_pos[2]
                    new_buf = [ str(self.node_id), str(self.curr_row), str(self.curr_col) ]
                new_msg = ''.join(new_buf)
                self.sock.sendall(new_msg)
    
            # Listen data
            data = self.sock.recv(16)
        print 'Closing socket'
        self.sock.close()
        motors.setSpeeds(0, 0)
        GPIO.cleanup()
'''



if "__main__" == __name__:
#	drive = DriverThread(

    node = Node(0, False, 0, 0, 'E', 0, 0)
    node.run()
    print "\nTerminated"
    os._exit(0)

