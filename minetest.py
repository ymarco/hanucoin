from urllib2 import urlopen
from colorama import Fore,Back,Style,init as initColorama
import threading, socket, hashspeed, time, struct, random, sys, atexit

initColorama(autoreset=True)


#Exit event for terminating program (call exit() or exit_event.set()):
exit_event=threading.Event()
atexit.register(exit_event.set)
old_exit=exit
exit=exit_event.set

#Default values:
SELF_WALLET = hashspeed.WalletCode(["yoav", "maayan", "itzik"]) #the order doesnt matter, it gets sorted - look at hashspeed.py
SELF_PORT = 8089
SELF_IP = localhost = "127.0.0.1"
BACKUP_FILE_NAME="backup.bin"
currentTime = int(time.time())
TEAM_NAME="Lead"
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
except IndexError:
	pass



periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
sending_trigger = False #flag for when a new node is added.
START_NODES = struct.pack(">I", 0xbeefbeef)  #{Instead of unpacking and comparing to the number everytime we
START_BLOCKS = struct.pack(">I", 0xdeaddead) #{will compare the raw string to the packed number.

backup=open(BACKUP_FILE_NAME,"r+b")
activeNodes={}
blocksList = []


def strAddress(addressTuple):
	return addressTuple[0]+": "+str(addressTuple[1])
	#takes (ip,port) and returns "ip:port"

class node:
	def __init__(self,host,port,name,ts):
		self.host = host
		self.port = port
		self.name = name
		self.ts = ts
	def __eq__(self,other):
		return self.__dict__ == other.__dict__

	def __repr__(self):
		return repr(self.__dict__)

SELF_NODE=node(SELF_IP,SELF_PORT,"Lead",currentTime)

class cutstr: #String with a self.cut(bytes) method which works like file.read(bytes).
	def __init__(self,string):
		self.string=string

	#def __repr__(self):
	#	return "cutstr object:"+repr(self.string)

	#def __eq__(self,other):
	#	return other==self.string #works with pure strings and other cutstr objects.

	def __len__(self):
		return len(self.string)
									
	def cut(self,bytes):
		if bytes>len(self.string):
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
		node_count 	= struct.unpack(">I",msg.cut(4))[0]
		for _ in xrange(node_count):
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
		print "  [parseMsg]: block_count:", block_count
		for _ in xrange(block_count):
			blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	except IndexError as err:
		print Fore.RED + "  [parseMsg]: Message too short, cut error:", err
		blocks=[]
	return cmd ,nodes, blocks


def createMsg(cmd,nodes_list,blocks):

	parsed_cmd = struct.pack(">I", cmd)
	nodes_count=struct.pack(">I",len(nodes_list))	
	parsed_nodes = ''
	for node in nodes_list:
		parsed_nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	block_count = struct.pack(">I", len(blocks))
	parsed_blocks = ''
	for block in blocks:
		 parsed_blocks += block     		   	
		
	return parsed_cmd + START_NODES + nodes_count + parsed_nodes + START_BLOCKS + block_count + parsed_blocks


def updateByNodes(nodes_dict):
	global activeNodes, sending_trigger
	for addr,node in nodes_dict.iteritems(): 
		if ((currentTime - 30*60) < node.ts <= currentTime) and localhost!=addr!=(SELF_IP,SELF_PORT) : #If it's not a message from the future or from more than 30 minutes ago	
			if addr not in activeNodes.keys(): #Its a new node, lets add it
				sending_trigger = True
				activeNodes[addr] = node
			elif (activeNodes[addr].ts < node.ts): #elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts #the node was seen later than what we have in activeNodes, so we update the ts

def updateByBlocks(block_list_in):
	#returns True if updated blocksList, else - False
	global blocksList
	#check if (list is more updated than ours) and (the lists are connected)
	if (len(blocksList) < len(block_list_in)) and (hashspeed.IsValidBlock(block_list_in[-2],block_list_in[-1]) is 0): #and (hashspeed.IsValidBlock(blocksList[-1], block_list_in[len(blocksList)]) is 0):
		blocksList = block_list_in
		return True
	return False
	
	
	
backupCmd, backupNodes, backupBlocks=parseMsg(backup.read()) #get nodes from backup file
updateByNodes(backupNodes)
updateByBlocks(backupBlocks)

print Fore.GREEN + "mining"
hashspeed.MineCoin(SELF_WALLET, blocksList[-1])
print Fore.GREEN + "finished"
time.sleep(20)



