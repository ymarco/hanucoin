#!/usr/bin/env python

import socket


TCP_IP = '127.0.0.1'
TCP_PORT = 8089
BUFFER_SIZE = 1024
messTemp = open("tal_message.bin")
MESSAGE = messTemp.read()


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

s.sendall(MESSAGE) #the client just gets stuck for 5 min till i closed it! I think 'sendall aint good at all'
data = s.recv(BUFFER_SIZE)


print "received data:", data
	
s.close()