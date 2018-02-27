int(time.time())import threading
import Queue
import socket
import hashspeed
import time

activeNodes = {} #its a dict
timeBuffer = int(time.time()) # it gets updated to current time every 5 min

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

		self.cmd = struct.unpack(">I",soc.recv(4))[0]
		start_nodes = struct.unpack(">I",soc.recv(4))[0]
		node_count = struct.unpack(">I",soc.recv(4))[0]

		self.nodes = {} #its a dict
		for x in xrange(node_count):
			name_len = struct.unpack("B",soc.recv(1))[0]
			name = soc.recv(name_len)
			host_len = struct.unpack("B",soc.recv(1))[0]
			host = soc.recv(host_len)
			port = struct.unpack(">H",soc.recv(2))[0]
			last_seen_ts = struct.unpack(">I",soc.recv(4))[0]
			self.nodes[host+port]=node(host,name,port,last_seen_ts) #If two nodes have the same host and port one of them is unnecessary

		start_blocks = struct.unpack(">I",soc.recv(4))[0]
		block_count = struct.unpack(">I",soc.recv(4))[0]
		self.blocks={}
		for x in xrange(block_count):
			serial_number = struct.unpack(">I",soc.recv(4))[0]
			wallet = struct.unpack(">I",soc.recv(4))[0]
			prev_sig = soc.recv(8)
			puzzle = soc.recv(4)
			sig = soc.recv(12)
			self.blocks[serial_number] = (wallet,prev_sig,puzzle,sig)
	#Example:
	#thingy = socdict(soc)
	#print(thingy.cmd) >> 1 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1),...}

def createMessege(cmd_i):
	cmd = struct.pack(">I",cmd_i)
	start_nodes = struct.pack(">I", 0xbeefbeed)
	nodes_count = struct.pack(">I", len(activeNodes))

	nodes = ''
	for node in activeNodes.itervalues() 	#preparing NODES
		nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)
		
	start_blocks = struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now
	blocks = ''              #we dont mine for now	
		
	return cmd + start_nodes + nodes_count + nodes + start_blocks + block count + blocks

def handleSocNodes(sock):
	soc = socdict(sock)
	for adress in soc.nodes.iterkeys():
		if (adress not in activeNodes.iterkeys()) or (activeNodes[adress].ts<soc.nodes[adress].ts<int(time.time())):
			activeNodes[adress]=soc.nodes[adress]
	if soc.cmd is 1:
		#send respond messege with cmd=2
		
		
	

#listen_socket is global
TCP_IP = '127.0.0.1'
TCP_PORT = 8089
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
   
	if int(time.time()) timeBuffer >= 5*60 : #once every 5 min:
		for adress in activeNodes.iterkeys():
			if int(time.time())int(time.time()) - activeNodes[address][ts] >= 30*60 #the node wasnt seen in 30min:
				del activeNodes[address] #the node is no longer active - so it doesnt belong to activeNodes 
		
   
	
time.sleep(0.1)  # we dont want the laptop to hang.
