#!/usr/bin/env python

import socket


TCP_IP = '127.0.0.1'
TCP_PORT = 8089
BUFFER_SIZE = 1024
messTemp = open("backup.bin","rb")
MESSAGE = messTemp.read()


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))
print s.send(MESSAGE)
#the client just gets stuck for 5 min till i closed it! I think '	SENDALL' aint good at all
data = s.recv(BUFFER_SIZE)


print "received data:", data
	
s.close()