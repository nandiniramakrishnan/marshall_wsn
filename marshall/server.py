import socket
import sys
from threading import Thread
import time
import Queue

server_address = ('', 10000)

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
            elif command.lower() == "help":
                print "-\nEnter a node followed by its destination's row and column\nCommand format: <node-index><row><col>\nExample: 012 # Node 0, Row 1, Col 2\n-"
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
                print "this is a proper command"
                self.queue.put(command)
            # SEND MESSAGE TO NODE

        return

class ClientThread(Thread):
    def __init__(self, client_sock, queue):
        Thread.__init__(self)
        self.client = client_sock
        self.queue = queue

    def run(self):

        # Start receiving commands from marshall
        while True:
            if not self.queue.empty():
                command = self.queue.get()
                self.client.sendall(command)
        
        self.client.close()
        return

# Multithreaded TCP Server
class Server:

    def __init__(self):
        self.sock = None
        self.thread_list = []

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
                self.sock.bind(server_address)
                # Socket can handle upto 3 incoming connections (for each node)
                self.sock.listen(3)
                server_up = True
                break
            except:
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
        ui_thread.start()
        try:
            while True:

                # If queue is not empty
                if not queue.empty():
                    print "there are commands in the queue"
                    command = queue.get()
                    if command[0] == '0':
                        queue0.put(command)
                    elif command[0] == '1':
                        queue1.put(command)
                    elif command[0] == '2':
                        queue2.put(command)
                try:
                    self.sock.settimeout(0.5)
                    client = self.sock.accept()[0]
                except socket.timeout:
                    time.sleep(1)
                    continue
                # CHK-ACK portion. Get node number here
#                received = False
                print "accepted socket conn"
                # Receive acknowledgement from marshall
 #               while not received:
                try:
                    data = client.recv(4)
                except socket.error as ex:
                    if str(ex) == "[Errno 35] Resource temporarily unavailable":
                        time.sleep(0.01)
                        continue
                    raise ex
                if data:
                    #received = True
                    print data
                    if data[0:3] == "CHK":
                        print "received chk"
                        if data[3] == '0':
                            new_thread = ClientThread(client, queue0)
                        elif data[3] == '1':
                            new_thread = ClientThread(client, queue1)
                        elif data[3] == '2':
                            new_thread = ClientThread(client, queue2)
                        print "created thread"

                        self.thread_list.append(new_thread)
                        new_thread.start()
                        client.sendall("ACK")
                        print "sent ack"
                    else:
                        print "--- BROKE!!"
                        break

                for thread in self.thread_list:
                    if not thread.isAlive():
                        self.thread_list.remove(thread)
                        thread.join()
        except Exception, err:
            print "Something's wrong. errno = %s" % err

        for thread in self.thread_list:
            thread.join(1.0)

        
        self.sock.close()

if "__main__" == __name__:
    server = Server()
    server.run()
    print "Terminated"
