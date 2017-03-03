import time
import socket

sendport = 50007
recvport = 40006

filename = 'config.txt'

def getconfig():
    configfile = open(filename, "r")
    hostnames = []
    for line in configfile.readlines():
        hostnames.append(line[:-1])
    return hostnames[0]

def connecttomarshall():
    hostname = getconfig()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    while (!connected):
        s.connect((hostname, sendport))
        s.sendall('CHK')
        data = s.recv(1024)
        if data[0] == 'A' and data[1] == 'C' and data[2] == 'K'
            connected = True
        time.sleep(0.1)

def sendmessage(socket, message):
    socket.sendall(message)
