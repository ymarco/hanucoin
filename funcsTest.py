from urllib2 import urlopen
from colorama import Fore,Back,Style,init as initColorama
import threading, socket,hashspeed, hashspeed2, time, struct, random, sys, atexit

initColorama(autoreset=True)


#Exit event for terminating program (call exit() or exit_event.set()):
exit_event = threading.Event()
atexit.register(exit_event.set)
old_exit = exit
exit = exit_event.set

#Default values:
SELF_WALLET = hashspeed2.WalletCode(["Lead"])
SELF_PORT = 8089
SELF_IP = localhost = "127.0.0.1"
BACKUP_FILE_NAME = "backup.bin"
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
	BACKUP_FILE_NAME = sys.argv[3]
	TEAM_NAME = sys.argv[4]
	#TAL_IP=sys.argv[5]
except IndexError:
	pass



periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
nodes_got_updated = False #flag for when a new node is added.
blocks_got_updated = False #flag for when someone (might be us) succeeds in mining.
START_NODES = struct.pack(">I", 0xbeefbeef)  #{Instead of unpacking and comparing to the number everytime we
START_BLOCKS = struct.pack(">I", 0xdeaddead) #{will compare the raw string to the packed number.
DO_BACKUP = BACKUP_FILE_NAME not in ("","nobackup","noBackup","NoBackup","NOBACKUP","none","None")
if DO_BACKUP: backup = open(BACKUP_FILE_NAME,"r+b")
activeNodes={} #saved as: (ip, port):node(host,port,name,ts) 
blockList = [] #saved as binary list of all blocks - [block_bin_0, blocks_bin_1,...]



def strAddress(addressTuple):
	return addressTuple[0]+": "+str(addressTuple[1])
	#takes (ip,port) and returns "ip: port"

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
	def __getitem__(self,index):
		return (self.host,self.port,self.name,self.ts)[index]

SELF_NODE=node(SELF_IP,SELF_PORT,TEAM_NAME,currentTime)

class cutstr(object): #String with a self.cut(bytes) method which works like file.read(bytes).
	def __init__(self,string):
		self.string = string

	#def __repr__(self):
	#	return "cutstr object:"+repr(self.string)

	#def __eq__(self,other):
	#	return other == self.string #works with pure strings and other cutstr objects.

	def __len__(self):
		return len(self.string)
									
	def cut(self,bytes):
		if bytes > len(self.string):
			raise IndexError("String too short for cutting by " + str(bytes) + " bytes.")
		
		piece = self.string[:bytes]
		self.string = self.string[bytes:]
		return piece


def parseMsg(msg):
	if msg == "":
		raise ValueError("[parseMsg]: msg is empty")
	#else:
	msg = cutstr(msg)
	nodes = {}
	blocks =  []
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
		print "    [parseMsg]: block_count:", block_count
		for _ in xrange(block_count):
			blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	except IndexError as err:
		print Fore.RED+ "    [parseMsg]: Message too short, cut error:",err
		blocks = []
	return cmd ,nodes, blocks


