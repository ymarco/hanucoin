import threading
import Queue
import socket
import hashspeed
import time, datetime

activeNodes = {}

class socdict:
	def __init__(self,soc):

		self.cmd = struct.unpack(">I",soc.read(4))
		start_nodes = struct.unpack(">I",soc.read(4))
		node_count = struct.unpack(">I",soc.read(4))
		self.nodes = {}
		for x in xrange(node_count):
			name_len = struct.unpack("B",soc.read(1))
			name = soc.read(name_len)
			host_len = struct.unpack("B",soc.read(1))
			host = soc.read(host_len)
			port = struct.unpack(">H",soc.read(2))
			last_seen_ts = struct.unpack(">I",soc.read(4))
			self.nodes[host] = (name,port,last_seen_ts)

		start_blocks = struct.unpack(">I",soc.read(4))
		block_count = struct.unpack(">I",soc.read(4))
		self.blocks={}
		for x in xrange(block_count):
			serial_number = struct.unpack(">I",soc.read(4))
			wallet = struct.unpack(">I",soc.read(4))
			prev_sig = soc.read(8)
			puzzle = soc.read(4)
			sig = soc.read(12)
			self.blocks[serial_number] = (wallet,prev_sig,puzzle,sig)
	#Example:
	#thingy=socdict(soc)
	#print(thingy.cmd) >> 45 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1),...}

#listen_socket is global
TCP_IP = '127.0.0.1'
TCP_PORT = 5005
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))
listen_socket.listen(1)
g_queue = Queue.Queue()

def AcceptLoop():
   global g_queue
   while True:
       soc, addr = listen_socket.accept()  # synchronous, blocking
       g_queue.put(soc)


threading.Thread(target=AcceptLoop).start()



while True:
   # soc is a new accepted socket
   try:
       soc = g_queue.get()
       sockets.append(soc)  # add to list
   except Queue.Empty:
       soc = None

   #HandleAllSockets()  # handle sockets[i]
   #DoSomeCoinMining()
   time.sleep(0.1)  # if you don't want the laptop to hang.
