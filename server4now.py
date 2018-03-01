<<<<<<< HEAD
from urllib2 import urlopen
from colorama import Fore,Back,Style
from colorama import init as initColorama
import threading, socket, hashspeed, time, Queue, struct, random, sys

initColorama(autoreset=True)

TCP_PORT= 8089
SELF_IP = "127.0.0.1"
BACKUP_FILE_NAME="backup.bin"
try:
	if sys.argv[1] == "public":
		SELF_IP = urlopen('http://ip.42.pl/raw').read()
	elif sys.argv[1] == "local":
		pass
	else:
		SELF_IP = sys.argv[1]
	TCP_PORT = int(sys.argv[2])
	BACKUP_FILE_NAME=sys.argv[3]
except IndexError:
	pass

periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
nodes_updated = False #goes True when we find a new node, then turns back off - look in #EVERY 5 MIN
START_NODES = struct.pack(">I", 0xbeefbeef)
START_BLOCKS = struct.pack(">I", 0xdeaddead)

backup=open(BACKUP_FILE_NAME,"r+b")
#socket.setdefaulttimeout(60)
#teamname = hashspeed.somethingWallet(lead)
#local ip = ''
def strAddress(addressTuple):
	return addressTuple[0]+":"+str(addressTuple[1])
	#takes (ip,port) and returns "ip:port"
class node:
	def __init__(self,host,port,name,ts):
		self.host = host
		self.port = port
		self.name = name
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
	try:
		cmd = struct.unpack(">I",msg.cut(4))[0]
		if msg.cut(4) != START_NODES: 
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

	nodes+=struct.pack("B",4) + "Lead" + struct.pack("B",len(SELF_IP)) + SELF_IP + struct.pack(">H",TCP_PORT) + struct.pack(">I", SELF_NODE.ts) #Add our node

	start_blocks= struct.pack(">I", 0xdeaddead)
	block_count = struct.pack(">I", 0) # 0 for now, because
	blocks 		= ''              		   #we don't mine for now	
		
	return cmd + START_NODES + nodes_count + nodes + START_BLOCKS + block_count + blocks


def updateByNodes(nodes):
	global activeNodes, nodes_updated
	for addr,node in nodes.iteritems(): #we also need to add a blacklist for 127.0.0.1
		if currentTime - 30*60 < node.ts <= currentTime: #If it's not a message from the future or from more than 30 minutes ago
			if addr not in activeNodes.keys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[addr] = node
			elif activeNodes[addr].ts < node.ts: #elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts #the node was seen earlier than what we have in activeNodes, so we update the ts


_,activeNodes,__=parseMsg(backup.read()) #get nodes from init file (backup.bin)

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', TCP_PORT))


def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print Fore.GREEN+"[inputLoop]: got a connection from: " + strAddress(addr)
		try:	
			msg = sock.recv(1<<20) #Mega Byte
			if msg != "":
				cmd,nodes,blocks = parseMsg(msg)
			else:
				print Fore.MAGENTA+'[inputLoop]: got an empty message from: '+  strAddress(addr)
			#if cmd!=1: raise ValueError("cmd=1 in input functuon!") | will be handled later with try,except
				updateByNodes(nodes)
			#updateByBlocks(blocks)
				sock.sendall(createMessage(2))
				sock.shutdown(2)
		except socket.timeout as err:
			print Fore.MAGENTA+'[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(addr, err)
		except socket.error as err:
			print Fore.RED+'[inputLoop]: socket.error while connected to {}, error: "{}"'.format(addr, err) #Select will be added later
		else:
			print Fore.GREEN+"[InputLoop]: reply sent successfuly"
		finally:
			sock.close()


threading.Thread(target = inputLoop).start() 

