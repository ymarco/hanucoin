import threading,socket,hashspeed,time,Queue

activeNodes = {} #its a dict
timeBuffer = int(time.time()) # it gets updated to current time every 5 min

class node:
	def __init__(self,host,name,port,ts):
		self.host=host
		self.name=name
		self.port=port
		self.ts=ts
	def __eq__(self,other):
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
			self.nodes[(host,port)]=node(host,name,port,last_seen_ts) #If two nodes have the same host and port one of them is unnecessary

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
	start_nodes = struct.pack(">I", 0xbeefbeef)
	nodes_count = struct.pack(">I", len(activeNodes))

	nodes = ''
	for node in activeNodes.itervalues() 	#preparing NODES
		nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)
		
	start_blocks = struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now
	blocks = ''              #we dont mine for now	
		
	return cmd + start_nodes + nodes_count + nodes + start_blocks + block count + blocks

def updateBySock(sock):
	global activeNodes,nodes_updated
	soc = socdict(sock)
	for adress,nod in soc.nodes.iteritems():
		if currentTime-1800<nod.ts<=currentTime #If it's not a message from the future or from more than 30 minutes ago
			if adress not in activeNodes.iterkeys():
				nodes_updated=True
				activeNodes[adress]=nod
			elif activeNodes[adress].ts<nod.ts<int(time.time()):
				activeNodes[adress].ts=nod.ts

#listen_socket is global
TCP_IP = '127.0.0.1'
TCP_PORT = 8089
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))
listen_socket.listen(1)
g_queue = Queue.Queue()

def inputLoop():
   while True:
       sock, addr = listen_socket.accept()  # synchronous, blocking
       updateBySock(sock)
       sock.send(createMessage(2))
       sock.close()



threading.Thread(target=inputLoop).start() 

out_socket = socket.socket(sockt.AF_INET,socket.SOCK_STREAM)
while True:

	#DoSomeCoinMining()
   	currentTime=int(time.time())
	if nodes_updated or currentTime - 5*60 >= timeBuffer: #once every 5 min:
		timeBuffer=currentTime
		nodes_updated=False

		for adress in random.sample(activeNodes.viewkeys(),min(3,len(activeNodes))): #Random 3 adresses
			out_socket.connect(adress)
			out_socket.send(createMessage(1))
			updateBySock(out_socket)

	"""DELETE 30 MIN OLD NODES:
		for adress in activeNodes.iterkeys():
			if currentTime - activeNodes[address][ts] >= 30*60 #the node wasnt seen in 30min:
				del activeNodes[address] #the node is no longer active - so it doesnt belong to activeNodes"""
		
   
	
	time.sleep(0.1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' abillity