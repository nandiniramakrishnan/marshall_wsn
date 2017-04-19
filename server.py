import socket
import os
import sys
from threading import Thread
import time
import Queue

server_address = ('', 10000)
node_state = {'0':{'curr_row': 0, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 0, 'next_col': 0}, 
        '1':{'curr_row': 1, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 1, 'next_col': 0}, 
        '2':{'curr_row': 2, 'curr_col': 0, 'curr_orient': 'E', 'next_row': 2, 'next_col': 0} }

class UserInterfaceThread(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        print "Hello from user interface!"
        
        # Filter out invalid commands
        while True:
            command = raw_input("> ")
            if command.lower() == "quit":
                print "Quitting marshall..."
                self.queue.put(command)
            elif command.lower() == "help":
                print "-\nINSTRUCTIONS:\nEnter a node followed by its destination's row and column\nCommand format: <node-index><row><col>\nExample: 012 # Node 0, Row 1, Col 2\n-"
            elif len(command) != 3:
                print "Invalid length. Try again."
            elif command[0] < '0' or command[0] > '2':
                print "Invalid node. Try again."
            elif command[1] < '0' or command[1] > '4':
                print "Invalid row. Try again."
            elif command[2] < '0' or command[2] > '6':
                print "Invalid column. Try again."
            else:
                # Adding proper commands to the queue
                self.queue.put(command)
        return

class ClientThread(Thread):
    def __init__(self, client_sock, queue, curr_row, curr_col, node_id):
        Thread.__init__(self)
        self.client = client_sock
        self.queue = queue
        self.curr_row = curr_row
        self.curr_col = curr_col
        self.node_id = node_id
    
    def run(self):

        # Start receiving commands from marshall
        while True:
            # if client sock is not up
            
            if not self.queue.empty():
                command = self.queue.get()
                self.client.sendall(command)
                
            try:
                data = self.client.recv(6)
                if len(data) == 6:
                    node_state[self.node_id]['curr_row'] = data[1]
                    node_state[self.node_id]['curr_col'] = data[2]
                    node_state[self.node_id]['curr_orient'] = data[3]
                    node_state[self.node_id]['next_row'] = data[4]
                    node_state[self.node_id]['next_col'] = data[5]
                    print data
            except socket.error as ex:
                if str(ex) == "[Errno 35] Resource temporarily unavailable":
                    time.sleep(0.01)
                    continue
                elif str(ex) == "[Errno 54] Connection reset by peer":
                    print "Connection reset. Maybe the original client ended. Try again?"
                    continue
                #elif str(ex) == "[Errno 9] Bad file descriptor":
                #    print "Client's dead.. ending this thread."
                #    break
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

    def run(self):
        # Server socket indicator
        server_up = False
        # Count for attempts to open server socket (max 3)
        try_count = 0


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
        queue0 = Queue.Queue()
        queue1 = Queue.Queue()
        queue2 = Queue.Queue()
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
                    if command[0] == '0':
                        queue0.put(command)
                        new_buf = [ 'R', str(node_state['0']['curr_row']), str(node_state['0']['curr_col']) ]
                        new_msg = ''.join(new_buf) 
                        queue1.put(new_msg)
                        queue2.put(new_msg)
                    elif command[0] == '1':
                        queue1.put(command)
                        new_buf = [ 'R', str(node_state['1']['curr_row']), str(node_state['1']['curr_col']) ]
                        new_msg = ''.join(new_buf) 
                        queue0.put(new_msg)
                        queue2.put(new_msg)
                    elif command[0] == '2':
                        queue2.put(command)
                        new_buf = [ 'R', str(node_state['2']['curr_row']), str(node_state['2']['curr_col']) ]
                        new_msg = ''.join(new_buf) 
                        queue0.put(new_msg)
                        queue1.put(new_msg)
                try:
                    self.sock.settimeout(0.5)
                    client = self.sock.accept()[0]
                    print client
                except socket.timeout:
                    time.sleep(1)
                    continue
                try:
                    data = client.recv(16)
                    if data != None and len(data) == 6 and data[0:3] == "CHK":
                        curr_row = data[4]
                        curr_col = data[5]
                        if data[3] == '0':
                            new_thread = ClientThread(client, queue0, curr_row, curr_col, data[3])
                        elif data[3] == '1':
                            new_thread = ClientThread(client, queue1, curr_row, curr_col, data[3])
                        elif data[3] == '2':
                            new_thread = ClientThread(client, queue2, curr_row, curr_col, data[3])
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
                
                if ((node_state['0']['curr_row'] == node_state['0']['next_row']) and (node_state['0']['curr_col'] == node_state['0']['next_col'])):
                    new_buf = [ 'A', str(node_state['0']['curr_row']), str(node_state['0']['curr_col']) ]
                    new_msg = ''.join(new_buf) 
                    queue1.put(new_msg)
                    queue2.put(new_msg)
                if ((node_state['1']['curr_row'] == node_state['1']['next_row']) and (node_state['1']['curr_col'] == node_state['1']['next_col'])):
                    new_buf = [ 'A', str(node_state['1']['curr_row']), str(node_state['2']['curr_col']) ]
                    new_msg = ''.join(new_buf) 
                    queue0.put(new_msg)
                    queue2.put(new_msg)
                if ((node_state['2']['curr_row'] == node_state['2']['next_row']) and (node_state['2']['curr_col'] == node_state['2']['next_col'])):
                    new_buf = [ 'A', str(node_state['1']['curr_row']), str(node_state['2']['curr_col']) ]
                    new_msg = ''.join(new_buf) 
                    queue0.put(new_msg)
                    queue1.put(new_msg)
                
                if ((node_state['0']['next_row'] == node_state['1']['next_row']) and (node_state['0']['next_col'] == node_state['1']['next_col'])):
                    queue0.put('STOPR')
                    queue1.put('STOP')
                if ((node_state['0']['next_row'] == node_state['2']['next_row']) and (node_state['0']['next_col'] == node_state['2']['next_col'])):
                    queue0.put('STOPR')
                    queue2.put('STOP')
                if ((node_state['1']['next_row'] == node_state['2']['next_row']) and (node_state['1']['next_col'] == node_state['2']['next_col'])):
                    queue2.put('STOP')                    
                    queue1.put('STOPR')
                
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
