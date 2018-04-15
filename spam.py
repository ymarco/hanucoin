from urllib2 import urlopen
from colorama import Fore,Back,Style,init as initColorama
import threading, socket, hashspeed2, time, struct, random, sys, atexit

initColorama(autoreset=True)


#Exit event for terminating program (call exit() or exit_event.set()):
exit_event = threading.Event()
atexit.register(exit_event.set)
old_exit = exit
exit = exit_event.set

#Default values:
SELF_WALLET = hashspeed2.WalletCode(["Lead"])
NOONE_WALLET = hashspeed2.WalletCode(["Bob"])
SELF_PORT = 8089
SELF_IP = urlopen('http://ip.42.pl/raw').read() #Get public ip
localhost = '127.0.0.1'
currentTime = int(time.time())
TEAM_NAME="Lead"
TAL_IP="34.244.16.40"
mining_slices = "1/1"
TAL_PORT=8080
TIME_BETWEEN_SENDS = 5*60 #5 min
send_self_node = True
#try to get ip and port from user input:
try:
	SELF_PORT = int(sys.argv[1])
	mining_slices = sys.argv[2] #{we'll write what slice we want to mine in. useful when several copies of this server are running together.
								#{say we want to run 3 servers, we'll run the 1st in '1/3' slice, 2nd in '2/3' slice, 3rd in '3/3' slice
								#{so they try numbers for mining from different xranges. 
	TIME_BETWEEN_SENDS = int(sys.argv[3]) #in secs
	send_self_node = bool(sys.argv[4])
except IndexError: pass

mining_slice_1,mining_slice_2 = mining_slices.split('/')
mining_slice_1 = int(mining_slice_1) #we want these as numbers, not strings
mining_slice_2 = int(mining_slice_2)

MINING_STARTPOINT = ((mining_slice_1 -1)*(1<<16))/mining_slice_2
MINING_STOPPOINT = ((mining_slice_1)*(1<<16))/mining_slice_2


periodicalBuffer = sendBuffer = int(time.time())
#DEBUG: *******************
periodicalBuffer -= (4*60+0.4*60)
sendBuffer -= (4*60+0.6*60)
#************************
nodes_got_updated = False #flag for when a new node is added.
blocks_got_updated = False #flag for when someone (might be us) succeeds in mining.
START_NODES = struct.pack(">I", 0xbeefbeef)  #{Instead of unpacking and comparing to the number everytime we
START_BLOCKS = struct.pack(">I", 0xdeaddead) #{will compare the raw string to the packed number.
backup = open("backup.bin","r+b")
activeNodes={} #saved as: {(ip, port): node(host,port,name,ts)...} 
blocksList = [] #saved as binary list of all blocks - [block_bin_0, blocks_bin_1,...]



def strAddress(addressTuple):
	return addressTuple[0]+": "+str(addressTuple[1])
	#takes (ip,port) and returns "ip: port"

def backupRewrite(msg):
	global backup
	backup.seek(0) #go to the start of the file
	backup.write(msg) #write in the new backup
	backup.truncate() #delete anything left from the previous backup
	backup.flush() #save info.
	print Fore.CYAN + "- File backup is done"

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


if send_self_node: SELF_NODE=node(SELF_IP,SELF_PORT,TEAM_NAME,currentTime)
else: SELF_NODE = []

class CutError(IndexError):
	pass
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
			raise CutError("String too short for cutting by " + str(bytes) + " bytes.")
		
		piece = self.string[:bytes]
		self.string = self.string[bytes:]
		return piece


def parseMsg(msg):
	msg = cutstr(msg)
	nodes = {}
	blocks =  []
	cmd = None
	try:
		cmd = struct.unpack(">I",msg.cut(4))[0]
		if msg.cut(4) != START_NODES: raise ValueError("Wrong start_nodes")
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
		block_count = struct.unpack(">I",msg.cut(4))[0]
		print "    [parseMsg]: block_count:", block_count
		for _ in xrange(block_count):
			blocks.append(msg.cut(32)) #NEEDS CHANGES AT THE LATER STEP
	except CutError as err:
		print Fore.RED + "[parseMsg]: Message too short, cut error:",err
		blocks = [] #we dont want damaged blocks
	return cmd, nodes, blocks


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
		else: None
			

def updateByBlocks(blocks):
	#returns True if updated blocksList, else - False
	global blocksList
	if len(blocksList) <= 2:
		blocksList =blocks
		return True
	#else: check if ((list is longer than ours) and (last block is valid)) and (the lists are connected)
	if (len(blocksList) < len(blocks)): # and (hashspeed2.IsValidBlock(blocks[-2],blocks[-1])==0) and hashspeed2.IsValidBlock(blocksList[-1],blocks[len(blocksList)])==0:
		blocksList = blocks
		return True
	return False



