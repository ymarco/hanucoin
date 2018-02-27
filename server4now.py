import threading
import Queue
import socket
import hashspeed
import time

activeNodes = [] #its a LIST

class node:
	def __init__(self,host,name,port,ts):
		self.host=host
		self.name=name
		self.port=port
		self.ts=ts
	def __eq__(self,other)
	 return self.__dict__==other.__dict__

class socdict:
	def __init__(self,soc):

		self.cmd = struct.unpack(">I",soc.read(4))
		start_nodes = struct.unpack(">I",soc.read(4))
		node_count = struct.unpack(">I",soc.read(4))
		self.nodes = [] #changed that into a LIST
		for x in xrange(node_count):
			name_len = struct.unpack("B",soc.read(1))
			name = soc.read(name_len)
			host_len = struct.unpack("B",soc.read(1))
			host = soc.read(host_len)
			port = struct.unpack(">H",soc.read(2))
			last_seen_ts = struct.unpack(">I",soc.read(4))
			self.nodes.append(node(host,name,port,last_seen_ts))

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
	#thingy = socdict(soc)
	#print(thingy.cmd) >> 1 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1),...}

def handleSocNodes(sock)
	soc = socdict(sock)
	for node in soc.nodes:
		if (node already exists in activeNodes) and (node.ts is bigger than (node.ts that has the same node)) :
			#update node.last_seen_ts
		#else:
			activeNodes.append(node)
	if soc.cmd is 1:
		#send respond messege with cmd=2
		
		
	

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

   #handldeSocNodes(soc)
   #DoSomeCoinMining()
   
   #once per 5 minutes:
   
   #for node in activeNodes:
   	#if int(time.time()) - node.last_seen_ts >= 60*30:
		#del activeNodes[node]
   time.sleep(0.1)  # we dont want the laptop to hang.
