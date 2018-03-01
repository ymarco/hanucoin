import threading, socket, hashspeed, time, Queue, struct, random, sys

TCP_IP = ''
try:
	TCP_PORT = int(sys.argv[1])
except IndexError:
	TCP_PORT=8089
	
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

class cutstr:
	def __init__(self,string):
		self.string=string

	def __repr__(self):
		return "cutstr object:"+repr(self.string)

	def __eq__(self,other):
		return other==self.string

	def __len__(self):
		return len(self.string)

	def cut(self,bytes):
		if bytes>len(self):
			raise IndexError("String too short for cutting by " + str(bytes) + " bytes.")
		
		piece=self.string[:bytes]
		self.string=self.string[bytes:]
		return piece


def parseMsg(msg):
	msg=cutstr(msg)
	nodes={}
	blocks=[]
	cmd = struct.unpack(">I",msg.cut(4))[0]

	if msg.cut(4) != START_NODES: #start_nodes!=0xbeefbeef
		raise ValueError("Wrong start_nodes")

	node_count = struct.unpack(">I",msg.cut(4))[0]
	for x in xrange(node_count):
		name_len=struct.unpack("B",msg.cut(1))[0]
		name 	=msg.cut(name_len)
		host_len=struct.unpack("B",msg.cut(1))[0]
		host 	=msg.cut(host_len)
		port 	=struct.unpack(">H",msg.cut(2))[0]
		ts 		=struct.unpack(">I",msg.cut(4))[0]
		nodes[(host,port)]=node(host,port,name,ts)

	if msg.cut(4) != START_BLOCKS: #start_blocks!=0xdeaddead
		raise ValueError("Wrong start_blocks")
	block_count=struct.unpack(">I",msg.cut(4))[0]
	print block_count
	for x in xrange(block_count):
		print x
		blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	return cmd ,nodes, blocks


	#Example:
	#thingy = parsedmsg(soc)
	#print(thingy.cmd) >> 1 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1), "hostname2":(teamname2,...)} #was it changed?

def createMessege(cmd_i):
	global START_NODES, START_BLOCKS
	cmd = struct.pack(">I", cmd_i)
	
	nodes = ''
	for node in activeNodes.itervalues():
		nodes += struct.pack(">B",len(node.name)) + node.name + struct.pack(">B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)
		
	start_blocks= struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now, because
	blocks 		= ''              		   #we don't mine for now	
		
	return cmd + START_NODES + nodes_count + nodes + START_BLOCKS + block_count + blocks


def updateByNodes(nodes):
	global activeNodes,nodes_updated
	for address,nod in nodes.iteritems():
		if currentTime - 1800 <nod.ts <=currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if address not in activeNodes.iterkeys():
				nodes_updated = True
				activeNodes[address] = nod
			elif activeNodes[address].ts < nod.ts: #elif prevents exceptions here (activeNodes[address] exists)
				activeNodes[address].ts = nod.ts


def updateByNodes(nodes):
	global activeNodes, nodes_updated
	for address,node in nodes.iteritems(): #we also need to add a blacklist for 127.0.0.1
		if currentTime - 30*60 < node.ts <= currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if address not in activeNodes.keys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[address] = node
			elif activeNodes[address].ts < node.ts: #elif prevents exceptions here (activeNodes[address] exists - we already have this node)
					activeNodes[address].ts = node.ts #the node was seen earlier than what we have in activeNodes, so we update the ts

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))


def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print "[inputLoop]: got a message from: " + addr[0] + ":" + str(addr[1])
		try:	
			msg = sock.recv(1<<20)
			if msg == "":
				raise ValueError(addr + "has sent an empty str")
			cmd,nodes,blocks = parseMsg(msg)
			#if cmd!=1: raise ValueError("cmd=1 in input functuon!") | will be handled later with try,except
			updateByNodes(nodes)
			#updateByBlocks(blocks)
			sock.sendall(createMessage(2))
		#except socket.timeout:
		except socket.error as err:
			print '[InputLoop]: socket.error:"' + str(err) +'"'
		else:
			print "[InputLoop]: replay sent successfuly"
		finally:
			sock.shutdown(2)
			sock.close()


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

			out_socket.sendall(createMessage(1))
			print "Sent message to:" + address[0]+str(address[1])
			#out_socket.shutdown(1) #Finished sending, now listening
			msg = sock.recv(1<<20)
			if msg != "": #Can potentialy be changed into (if msg == "": raise something) #we can just add try and except to parseMsg
				cmd,nodes,blocks = parseMsg(msg)
			#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
			out_socket.shutdown(2)
			out_socket.close()
			#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
			updateByNodes(nodes)
			#updateByBlocks(blocks)

		#DELETE 30 MIN OLD NODES:
		for address in activeNodes.iterkeys():
			if currentTime - activeNodes[address].ts > 30*60: #the node wasnt seen in 30 min:
				del activeNodes[address] #the node is no longer active - so it doesnt belong to activeNodes
		
   		
   		print "activeNodes: " + srt(activeNodes.keys())
	
	time.sleep(0.1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
	