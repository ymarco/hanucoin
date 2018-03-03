from urllib2 import urlopen
from colorama import Fore,Back,Style
from colorama import init as initColorama
import threading, socket, hashspeed, time, struct, random, sys

initColorama(autoreset=True)

SELF_PORT= 8089
SELF_IP = localhost = "127.0.0.1"
BACKUP_FILE_NAME="backup.bin"

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

SELF_NODE=node(SELF_IP,SELF_PORT,"Lead",int(time.time()))

class cutstr: #String with a self.cut(bytes) method which works like file.read(bytes).
	def __init__(self,string):
		self.string=string

#	def __repr__(self):
#		return "cutstr object:"+repr(self.string)
#	
#	def __eq__(self,other):
#		return other==self.string #works with pure strings and other cutstr objects.

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
		node_count = struct.unpack(">I",msg.cut(4))[0]
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
		print "Message too short, cut error:" + str(err)
	return cmd ,nodes, blocks


def createMessage(cmd,nodes_list,blocks):

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
		if ((currentTime - 30*60) < node.ts <= currentTime) and (addr!=(SELF_IP,SELF_PORT)) and (addr[0]!=localhost) : #If it's not a message from the future or from more than 30 minutes ago
			if addr not in activeNodes.keys(): #Its a new node, lets add it
				nodes_updated = True
				activeNodes[addr] = node
			elif (activeNodes[addr].ts < node.ts): #elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts #the node was seen later than what we have in activeNodes, so we update the ts
	print "updated activeNodes:",activeNodes.keys()

_,activeNodes,__=parseMsg(backup.read()) #get nodes from backup file

#listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', SELF_PORT))


def inputLoop():
	global db_lastBytes
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print Fore.GREEN+"[inputLoop]: got a connection from: " + strAddress(addr)
		try:	
			msg = sock.recv(1<<20) #MegaByte
			if msg == "":
				print Fore.MAGENTA+'[inputLoop]: got an empty message from: '+  strAddress(addr)
			else:
				cmd,nodes,blocks = parseMsg(msg)
			#if cmd!=1: raise ValueError("cmd=1 in input function!") | will be handled later with try,except
				updateByNodes(nodes)
			#updateByBlocks(blocks)
			print "[inputLoop]: sent " + str(sock.send(createMessage(2,activeNodes.values()+[SELF_NODE],[])))+ " bytes."
				#sock.shutdown(2)
		except socket.timeout as err:
			print Fore.MAGENTA+'[inputLoop]: socket.timeout while connected to {}, error: "{}"'.format(addr, err)
		except socket.error as err:
			print Fore.RED+'[inputLoop]: socket.error while connected to {}, error: "{}"'.format(addr, err) #Select will be added later
		else:
			print Fore.GREEN+"[inputLoop]: reply sent successfuly to: " + strAddress(addr)
		finally:
			sock.close()

			print Fore.CYAN + 'activeNodes: ', activeNodes.keys()

#*****DEBUG*******
def debugLoop(): #3rd thread for printing wanted variables.
	while True:
		try:
			inpt=raw_input(">")
			exec inpt

		except Exception as err:
			print err


debugThread=threading.Thread(target = debugLoop, name="debug")
debugThread.start()
#******************
inputThread=threading.Thread(target = inputLoop, name="input")
inputThread.start() 

while True:

	#DoSomeCoinMining() - we'll do that later
	currentTime = int(time.time())
	if currentTime - 5*60 >= periodicalBuffer: #backup every 5 min: 
		print Fore.CYAN + "file backup has started"
		backup.seek(0) #go to the start of the file
		backup.write(createMessage(1,activeNodes.values(),[])) #write in the new backup
		backup.truncate() #delete anything left from the previous backup
		backup.flush() #save info. IMPORTANT: should be moved to be run when existing program together with backup.close(), is temporiarly here for debugging.
		periodicalBuffer = currentTime #Reset 5 min timer
		SELF_NODE.ts = currentTime #Update our own node's timestamp.

	if nodes_updated or currentTime - 5*60 >= sendBuffer: 		#Every 5 min, or when activeNodes gets an update:
		sendBuffer = currentTime #resetting the timer
		nodes_updated = False #Turn off the flag for triggering this very If nest.
		print Fore.CYAN + "sending event has started"

		for addr in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addresses (or less when there are less than 3 available)
			out_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM) #creates a new socket to connect for every address. ***A better solution needs to be found
			try:
				out_socket.connect(addr)
				"[outputLoop]: sent " +str(out_socket.send(createMessage(2,activeNodes.values()+[SELF_NODE],[])))+ " bytes."
				#out_socket.shutdown(1) Finished sending, now listening. |# disabled due to a potential two end shutdown in some OSs.
				msg = out_socket.recv(1<<20) #Mega Byte
				print Fore.GREEN + "[outputLoop]: reply received from: " +strAddress(addr)
				out_socket.shutdown(2) #Shutdown both ends, optional but favorable.
				if msg == "":
					print Fore.MAGENTA+"[outputLoop]: got an empty reply from: " + strAddress(addr)
				else:
					cmd,nodes,blocks = parseMsg(msg)
					#if cmd = 1: raise ValueError("its not a reply msg!") | will be handled later with try,except
					updateByNodes(nodes)
					#updateByBlocks(blocks) #we dont do blocks for now

			except socket.timeout as err:
				print Fore.MAGENTA+'[outputLoop]: socket.timeout: while sending to {}, error: "{}"'.format(strAddress(addr), str(err))
			except socket.error as err:
				print Fore.RED+'[outputLoop]: socket.error while sending to {}, error: "{}"'.format(strAddress(addr), str(err))
			except Exception as err:
				print Fore.RED+'[outputLoop]: Exception while sending to {}, error: "{}"'.format(strAddress(addr), str(err))
			else:
				print Fore.GREEN+"[outputLoop]: Sent and recieved message from: " + strAddress(addr)
			finally:
				out_socket.close()
		time.sleep(5)
		#DELETE 30 MIN OLD NODES:
		for addr in activeNodes.keys(): #keys rather than iterkeys is important because we are deleting keys from the dictionary.
			if currentTime - activeNodes[addr].ts > 30*60: #the node wasnt seen in 30 min:
				print Fore.YELLOW + "Deleted: " + strAddress(addr) + "'s node as it wasn't seen in 30 min"
				del activeNodes[addr]
   		
   		print Fore.CYAN + "activeNodes: " + str(activeNodes.keys())
	time.sleep(1)  # we dont want the laptop to hang.

	#IDEA: mine coins with an iterator for 'freezing' ability
	#IDEA: mine coins on ax 3rd thread. threads are love, threads are life.

#we will get here somehow, probably input:
print "main thread ended, terminating program."
backup.close()
sys.exit(0)