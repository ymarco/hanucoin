from urllib2 import urlopen
from json import load
from colorama import Fore,Back,Style,init as initColorama
import threading, socket, hashspeed, time, struct, random, sys, atexit

initColorama(autoreset=True)

#Exit event for terminating program (call exit() or exit_event.set()):
exit_event=threading.Event()
atexit.register(exit_event.set)
old_exit=exit
exit=exit_event.set

#Default values:
SELF_PORT = 8089
SELF_IP = localhost = "127.0.0.1"
BACKUP_FILE_NAME="backup.bin"
currentTime = int(time.time())
TEAM_NAME="Lead"
TAL_IP="34.244.16.40"
#try to get ip and port from user input:
try:
	if sys.argv[1] == "public":
		SELF_IP = urlopen('http://ip.42.pl/raw').read() #Get public ip
	elif sys.argv[1] == "local":
		pass
	else:
		SELF_IP = sys.argv[1]
	SELF_PORT = int(sys.argv[2])
	BACKUP_FILE_NAME=sys.argv[3]
	TEAM_NAME=sys.argv[4]
	TAL_IP=sys.argv[5]
except IndexError:
	pass
periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
nodes_updated = False #flag for when a new node is added.
START_NODES = struct.pack(">I", 0xbeefbeef)  #{Instead of unpacking and comparing to the number everytime we
START_BLOCKS = struct.pack(">I", 0xdeaddead) #{will compare the raw string to the packed number.
DO_BACKUP = BACKUP_FILE_NAME not in ("","nobackup","noBackup","NoBackup","NOBACKUP","none","None")
if DO_BACKUP:
	backup=open(BACKUP_FILE_NAME,"r+b")
activeNodes={}
#teamname = hashspeed.somethingWallet(lead)
#local ip = ''

def strAddress(addressTuple):
	return addressTuple[0]+": "+str(addressTuple[1])
	#takes (ip,port) and returns "ip:port"

class node(object):
	def __init__(self,host,port,name,ts):
		self.host = host
		self.port = port
		self.name = name
		self.ts = ts
	def __eq__(self,other):
		return self.__dict__ == other.__dict__

	def __repr__(self):
		return repr(self.__dict__)

SELF_NODE=node(SELF_IP,SELF_PORT,TEAM_NAME,currentTime)

class cutstr(object): #String with a self.cut(bytes) method which works like file.read(bytes).
	def __init__(self,string):
		self.string=string

	#def __repr__(self):
	#	return "cutstr object:"+repr(self.string)

	#def __eq__(self,other):
	#	return other==self.string #works with pure strings and other cutstr objects.

	def __len__(self):
		return len(self.string)
									
	def cut(self,bytes):
		if bytes>len(self):
			raise IndexError("String too short for cutting by " + str(bytes) + " bytes.")
		
		piece=self.string[:bytes]
		self.string=self.string[bytes:]
		return piece

	def safecut(self,bytes):
		if bytes>len(self):
			bytes = len(self)
		
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
		node_count 	= struct.unpack(">I",msg.cut(4))[0]
		for x in xrange(node_count):
			name_len=struct.unpack("B",msg.cut(1))[0]
			name 	=msg.cut(name_len)
			host_len=struct.unpack("B",msg.cut(1))[0]
			host 	=msg.cut(host_len)
			port 	=struct.unpack(">H",msg.cut(2))[0]
			ts 		=struct.unpack(">I",msg.cut(4))[0]
			nodes[(host,port)]=node(host,port,name,ts)
		if msg.cut(4) != START_BLOCKS: 
			raise ValueError("Wrong start_blocks")
		block_count=struct.unpack(">I",msg.cut(4))[0]
		print "block_count:", block_count
		for x in xrange(block_count):
			blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	except IndexError as err:
		print Fore.RED+"Message too short, cut error:",err
		print "(at node/block number {})".format(x)
		#blocks=[]
	return cmd ,nodes, blocks