backupMSG = backup.read()
if backupMSG:
	_, BACKUP_NODES, __ = parseMsg(backupMSG) #get nodes from backup file
	updateByNodes(BACKUP_NODES)
	#we dont want to updateByBlocks cause these blocks are probably outdated

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', SELF_PORT))

socket.setdefaulttimeout(5) #All sockets except listen_socket need timeout. may be too short
#listen_socket will run on its own inputLoop thread and as so doesnt need timeout
out_messages_input=[]

def inputLoop():
	global out_messages_input, blocks_got_updated
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print Fore.GREEN+"[inputLoop]: got a connection from: " + strAddress(addr)
		try:
			in_msg = ""
			while True:
				data = sock.recv(1<<10) #MegaByte
				if not data: break
				in_msg += data
			cmd,nodes,blocks = parseMsg(in_msg)
			if cmd != 1: raise ValueError('cmd accepted isnt 1!')
			sock.shutdown(socket.SHUT_RD) #Finished receiving, now sending.
			blocks_got_updated = updateByBlocks(blocks)
			out_message = createMsg(2,activeNodes.values()+[SELF_NODE], blocksList)
			bytes_sent = 0
			while bytes_sent<len(out_message):
				bytes_sent += sock.send(out_message[bytes_sent:])
			print Fore.GREEN + "[inputLoop]: sent %d bytes back to %s" % (bytes_sent,strAddress(addr))
			sock.shutdown(2)
		except socket.timeout as err:	print Fore.MAGENTA	+'[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(strAddress(addr), err)
		except socket.error as err:		print Fore.RED 		+'[inputLoop]: socket.error while connected to {}, error: "{}"'.format(strAddress(addr), err) #Select will be added later
		except ValueError as err:		print Fore.MAGENTA 	+'[inputLoop]: got an invalid data msg from {}: {}'.format(strAddress(addr),err)
 		else:							print Fore.GREEN 	+"[inputLoop]: reply sent successfuly to: " + strAddress(addr)
		finally:						sock.close()


def miningLoop():
	global blocksList, blocks_got_updated
	while True:
		if blocksList: #blocksList aint empty
			if hashspeed2.unpack_block_to_tuple(blocksList[-1])[1] == SELF_WALLET:
				wallet = NOONE_WALLET
				print Fore.CYAN + '[miningLoop]: mining as "no_body". Mining in progress' 
			else: 
				wallet = SELF_WALLET
				print Fore.CYAN + '[miningLoop]: mining as "Lead". Mining in progress' 


			for i in xrange(MINING_STARTPOINT, MINING_STOPPOINT):
				start_num = i*(1<<16)
				new_block= hashspeed2.MineCoinAttempts(wallet, blocksList[-1],start_num,1<<16) 
				if blocks_got_updated or new_block!=None: break #start all over again, we have a new block

			if blocks_got_updated == True: print Fore.YELLOW + "[miningLoop]: someone succeeded mining, trying again on the new block"
			elif new_block != None: 
				print Fore.GREEN + "[miningLoop]: Mining attempt succeeded (!)"
				print new_block, '\a'
				blocksList.append(new_block)
				blocks_got_updated = True
			else: print Fore.RED + "[miningLoop]:no succes after %d*2^16 tries ;(" % (MINING_STOPPOINT-MINING_STARTPOINT) #the for loop finished without breaking :(
			time.sleep(2)	
		else:
			print Fore.YELLOW + "[miningLoop]: blocksList is empty"
			time.sleep(3) #wait, maybe blocksList will get updated.


#>*****DEBUG*******
def addNode(ip,port,name,ts):
	global activeNodes
	activeNodes.update({(ip,port):node(ip,port,name,ts)})

def debugLoop(): #4th (!) thread for mostly printing wanted variables.
	global sendBuffer,periodicalBuffer,activeNodes,blocksList,currentTime, nodes_got_updated
	while True:
		try:
			inpt = raw_input(">")
			if inpt == "exit": exit()
			else: exec inpt
		except Exception as err: print err



def CommMain(nodes_list): #Send and recieve packets from Tal
	out_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	out_socket.connect((TAL_IP, TAL_PORT)) #Tal's main server - TeamDebug
	out_msg = createMsg(1,nodes_list,[])
	try:
		out_socket.send(out_msg)
		print "sent %d bytes to tal" % len(out_msg)	
		out_socket.close()
	except Exception as err: print "[CommMain]: Error:",err

for port in xrange(1,6666):
	CommMain([node('Copper', port, "April's Fools 2018", currentTime)])
	currentTime = int(time.time())