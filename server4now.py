import threading
import Queue
import socket
import hashspeed
import time

activeNodes = {} #its a LIST


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
		self.nodes = {} #changed that into a LIST
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
	nodes_count = 0
	for node in activenodes.itervalues() 	#preparing NODES
		nodes_count += 1
		namelen=0
		for i in node.name: #getting name_len
			namelen += 1
		name_len = struct.pack('B' , namelen)
		hostlen=0
		for i in node.host
			hostlen +=1
		host_len = struct.pack('B', hostlen)
		port = struct.pack(">H", node.port)
		last_seen_ts = struct.pack(">I", node.port)
		nodes = nodes + name_len + node.name + host_len + name.host + port + last_seen_ts
		
	start_blocks = struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now
	blocks = ''              #we dont mine for now	
		
	message = cmd + start_nodes + nodes_count + nodes + start_blocks + block count + blo
	return messege

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
   
   #once per 5 minutes:
   
   #for node in activeNodes:
   	#if int(time.time()) - node.last_seen_ts >= 60*30:
		#del activeNodes[node]
   time.sleep(0.1)  # we dont want the laptop to hang.