def createMsg(cmd,nodes_list,blocks):

	parsed_cmd = struct.pack(">I", cmd)
	nodes_count=struct.pack(">I",len(nodes_list))	
	parsed_nodes = ''
	for node in nodes_list:
		parsed_nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	block_count = struct.pack(">I", 0) # 0 for now, because
	parsed_blocks = ''              		   #we don't mine for now	
		
	return parsed_cmd + START_NODES + nodes_count + parsed_nodes + START_BLOCKS + block_count + parsed_blocks


def updateByNodes(nodes_dict):
	global activeNodes, nodes_updated
	for addr,node in nodes_dict.iteritems(): 
		if ((currentTime - 30*60) < node.ts <= currentTime) and localhost!=addr!=(SELF_IP,SELF_PORT) : #If it's not a message from the future or from more than 30 minutes ago	
			print "updated activeNodes:",activeNodes.keys()
			if addr not in activeNodes.keys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[addr] = node
			elif (activeNodes[addr].ts < node.ts): #elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts #the node was seen later than what we have in activeNodes, so we update the ts
			else: print "updateByNodes: didn't accept a new node of " + strAddress(addr) + " because it's timestamp was lower than ours"
		else:
			print "updateByNodes: didn't accept a node " + strAddress(addr) + " due to an invalid timestamp/address"
if DO_BACKUP:
	backupMSG=backup.read()
	if backupMSG:
		_,BACKUP_NODES,__=parseMsg(backupMSG) #get nodes from backup file
		updateByNodes(BACKUP_NODES)

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', SELF_PORT))

socket.setdefaulttimeout(30) #All sockets except listen_socket need timeout. may be too short
out_messages_input=[]
def inputLoop():
	global out_messages_input
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print Fore.GREEN+"[inputLoop]: got a connection from: " + strAddress(addr)
		try:
			in_msg=""
			while True:
				dat=sock.recv(1<<10)	
				if not dat: break
				in_msg += dat #MegaByte
			if in_msg == "":
				print Fore.MAGENTA+'[inputLoop]: got an empty message from: '+  strAddress(addr)
			else:
				cmd,nodes,blocks = parseMsg(in_msg)
			#if cmd!=1: raise ValueError("cmd=1 in input function!") | will be handled later with try,except
				updateByNodes(nodes)
			#updateByBlocks(blocks)
			out_message=cutstr(createMsg(2,activeNodes.values()+[SELF_NODE,node("we finally sent a proper response!",1234,"LEAD_RESPONSE",int(time.time()))],[]))
			total_sent_bytes = 0
			while len(out_message) > 0:
				total_sent_bytes += sock.send(out_message.safecut(1<<10))

			print Fore.GREEN + "sent %d total bytes to %s" % (total_sent_bytes, strAddress(addr))
			out_messages_input.append(out_message)
				#sock.shutdown(2)
		except socket.timeout as err:
			print Fore.MAGENTA+'[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(strAddress(addr), err)
		except socket.error as err:
			print Fore.RED+'[inputLoop]: socket.error while connected to {}, error: "{}"'.format(strAddress(addr), err) #Select will be added later
		except ValueError as err:
			print Fore.MAGENTA+ '[inputLoop]: got an invalid data msg from {}: {}'.format(strAddress(addr),err)
 		else:
			print Fore.GREEN+"[inputLoop]: reply sent successfuly to: " + strAddress(addr)
		finally:
			sock.close()

			print Fore.CYAN + 'activeNodes: ', activeNodes.keys()
#>*****DEBUG*******
def addNode(ip,port,name,ts):
	global activeNodes
	activeNodes.update({(ip,port):node(ip,port,name,ts)})

def debugLoop(): #3rd thread for printing wanted variables.
	global sendBuffer,periodicalBuffer,activeNodes,currentTime
	while True:
		try:
			inpt=raw_input(">")
			if inpt=="exit": exit()
			else: exec inpt

		except Exception as err:
			print err

