import socket
import os
import sys
from threading import Thread
import time
import Queue

server_address = ('', 10000)
node_state = {'0':{'node_id':0, 'curr_row': 0, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 0, 'next_col': 0, 'next_next_row': 0, 'next_next_col': 0, 'stopped': ('0', 0), 'rerouting':0 }, 
        '1':{'node_id':1, 'curr_row': 1, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 1, 'next_col': 0, 'next_next_row': 1, 'next_next_col': 0, 'stopped': ('0', 0), 'rerouting': 0 }, 
        '2':{'node_id':2, 'curr_row': 2, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 2, 'next_col': 0, 'next_next_row': 2, 'next_next_col': 0, 'stopped': ('0', 0), 'rerouting': 0 } }

queue0 = Queue.Queue()
queue1 = Queue.Queue()
queue2 = Queue.Queue()

class UserInterfaceThread(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        print "Hello from user interface!"
        
        # Filter out invalid commands
        while True:
            command = raw_input("> ")
            if len(command) == 4 and (command[0] == "A" or command[0] == "R"):
                self.queue.put(command)
            elif command.lower() == "quit":
                print "Quitting marshall..."
                self.queue.put(command)
            elif command.lower() == "help":
                print "-\nINSTRUCTIONS:\nEnter a node followed by its destination's row and column\nCommand format: <node-index><row><col>\nExample: 012 # Node 0, Row 1, Col 2\n-"
            elif len(command) != 3:
                print "Invalid length. Try again."
            elif (command[0] != 'G' and command[0] != 'R') and (command[0] < '0' or command[0] > '2'):
                print "Invalid node. Try again. %s" % command[0]
            elif command[1] < '0' or command[1] > '4':
                print "Invalid row. Try again."
            elif command[2] < '0' or command[2] > '6':
                print "Invalid column. Try again."
            else:
                # Adding proper commands to the queue
                self.queue.put(command)
                
        return

class ClientThread(Thread):
    def __init__(self, client_sock, queue, node_id):
        Thread.__init__(self)
        self.client = client_sock
        self.queue = queue
        self.node_id = node_id
    
    def run(self):

        # Start receiving commands from marshall
        while True:
            
            if not self.queue.empty():
                command = self.queue.get()
                if command == "GOOO":
                    print "sending GOOO"
                self.client.sendall(command)
            
            try:
                data = self.client.recv(8)
                if len(data) == 8:
                    node_state[self.node_id]['curr_row'] = data[1]
                    node_state[self.node_id]['curr_col'] = data[2]
                    node_state[self.node_id]['curr_orient'] = data[3]
                    node_state[self.node_id]['next_row'] = data[4]
                    node_state[self.node_id]['next_col'] = data[5]
                    node_state[self.node_id]['next_next_row'] = data[6]
                    node_state[self.node_id]['next_next_col'] = data[7]
                    if node_state[self.node_id]['rerouting'] == 1:
                        node_state[self.node_id]['rerouting'] = 0
                        print "done rerouting"
                    print data
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
            
        print "Closing client socket..."
        self.client.close()
        return


# Multithreaded TCP Server
class Server:

    def __init__(self):
        self.sock = None
        self.thread_list = []
        self.client_list = []
        self.avoid_list = []
        self.stop_list = []

    def check_collision(self, node_a, node_b):   

        curr_pos_a = [node_a['curr_row'], node_a['curr_col']]
        curr_pos_b = [node_b['curr_row'], node_b['curr_col']]
        collision_pos_a = [node_a['next_row'], node_a['next_col']]
        collision_pos_next_a = [node_a['next_next_row'], node_a['next_next_col']]
        collision_pos_b = [node_b['next_row'], node_b['next_col']]
        collision_pos_next_b = [node_b['next_next_row'], node_b['next_next_col']]

        if collision_pos_next_a == collision_pos_b:
            print "next 0 == next next 1"
            return collision_pos_next_a
        elif collision_pos_next_a == collision_pos_next_b:
            print "next next 0 == next next 1"
            return collision_pos_next_a
        else:
            return None

        '''
        if collision_pos_a == collision_pos_next_b:
            print "next 0 == next next 1"
            return (node_b['node_id'], collision_pos_a)
        if collision_pos_b == collision_pos_next_a:
            print "next 1 == next next 0"
            return (node_a['node_id'], collision_pos_next_a)
        if collision_pos_a == collision_pos_b:
            print "next 0 == next 1"
            return (node_a['node_id'], collision_pos_a)
        if collision_pos_next_a == collision_pos_next_b:
            print "next next 0 == next next 1"
            return (node_a['node_id'], collision_pos_next_a)
        else:
            return None
        '''
    def run(self):
        # Server socket indicator
        server_up = False
        # Count for attempts to open server socket (max 3)
        try_count = 0

        global queue0
        global queue1
        global queue2

        # Attempt to open socket
        while not server_up:
            # Tried to open the socket thrice. Exit with an error
            if try_count > 3:
                sys.exit(1)
            try:
                # Create the socket
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind(server_address)
                # Socket can handle upto 3 incoming connections (for each node)
                self.sock.listen(5)
                server_up = True
                break
            except Exception as msg :
                print msg
                print 'Socket connection error... Waiting 10 seconds to retry.'
                del self.sock
                time.sleep(10)
                try_count += 1
        queue = Queue.Queue()
        print "Server is listening for incoming connections"
        ui_thread = UserInterfaceThread(queue)
        self.thread_list.append(ui_thread)
        ui_thread.start()
        try:
            while True:

                # If queue is not empty
                if not queue.empty():
                    command = queue.get()
                    if command.lower() == 'quit':
                        for client in self.client_list:
                            client.sendall('quit')
                            client.close()
                        for thread in self.thread_list:
                            thread.join(1.0)
                        self.sock.close()
                        break
                        
                    if command[0] == 'G':
                        stop_pos = (int(command[1]), int(command[2]))
                        if stop_pos in self.stop_list:
                            self.stop_list.remove(stop_pos)
                        queue0.put("G"+command)
                        queue1.put("G"+command)
                        queue2.put("G"+command)
                    if len(command) == 3 and command[0] == 'R':
                        stop_pos = (int(command[1]), int(command[2]))
                        if stop_pos not in self.stop_list:
                            print "appending to avoid list"
                            print stop_pos
                            self.stop_list.append(stop_pos)
                        queue0.put("R"+command)
                        queue1.put("R"+command)
                        queue2.put("R"+command)
                    elif len(command) == 4 and command[0] == 'R':
                        for client in self.client_list:
                            client.sendall(command)
                    if command[0] == '0':
                        queue0.put(command)
                    elif command[0] == '1':
                        queue1.put(command)
                    elif command[0] == '2':
                        queue2.put(command)
                    elif command[0] == 'A':
                        queue0.put(command)
                    if command[0] == '0' or command[0] == '1' or command[0] == '2':
                        remove_buf = [ command[0], str(node_state[command[0]]['curr_row']), str(node_state[command[0]]['curr_col']) ]
                        remove_msg = ''.join(remove_buf)

                        if remove_msg in self.avoid_list:
                            self.avoid_list.remove(remove_msg)
                            for client in self.client_list:
                                client.sendall("R"+remove_msg)
                        time.sleep(0.5)
                for node_id, node_properties in node_state.iteritems():
                    if node_properties['curr_row'] == node_properties['next_row'] and node_properties['curr_col'] == node_properties['next_col']:
                        avoid_buf = [ node_id, str(node_properties['curr_row']), str(node_properties['curr_col']) ]
                        avoid_msg = ''.join(avoid_buf)
                        if avoid_msg not in self.avoid_list and len(self.client_list) == 2:
                            self.avoid_list.append(avoid_msg)
                            for client in self.client_list:
                                client.sendall("A"+avoid_msg)
                    
                for node_id, node_properties in node_state.iteritems():
                    if node_properties['stopped'][1] == 1:
                        print "node %s is stopped" % node_id
                        print "because node %s was rerouting" % node_properties['stopped'][0]
                        if node_state[node_properties['stopped'][0]]['rerouting'] == 0:
                            print "node %s can continue now" % node_id
                            node_properties['stopped'] = ('0', 0)
                            globals()['queue'+node_id].put("GOOO")

                for node_id, node_properties in node_state.iteritems():
                    curr_pos = (node_properties['curr_row'], node_properties['curr_col'])
                    if curr_pos in self.stop_list:
                        for client in self.client_list:
                            avoid_msg = "A"+node_id+str(node_properties['curr_row']+str(node_properties['curr_col']))
                            print avoid_msg
                            client.sendall(avoid_msg) 
                collision01 = self.check_collision(node_state['0'], node_state['1'])
                collision02 = self.check_collision(node_state['0'], node_state['2'])
                collision12 = self.check_collision(node_state['1'], node_state['2'])
                if collision01 != None:
                    avoid_buf = ['S', 'R', str(collision01[0]), str(collision01[1])]
                    avoid_msg = ''.join(avoid_buf)
                    queue0.put(avoid_msg)
                    node_state['0']['rerouting'] = 1
                    queue1.put('STOP')
                    node_state['1']['stopped'] = ('0', 1)
                    print "collision detected! avoid_msg = %s" % avoid_msg
                if collision02 != None:
                    avoid_buf = ['S', 'R', str(collision02[0]), str(collision02[1])]
                    avoid_msg = ''.join(avoid_buf)
                    queue0.put(avoid_msg)
                    node_state['0']['rerouting'] = 1
                    queue2.put('STOP')
                    node_state['2']['stopped'] = ('0', 1)
                    print "collision detected! avoid_msg = %s" % avoid_msg
                if collision12 != None:
                    avoid_buf = ['S', 'R', str(collision12[0]), str(collision12[1])]
                    avoid_msg = ''.join(avoid_buf)
                    queue1.put(avoid_msg)
                    node_state['1']['rerouting'] = 1
                    queue2.put('STOP')
                    node_state['2']['stopped'] = ('1', 1)
                    print "collision detected! avoid_msg = %s" % avoid_msg

                try:
                    self.sock.settimeout(0.5)
                    client = self.sock.accept()[0]
                except socket.timeout:
                    time.sleep(1)
                    continue
                try:
                    data = client.recv(16)
                    if data != None and len(data) == 6 and data[0:3] == "CHK":
                        curr_row = data[4]
                        curr_col = data[5]
                        if data[3] == '0':
                            new_thread = ClientThread(client, queue0, data[3])
                        elif data[3] == '1':
                            new_thread = ClientThread(client, queue1, data[3])
                        elif data[3] == '2':
                            new_thread = ClientThread(client, queue2, data[3])
                        print "Received CHK, sending ACK..."
                        self.client_list.append(client)
                        self.thread_list.append(new_thread)
                        new_thread.start()
                        client.sendall("ACK")
                except socket.error as ex:
                    if str(ex) == "[Errno 35] Resource temporarily unavailable":
                        time.sleep(0.01)
                        continue
                    else:
                        print ex
                    raise ex
                
                for thread in self.thread_list:
                    if not thread.isAlive():
                        self.thread_list.remove(thread)
                        thread.join()
        except Exception, err:
            print "Something's wrong. errno = %s" % err
            print sys.exc_info()

        for client in self.client_list:
            client.close()

        for thread in self.thread_list:
            thread.join(1.0)
        
        self.sock.close()

if "__main__" == __name__:
    server = Server()
    server.run()
    print "\nTerminated"
    os._exit(0)