while True:

	#DoSomeCoinMining() we'll do that later
	currentTime = int(time.time())
	if currentTime - 5*60 >= periodicalBuffer:
		print "file writing even has started."
		backup.seek(0) #go to the start of the file
		backup.write(createMessage(1)) #write in the new backup
		backup.truncate() #delete anything left from the previous file
		backup.flush()
		periodicalBuffer = currentTime
		SELF_NODE.ts = currentTime

	if nodes_updated or currentTime - 5*60 >= sendBuffer: 		#Every 5 min, or when activeNodes gets an update:
		sendBuffer = currentTime #resetting the timer
		nodes_updated = False
		print "sending event has started!"

		for addr in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addres
			out_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			try:
				out_socket.connect(addr)
				out_socket.sendall(createMessage(1))
				#out_socket.shutdown(1) Finished sending, now listening
				msg = out_socket.recv(1<<20) #Mega Byte
				out_socket.shutdown(2)
				if msg != "": #Can potentialy be changed into (if msg == "": raise something) #we can just add try and except to parseMsg
					cmd,nodes,blocks = parseMsg(msg)
					#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
					updateByNodes(nodes)
					#updateByBlocks(blocks) #we dont do blocks for now
				else:
					print "[outputLoop]: got an empty msg from: " + strAdress(addr)
			except socket.timeout as err:
				print Fore.MAGENTA+'[outputLoop]: socket.timeout: while sending to {}, error: "{}"'.format(strAddress(addr), str(err))
			except socket.error as err:
				print Fore.RED+'[outputLoop]: socket.error while sending to {}, error: "{}"'.format(strAddress(addr), str(err))
			else:
				print Fore.GREEN+"[outputLoop]: Sent a message to: " + str(addr)
			finally:
				out_socket.close()
		#DELETE 30 MIN OLD NODES:
		for addr in activeNodes.keys(): #keys rather than iterkeys is important because we are deleting keys from the dictionary.
			if currentTime - activeNodes[addr].ts > 30*60: #the node wasnt seen in 30 min:
				print "Deleted: " + strAddress(addr) + "'s node as it wasn't seen in 30 min"
				del activeNodes[addr]
   		
   		print "activeNodes: " + str(activeNodes.keys())
	time.sleep(1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
=======
from urllib2 import urlopen
import threading, socket, hashspeed, time, Queue, struct, random, sys

TCP_PORT= 8089
SELF_IP = "127.0.0.1"
BACKUP_FILE_NAME="backup.bin"
try:
	if sys.argv[1] == "public":
		SELF_IP = urlopen('http://ip.42.pl/raw').read()
	elif sys.argv[1] == "local":
		pass
	else:
		SELF_IP = sys.argv[1]
	TCP_PORT = int(sys.argv[2])
	BACKUP_FILE_NAME=sys.argv[3]
except IndexError:
	pass

periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
nodes_updated = False #goes True when we find a new node, then turns back off - look in #EVERY 5 MIN
START_NODES = struct.pack(">I", 0xbeefbeef)
START_BLOCKS = struct.pack(">I", 0xdeaddead)

backup=open(BACKUP_FILE_NAME,"r+b")
#socket.setdefaulttimeout(60)
#teamname = hashspeed.somethingWallet(lead)
#local ip = ''

class node:
	def __init__(self,host,port,name,ts):
		self.host = host
		self.port = port
		self.name = name
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

	nodes+=struct.pack("B",4) + "Lead" + struct.pack("B",len(SELF_IP)) + SELF_IP + struct.pack(">H",TCP_PORT) + struct.pack(">I", SELF_NODE.ts) #Add our node

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

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', TCP_PORT))


def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print "[inputLoop]: got a message from: " + addr[0] + ":" + str(addr[1])
		try:	
			msg = sock.recv(1<<20) #Mega Byte
			if msg != "":
				cmd,nodes,blocks = parseMsg(msg)
			#if cmd!=1: raise ValueError("cmd=1 in input functuon!") | will be handled later with try,except
				updateByNodes(nodes)
			#updateByBlocks(blocks)
				sock.sendall(createMessage(2))
				sock.shutdown(2)
		except socket.timeout as err:
			print '[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(addr, err)
		except socket.error as err:
			print '[inputLoop]: socket.error while connected to {}, error: "{}"'.format(addr, err) #Select will be added later
		else:
			print "[InputLoop]: reply sent successfuly"
		finally:
			sock.close()


threading.Thread(target = inputLoop).start() 

while True:

	#DoSomeCoinMining() we'll do that later
	currentTime = int(time.time())
	if currentTime - 5*60 >= periodicalBuffer:
		print "file writing even has started@"
		backup.seek(0) #go to the start of the file
		backup.write(createMessage(1)) #write in the new backup
		backup.truncate() #delete anything left from the previous file
		backup.flush()
		periodicalBuffer = currentTime
		SELF_NODE.ts = currentTime

	if nodes_updated or currentTime - 5*60 >= sendBuffer: 		#Every 5 min, or when activeNodes gets an update:
		sendBuffer = currentTime #resetting the timer
		nodes_updated = False
		print "sending event has started!"

		for address in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addresses
			out_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
			try:
				out_socket.connect(address)
				out_socket.sendall(createMessage(1))
				print "[5 min message sends]: Sent a message to: " + str(address)
				#out_socket.shutdown(1) Finished sending, now listening
				msg = out_socket.recv(1<<20) #Mega Byte
				out_socket.shutdown(2)
				if msg != "": #Can potentialy be changed into (if msg == "": raise something) #we can just add try and except to parseMsg
					cmd,nodes,blocks = parseMsg(msg)
					#if cmd!=2: raise ValueError("cmd=2 in output function!") | will be handled later with try,except
					updateByNodes(nodes)
					#updateByBlocks(blocks) #we dont do blocks for now
			except socket.timeout as err:
				print '[5 min message sends]: socket.timeout: while sending to {}, error: "{}"'.format(address[0]+":"+str(address[1]), str(err))
			except socket.error as err:
				print '[5 min message sends]: socket.error while sending to {}, error: "{}"'.format(address[0]+":"+str(address[1]), str(err))
			finally:
				out_socket.close()
		#DELETE 30 MIN OLD NODES:
		for address in activeNodes.keys(): #keys rather than iterkeys is important because we are deleting keys from the dictionary.
			if currentTime - activeNodes[address].ts > 30*60: #the node wasnt seen in 30 min:
				print "Deleted: " + address[0]+":"+str(address[1]) + "'s node as it wasn't seen in 30 min"
				del activeNodes[address]
   		
   		print "activeNodes: " + str(activeNodes.keys())
	time.sleep(1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
print "main program ended"