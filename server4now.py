import threading, socket, hashspeed, time, Queue, struct, sys

TCP_IP = ''
TCP_PORT = int(sys.argv[1])

activeNodes = {} #its a dict
timeBuffer = int(time.time()) # it gets updated to current time every 5 min
nodes_updated = False

class node:
	def __init__(self,host,port,name,ts):
		self.host=host
		self.name=name
		self.port=port
		self.ts=ts
	def __eq__(self,other):
		return self.__dict__==other.__dict__

def cut(string,bytes):
	piece=string[:bytes]
	string=[bytes:]
	return piece

def parseMsg(msg): #Needs to be changed into a string data processing function rather than real time processing one. *maybe
	nodes={}
	blocks=[]
	cmd = struct.unpack(">I",cut(msg,4))[0]
	if cut(msg,4) != "\xbe\xef\xbe\xef" #start_nodes!=0xbeefbeef:
		raise TypeError("Wrong start_nodes")
	node_count = struct.unpack(">I",cut(msg,4))[0]
	for x in xrange(node_count):
		name_len=struct.unpack("B",cut(msg,1))[0]
		name=cut(msg,name_len)
		host_len=struct.unpack("B",cut(msg,1))[0]
		host=cut(msg,host_len)
		port=struct.unpack(">H",cut(msg,2))[0]
		last_seen_ts=struct.unpack(">I",cut(msg,4))[0]
		nodes[(host,port)]=node(host,port,name,last_seen_ts)
	if cut(msg,4) != "\xde\xad\xde\xad": #start_blocks!=0xdeaddead
		raise TypeError("Wrong start_blocks")
	block_count=struct.unpack(">I",cut(msg,4))[0]
	for x in xrange(block_count):
		blocks.append(cut(msg,32)) #NEEDS CHANGES AT THE LATER STEP

	return cmd,nodes,blocks

	#Example:
	#thingy = parsedmsg(soc)
	#print(thingy.cmd) >> 1 (a 4 byte number)
	#print(thingy.nodes) >> {"hostname1":(teamname1,port1,last_seents1), "hostname2":(teamname2,...)} #was it changed?

def createMessege(cmd_i):
	cmd = struct.pack(">I",cmd_i)
	start_nodes = struct.pack(">I", 0xbeefbeef)
	nodes_count = struct.pack(">I", len(activeNodes))

	nodes = ''
	for node in activeNodes.itervalues(): #python has issues with this line for some reason
		nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)
		
	start_blocks = struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now, because
	blocks = ''              		   #we don't mine for now	
		
	return cmd + start_nodes + nodes_count + nodes + start_blocks + block_count + blocks

def updateByNodes(nodes):
	global activeNodes,nodes_updated
	for address,nod in nodes.iteritems():
		if currentTime-1800 <nod.ts <=currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if address not in activeNodes.iterkeys():
				nodes_updated=True
				activeNodes[address]=nod
			elif activeNodes[address].ts<nod.ts: #elif prevents exceptions here (activeNodes[adress] exists)
				activeNodes[address].ts=nod.ts

#listen_socket is global

listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))

def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print "data message from:", addr
		msg=sock.recv(1024)
		cmd,nodes,blocks = parseMsg(msg)
		#if cmd!=1: raise ValueError("cmd=1 in input functuon!") | will be handled later with try,except
		updateByNodes(nodes)
		#updateByBlocks(blocks)
		sock.sendall(createMessage(2))
		sock.shutdown(2)
		sock.close()



threading.Thread(target=inputLoop).start() 

out_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
while True:

	#DoSomeCoinMining()
	currentTime = int(time.time())
	
	if nodes_updated or currentTime - 5*60 >= timeBuffer: #once every 5 min:
		timeBuffer=currentTime
		nodes_updated=False


		for address in random.sample(activeNodes.viewkeys(),min(3,len(activeNodes))): #Random 3 addresses
			out_socket.connect(address)
			out_socket.sendall(createMessage(1))
			out_socket.shutdown(1) #Finished sending, now listening
			msg=sock.recv(1024)
			if msg != "": #Can potentialy be changed into (if msg == "": raise something)
			cmd,nodes,blocks = parseMsg(msg)
			out_socket.shutdown(2)
			out_socket.close()
			#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
			updateByNodes(nodes)
			#updateByBlocks(blocks)

		#DELETE 30 MIN OLD NODES:
		for address in activeNodes.iterkeys():
			if currentTime - activeNodes[address].ts > 30*60: #the node wasnt seen in 30 min:
				del activeNodes[address] #the node is no longer active - so it doesnt belong to activeNodes
		
   
	
	time.sleep(0.1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
	