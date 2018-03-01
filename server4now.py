from urllib2 import urlopen
import threading, socket, hashspeed, time, Queue, struct, random, sys

TCP_PORT= 8089
SELF_IP = "127.0.0.1"
try:
	if sys.argv[1] == "public":
		SELF_IP = urlopen('http://ip.42.pl/raw').read()
	elif sys.argv[1] == "local":
		pass
	else:
		SELF_IP = sys.argv[1]
	TCP_PORT = int(sys.argv[2])
except IndexError:
	pass

sendBuffer = int(time.time())
periodicalBuffer=int(time.time())

nodes_updated = False #goes True when we find a new node, then turns back off - look in #EVERY 5 MIN
START_NODES = struct.pack(">I", 0xbeefbeef)
START_BLOCKS = struct.pack(">I", 0xdeaddead)

backup=open("backup.bin","r+b")
#socket.setdefaulttimeout(60)
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

SELF_NODE=node(SELF_IP,TCP_PORT,"Lead",int(time.time()))

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

	if msg.cut(4) != START_NODES: 
		raise ValueError("Wrong start_nodes")
	try:
		node_count = struct.unpack(">I",msg.cut(4))[0]
		for x in xrange(node_count):
			name_len=struct.unpack("B",msg.cut(1))[0]
			name 	=msg.cut(name_len)
			host_len=struct.unpack("B",msg.cut(1))[0]
			host 	=msg.cut(host_len)
			port 	=struct.unpack(">H",msg.cut(2))[0]
			ts 		=struct.unpack(">I",msg.cut(4))[0]
			nodes[(host,port)]=node(host,port,name,ts)
		print "nodes:",nodes
		if msg.cut(4) != START_BLOCKS: 
			raise ValueError("Wrong start_blocks")
		block_count=struct.unpack(">I",msg.cut(4))[0]
		print "block_count:", block_count
		for x in xrange(block_count):
			blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	except IndexError as err:
		print "Message too short, cut error:"
		print err
	return cmd ,nodes, blocks


def createMessage(cmd_i):
	global START_NODES, START_BLOCKS
	
	cmd = struct.pack(">I", cmd_i)

	nodes_count=struct.pack(">I",len(activeNodes)+1)	
	nodes = ''
	for node in activeNodes.itervalues():
		nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	nodes+=struct.pack("B",4) + "Lead" + struct.pack("B",len(SELF_IP)) + SELF_IP + struct.pack(">H",TCP_PORT) + struct.pack(">I", SELF_NODE.ts) #Add our port

	start_blocks= struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now, because
	blocks 		= ''              		   #we don't mine for now	
		
	return cmd + START_NODES + nodes_count + nodes + START_BLOCKS + block_count + blocks


def updateByNodes(nodes):
	global activeNodes, nodes_updated
	for address,node in nodes.iteritems(): #we also need to add a blacklist for 127.0.0.1
		if currentTime - 30*60 < node.ts <= currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if address not in activeNodes.keys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[address] = node
			elif activeNodes[address].ts < node.ts: #elif prevents exceptions here (activeNodes[address] exists - we already have this node)
					activeNodes[address].ts = node.ts #the node was seen earlier than what we have in activeNodes, so we update the ts


_,activeNodes,__=parseMsg(backup.read()) #get nodes from init file (backup.bin)
backup.close()

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', TCP_PORT))


def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print "[inputLoop]: got a message from: " + addr[0] + ":" + str(addr[1])
		try:	
			msg = sock.recv(1<<20) #Mega byte
			if msg == "":
				raise ValueError(addr + "has sent an empty str")
			cmd,nodes,blocks = parseMsg(msg)
			#if cmd!=1: raise ValueError("cmd=1 in input functuon!") | will be handled later with try,except
			updateByNodes(nodes)
			#updateByBlocks(blocks)
			sock.sendall(createMessage(2))
		except socket.timeout as err:
			print '[inputLoop]: socket.timeout:"' + str(err) + '"'
		except socket.error as err:
			print '[InputLoop]: socket.error:"' + str(err) + '"'
		else:
			print "[InputLoop]: reply sent successfuly"
		finally:
			sock.shutdown(2)
			sock.close()


threading.Thread(target = inputLoop).start() 

out_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM) #its the socket that we send every 5 min, to 3 random nodes

while True:

	#DoSomeCoinMining() we'll do that later
	currentTime = int(time.time())
	if currentTime - 5*60 >= periodicalBuffer:
		backup.seek(0) #go to the start of the file
		backup.write(createMessage(1)) #write in the new backup
		backup.truncate() #delete anything left from the previous file
		periodicalBuffer = currentTime
		SELF_NODE.ts = currentTime

	if nodes_updated or currentTime - 2 >= sendBuffer: #Every 5 min, or when activeNodes gets an update:
		sendBuffer = currentTime #resetting the timer
		nodes_updated = False
		print "sending event has started!"

		for address in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addresses
			try:
				out_socket.connect(address)
				out_socket.sendall(createMessage(1))
				print "Sent message to:" + address[0]+str(address[1])
				#out_socket.shutdown(1) #Finished sending, now listening
				msg = sock.recv(1<<20)
				if msg != "": #Can potentialy be changed into (if msg == "": raise something) #we can just add try and except to parseMsg
					cmd,nodes,blocks = parseMsg(msg)
				#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
				updateByNodes(nodes)
				#updateByBlocks(blocks) #we dont do blocks for now
			#except socket.timeout:
			except socket.error as err:
				#YOAV YOUR TURN
			finally:
				out_socket.shutdown(2)
				out_socket.close()
		#DELETE 30 MIN OLD NODES:
		for address in activeNodes.iterkeys():
			if currentTime - activeNodes[address].ts > 30*60: #the node wasnt seen in 30 min:
				print "Deleted: " + str(activeNodes[address]) + " as it wasnt seen in 30 min"
				del activeNodes[address]
   		
   		print "activeNodes: " + str(activeNodes.keys())
	print "main loop ended"
	time.sleep(0.1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
print "main thread ended"