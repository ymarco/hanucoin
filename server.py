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
LOCALHOST="127.0.0.1"
SELF_PORT = 8089
SELF_IP = urlopen('http://ip.42.pl/raw').read() #Get public ip
BACKUP_FILE_NAME="backup.bin"
currentTime = int(time.time())
TEAM_NAME="Lead"
TAL_IP="34.244.16.40"
TAL_PORT=8080
BIND_RANGE=""
#try to get ip and port from user input:
try:
	if sys.argv[1] == "local":
		SELF_IP = TAL_IP = BIND_RANGE = LOCALHOST
		TAL_PORT = 7860
	elif sys.argv[1] != "public":
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
START_NODES = struct.pack(">I", 0xbeefbeef)  #{Instead of unpacking and comparing to the number everytime,
START_BLOCKS = struct.pack(">I", 0xdeaddead) #{we will compare the raw string to the packed number.
DO_BACKUP = BACKUP_FILE_NAME not in ("","nobackup","noBackup","NoBackup","NOBACKUP","none","None")
if DO_BACKUP:
	backup=open(BACKUP_FILE_NAME,"r+b")
activeNodes={}
#teamname = hashspeed.somethingWallet(lead)
#local ip = ''
def recvAll(sock):
	while True:
		dat=sock.recv(1<<10)	
		if not dat: break
		msg += dat #MegaByte
	return msg

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
		if ((currentTime - 30*60) < node.ts <= currentTime) and (LOCALHOST,SELF_PORT)!=addr!=(SELF_IP,SELF_PORT) : #If it's not a message from the future or from more than 30 minutes ago	
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
listen_socket.bind((BIND_RANGE, SELF_PORT)) #BIND_RANGE='' by default
global_sends=0
socket.setdefaulttimeout(120) #All sockets except listen_socket need timeout. may be too short
out_messages_input=[]
def inputLoop():
	global out_messages_input,global_sends
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
			print Fore.GREEN+"[inLoop]: finished recieving, now sending"
			sock.shutdown(socket.SHUT_RD)

			global_sends+=1
			out_message=createMsg(2,[],[]) #Sends an empty message (cmd=2, node_count=0, block_count=0)
			#sock.sendall(out_message)
			byts=1
			part=0
			while part<len(out_message):
				byts = sock.send(out_message[part:part+1024])
				print Fore.YELLOW+str(byts)
				part += byts
			sock.shutdown(2)
			out_messages_input.append(out_message)
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
debugThread=threading.Thread(target = debugLoop, name="debug")
debugThread.daemon=True
debugThread.start()
#******************<
inputThread=threading.Thread(target = inputLoop, name="input")
inputThread.daemon=True
inputThread.start() 

#getting nodes from tal:
out_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
out_socket.connect((TAL_IP, TAL_PORT)) #Tal's main server - TeamDebug
out_msg = createMsg(1,[SELF_NODE],[])
out_socket.sendall(out_msg)
in_msg=""
while True:
	dat = out_socket.recv(1<<10)
	if not dat: break
	in_msg += dat
out_socket.close()
cmd,nodes,blocks = parseMsg(in_msg)
updateByNodes(nodes)
print activeNodes.keys()


while True:
	
	#DoSomeCoinMining() - we'll do that later
	currentTime = int(time.time())
	if DO_BACKUP and currentTime - 5*60 >= periodicalBuffer: #backup every 5 min: 
		print Fore.CYAN + "file backup has started"
		backup.seek(0) #go to the start of the file
		backup.write(createMsg(1,activeNodes.values(),[])) #write in the new backup
		backup.truncate() #delete anything left from the previous backup
		backup.flush() #save info.
		periodicalBuffer = currentTime #Reset 5 min timer
		SELF_NODE.ts = currentTime #Update our own node's timestamp.

	if nodes_updated or currentTime - 5*60 >= sendBuffer: 		#Every 5 min, or when activeNodes gets an update:
		sendBuffer = currentTime #resetting the timer
		nodes_updated = False #Turn off the flag for triggering this very If nest.

		print "deleting event has started"
		#DELETE 30 MIN OLD NODES:
		for addr in activeNodes.keys(): #keys rather than iterkeys is important because we are deleting keys from the dictionary.
			if currentTime - activeNodes[addr].ts > 30*60: #the node wasnt seen in 30 min:
				print Fore.YELLOW + "Deleted: " + strAddress(addr) + "'s node as it wasn't seen in 30 min"
				del activeNodes[addr]

		print Fore.CYAN + "sending event has started"

		for addr in random.sample(activeNodes.viewkeys(), min(3,len(activeNodes))): #Random 3 addresses (or less when there are less than 3 available)
			out_socket=socket.socket(socket.AF_INET,socket.SOCK_STREAM) #creates a new socket to connect for every address. ***A better solution needs to be found
			print "[outputLoop]: trying to send {} a message:".format(addr)
			try:
				out_socket.connect(addr)
				out_msg=createMsg(1,activeNodes.values()+[SELF_NODE],[])
				byts=1
				part=0
				while part<len(out_msg):
					byts = out_socket.send(out_msg[part:part+1024])
					print Fore.YELLOW+str(byts)
					part += byts
				out_socket.shutdown(socket.SHUT_WR)
				#out_socket.shutdown(1) Finished sending, now listening. |# disabled due to a potential two end shutdown in some OSs.
				print Fore.GREEN+"[outLoop]: Finished sending, now recieving."
				in_msg=""
				while True:
					dat=out_socket.recv(1<<10)
					if not dat: break
					in_msg += dat
				print Fore.GREEN + "[outputLoop]: reply received from: " +strAddress(addr)
				out_socket.shutdown(2) #Shutdown both ends, optional but favorable.
				if in_msg == "":
					print Fore.MAGENTA+"[outputLoop]: got an empty reply from: " + strAddress(addr)
				else:
					cmd,nodes,blocks = parseMsg(in_msg)
					#if cmd = 1: raise ValueError("its not a reply msg!") | will be handled later with try,except //??!!
					updateByNodes(nodes)
					#updateByBlocks(blocks) #we mine on branch "blocks"

			except socket.timeout as err:	print Fore.MAGENTA+'[outputLoop]: socket.timeout: while sending to {}, error: "{}"'.format(strAddress(addr), err)
			except socket.error as err:		print Fore.RED+'[outputLoop]: socket.error while sending to {}, error: "{}"'.format(strAddress(addr), err)
			except ValueError as err:		print Fore.MAGENTA+'[outputLoop] got an invalid data msg from {}: {}'.format(strAddress(addr),err)
			else:							print Fore.GREEN+"[outputLoop]: Sent and recieved message from: " + strAddress(addr)
			finally:						out_socket.close()


   		
   		print Fore.CYAN + "activeNodes: " + str(activeNodes.keys())
	
	if exit_event.wait(1): break  # we dont want the laptop to hang. (returns True if exit event is set, otherwise returns False after a second.)

	#IDEA: mine coins with an iterator for 'freezing' ability
	#IDEA: mine coins on ax 3rd thread. threads are love, threads are life.
	#BUG: for some reason the program was only terminated when the sending events started (i callled exit() about a minute before that)
#we will get here somehow, probably input:
print "main thread ended, terminating program."
if DO_BACKUP: backup.close()
#sys.exit(0)

#BUG: Apperantly, alot of messages are recieved cut. We probably want to raise exceptions and check what's going on.