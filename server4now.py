import threading, socket, hashspeed, time, Queue, struct, random, sys

activeNodes = {} #its a dict
timeBuffer = int(time.time()) # it gets updated to current time every 5 min
nodes_updated = False #goes True when we find a new node, then turns back off - look in #EVERY 5 MIN
START_NODES = struct.pack(">I", 0xbeefbeef)
START_BLOCKS = struct.pack(">I", 0xdeaddead)
#teamname = hashspeed.somethingWallet(lead)
#local ip = ''

class node:
	def __init__(self,host,port,name,ts):
		self.host = host
		self.name = name
		self.port = port
		self.ts = ts
	def __eq__(self,other):
		return self.__dict__ == other.__dict__

def parseSocket(soc):
	nodes = {} #dict
	blocks = []
	cmd = struct.unpack(">I", soc.recv(4))[0] #raises the EXCEPTION: "unpack requires a string argument of length 4' WHY??
	if soc.recv(4) != "\xbe\xef\xbe\xef":#start_nodes != 0xbeefbeef:
		raise Exception("parseSocket.start_nodes_isnt_'0xbeefbeef'")
	node_count = struct.unpack(">I",soc.recv(4))[0] 
	for x in xrange(node_count):
		name_len= struct.unpack(">B",soc.recv(1))[0]
		name 	= soc.recv(name_len)
		host_len= struct.unpack(">B",soc.recv(1))[0]
		host 	= soc.recv(host_len)
		port 	= struct.unpack(">H", soc.recv(2))[0] #added the unpack ~Marco
		ts 		= struct.unpack(">I", soc.recv(4))[0] #added the unpack ~Marco
		nodes[(host,port)] = (name,ts)
	if soc.recv(4) != "\xde\xad\xde\xad": #start_blocks!= 0xdeaddead
		raise Exception("parseSocket.start_blocks_isnt_'0xdeaddead'")
	block_count = struct.unpack(">I",soc.recv(4))[0]
	for x in xrange(block_count):
		blocks.append(soc.recv(32))
	soc.close()
	#Parse(blocks)
	#Parse(nodes):
	for address,tup in nodes:
		nodes[address]=node(*(address+(tup[0],)+struct.unpack(">I",tup[1])))

	return cmd, nodes, blocks

class parsedmsg:
	def __init__(self, cmd, nodes, blocks):
		self.cmd = cmd
		self.nodes = nodes
		self.blocks = blocks

	#Example:
	#thingy = parsedmsg(soc)
	#print(thingy.cmd) >> 1 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1), "hostname2":(teamname2,...)} #was it changed?

def createMessege(cmd_i):
	global START_NODES, START_BLOCKS
	cmd = struct.pack(">I", cmd_i)
	
	nodes = ''
	for node in activeNodes.itervalues():
		nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)
		
	start_blocks = struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now, because
	blocks = ''              		   #we don't mine for now	
		
	return cmd + START_NODES + nodes_count + nodes + START_BLOCKS + block_count + blocks

def updateBySock(sock):
	global activeNodes, nodes_updated
	data = parsedmsg(parseSocket(sock))
	for address, node in data.nodes.iteritems(): #we also need to add a blacklist for 127.0.0.1
		if currentTime - 30*60 < node.ts <= currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if address not in activeNodes.iterkeys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[address] = node
			elif activeNodes[address].ts < node.ts: #elif prevents exceptions here (activeNodes[adress] exists - we already have this node)
					activeNodes[address].ts = node.ts #the node was seen earlier than what we have in activeNodes, so we update the ts

#listen_socket is global
TCP_IP = ''
TCP_PORT = 8089
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))
listen_socket.listen(1)


def inputLoop():
	while True:
		sock, addr = listen_socket.accept() #blocking
		#we need to do something with recv here, dont we?
		
		
		try:
			updateBySock(sock)
			print "[inputLoop]: got a message from: " +  str(addr)
			sock.sendall(createMessage(2)) #blocking
			print "[inputLoop]: reply sent succesfully"

		except Exception as expt:
			print "[inputLoop]: got a message from: " + str(addr)
			print '[inputLoop]: Error: "' + str(expt) +'"'

		
		sock.close() #we are done with it anyway



threading.Thread(target = inputLoop).start() 

out_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #its the socket that we send every 5 min, to 3 random nodes
while True:

	#DoSomeCoinMining() we'll do that later
	currentTime = int(time.time())
	
	if nodes_updated or currentTime - 5*60 >= timeBuffer: #Every 5 min, or when activeNodes gets an update:
		timeBuffer = currentTime #resetting the timer
		nodes_updated = False


		for address in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addresses
			out_socket.connect(address)
			out_socket.send(createMessage(1)) #we'll need to create a non-blocking loop for that when messeges get long, *or a new thread*
			print "Sent message to: " + str(address)
			updateBySock(out_socket) #is that the reply message we're supposed to get? 
			out_socket.close()

		#DELETE 30 MIN OLD NODES:
		for address in activeNodes.iterkeys():
			if currentTime - activeNodes[address].ts > 30*60: #the node wasnt seen in 30 min:
				del activeNodes[address] #the node is no longer active - so it doesnt belong to activeNodes
		
   		
   		print "activeNodes: " + srt(activeNodes.keys())
	
	time.sleep(0.1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
	