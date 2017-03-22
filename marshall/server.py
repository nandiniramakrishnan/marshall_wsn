import socket
import sys
from threading import Thread
import time
import Queue

server_address = ('localhost', 10000)

class UserInterfaceThread(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        print "Hello from user interface!"
        while True:
            command = raw_input("> ")
            numchars = len(command)
            self.queue.put(command)
            
            # SEND MESSAGE TO NODE

        return

class ClientThread(Thread):
    def __init__(self, client_sock, queue):
        Thread.__init__(self)
        self.client = client_sock
        self.queue = queue

    def run(self):
        received = False
        while not received:
            data = self.client.recv(3)
            if data:
                received = True
                if data[0] == 'C' and data[1] == 'H' and data[2] == 'K':
                    self.client.sendall('ACK')
            else:
                break
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
        print "Server is listening for incoming connections"
        ui_thread = UserInterfaceThread(queue)
        ui_thread.start()
        try:
            while True:
                try:
                    self.sock.settimeout(0.5)
                    client = self.sock.accept()[0]
                except socket.timeout:
                    time.sleep(1)
                    continue
                new_thread = ClientThread(client, queue)
                print 'Incoming connection. Started thread ',
                print new_thread.getName()
                self.thread_list.append(new_thread)
                new_thread.start()

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