def createMsg(cmd,nodes,blocks):

	parsed_cmd = struct.pack(">I", cmd)
	nodes_count = struct.pack(">I",len(nodes))	

	parsed_nodes = ''
	for node in nodes:
		parsed_nodes += struct.pack("B",len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	block_count = struct.pack(">I", len(blocks))
	parsed_blocks = ''
	for block in blocks:
		 parsed_blocks += block     		   	
		
	return parsed_cmd + START_NODES + nodes_count + parsed_nodes + START_BLOCKS + block_count + parsed_blocks


def updateByNodes(nodes_dict):
	global activeNodes, nodes_got_updated
	for addr,node in nodes_dict.iteritems(): 
		if ((currentTime - 30*60) < node.ts <= currentTime) and addr!=(SELF_IP,SELF_PORT) : #If it's not a node from the future or from more than 30 minutes ago, and doesnt have our ip
			if addr not in activeNodes.keys(): #Its a new node, lets add it
				nodes_got_updated = True
				activeNodes[addr] = node	
			elif activeNodes[addr].ts < node.ts: #elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts #the node was seen later than what we have in activeNodes, so we update the ts
					print Fore.GREEN + "[updateByNodes]: updated {}'s ts".format(node[:3])
		else: None
			

def updateByBlocks(block_list_in):
	#returns True if updated blockList, else - False
	global blockList
	#check if (list is longer than ours) and (the lists are connected)
	if (len(blockList) < len(block_list_in)) and (hashspeed2.IsValidBlock(block_list_in[-2],block_list_in[-1])==0):#and hashspeed2.IsValidBlock(blockList[-1], block_list_in[len(blockList)])==0:
		blockList = block_list_in
		return True
	return False



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
			in_msg = ""
			while True:
				data = sock.recv(1<<10)	
				if not data: break
				in_msg += data #MegaByte	
			cmd,nodes,blocks = parseMsg(in_msg)
			#if cmd != 1: raise ValueError("cmd=1 in input function!") | will be handled later with try,except
			updateByNodes(nodes)
			blocks_got_updated = updateByBlocks(blocks)
			out_message = createMsg(2,activeNodes.values()+[SELF_NODE], blockList)
			print "[inputLoop]: sent " + str(sock.send(out_message))+ " bytes."
			out_messages_input.append(out_message)
			#sock.shutdown(2)
		except socket.timeout as err:	print Fore.MAGENTA+'[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(strAddress(addr), err)
		except socket.error as err:		print Fore.RED+'[inputLoop]: socket.error while connected to {}, error: "{}"'.format(strAddress(addr), err) #Select will be added later
		except ValueError as err:		print Fore.MAGENTA+ '[inputLoop]: got an invalid data msg from {}: {}'.format(strAddress(addr),err)
 		else:							print Fore.GREEN+"[inputLoop]: reply sent successfuly to: " + strAddress(addr)
		finally:
			sock.close()
			print Fore.CYAN + 'activeNodes: ', activeNodes.viewkeys()
		time.sleep(0.1)


def miningLoop():
	global blockList, blocks_got_updated
	while True:
		if blockList: #blockList aint empty
			print Fore.CYAN + "[miningLoop]: Mining in progress"
			for i in xrange(1<<16): #tries 2^16 attemps every cycle, 2^16 possible cycles. (2^16 attemps)*(2^16 possible cycles) = 2^32 total possible attemps, as needed.
				start_num = i*(1<<16)
				new_block= hashspeed2.MineCoinAttempts(SELF_WALLET, blockList[-1],start_num,1<<16) 
				if blocks_got_updated or new_block!=None: break #start all over again, its a new blocks

			if blocks_got_updated == True: print Fore.YELLOW + "[miningLoop]: someone else succeeded mining, trying again on the new block"
			elif new_block != None: 
				print Fore.GREEN + "[miningLoop]: Mining attempt succeeded (!)"
				blockList += new_block
				break
				blocks_got_updated = True
			else: print Fore.RED + "[miningLoop]: WTF! no succes after 2^32 tries... there's a big problem here..." #the for loop finished without breaking ?!
				
		else:
			print Fore.YELLOW + "[miningLoop]: blockList is empty"
			time.sleep(20) #wait, maybe blockList will get updated.
		time.sleep(0.1)


#>*****DEBUG*******
def addNode(ip,port,name,ts):
	global activeNodes
	activeNodes.update({(ip,port):node(ip,port,name,ts)})

def debugLoop(): #4th (!) thread for printing wanted variables.
	global sendBuffer,periodicalBuffer,activeNodes,blockList,currentTime
	while True:
		try:
			inpt = raw_input(">")
			if inpt == "exit": exit()
			else: exec inpt
		except Exception as err: print err


backup = open(BACKUP_FILE_NAME,"r+b")
backupMSG = backup.read()


BACKUP_CMD, BACKUP_NODES, BACKUP_BLOCKS=parseMsg(backupMSG) #get nodes from backup file
updateByNodes(BACKUP_NODES)
updateByBlocks(BACKUP_BLOCKS)

#block_bin without *
print hashspeed.IsValidBlock(blockList[-2],blockList[-1])
print "mining:"
new_block = hashspeed.MineCoin(SELF_WALLET, blockList[-1])
print new_block
print type(new_block)
print type(blockList[-1])
print len(new_block)
print len(blockList[-1])
print hashspeed.IsValidBlock(blockList[-1],new_block)
time.sleep(10)			
