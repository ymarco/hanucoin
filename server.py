import threading, socket, hashspeed2, time, struct, random, sys, atexit


class dictobj(object):
	def __init__(self, diction):
		self.__dict__ = diction


from urllib2 import urlopen

try:
	from colorama import Fore, Back, Style, init as initColorama

	initColorama(autoreset=True)
except ImportError:
	Fore = dictobj({"RED": "", "BLUE": "", "CYAN": "", "GREEN": "", "YELLOW": "", "MAGENTA": ""})

# Exit event for terminating program (call exit() or exit_event.set()):
exit_event = threading.Event()
atexit.register(exit_event.set)
old_exit = exit
exit = exit_event.set

# Default values:
SELF_WALLET = hashspeed2.WalletCode(["Lead"])
NOONE_WALLET = hashspeed2.WalletCode(["Bob"])
SELF_IP = urlopen('http://ip.42.pl/raw').read()  # Get public ip
SELF_PORT = 8089
LOCALHOST = '127.0.0.1'
TEAM_NAME = "Lead"
TAL_IP = "34.244.16.40"
mining_slices = "1/1"
TAL_PORT = 8080
TIME_BETWEEN_SENDS = 5 * 60  # 5 min
send_self_node = True
# try to get ip and port from user input:
try:
	SELF_PORT = int(sys.argv[1])
	mining_slices = sys.argv[2]
	# {we'll write what slice we want to mine in. useful when several copies of this server are running together.
	# {say we want to run 3 servers, we'll run the 1st in '1/3' slice, 2nd in '2/3' slice, 3rd in '3/3' slice
	# {so they try numbers for mining from different xranges.

	TIME_BETWEEN_SENDS = int(sys.argv[3])  # in secs
	send_self_node = bool(sys.argv[4])
except IndexError: pass

mining_slice_1, mining_slice_2 = mining_slices.split('/')
mining_slice_1 = int(mining_slice_1)  # we want these as numbers, not strings
mining_slice_2 = int(mining_slice_2)

MINING_STARTPOINT = ((mining_slice_1 - 1) * (1 << 16)) / mining_slice_2
MINING_STOPPOINT = (mining_slice_1 * (1 << 16)) / mining_slice_2

periodicalBuffer = sendBuffer = int(time.time())
# DEBUG: *******************
periodicalBuffer -= (4 * 60 + 0.4 * 60)
sendBuffer -= (4 * 60 + 0.6 * 60)
# ************************
nodes_got_updated = False  # flag for when a new node is added.
blocks_got_updated = False  # flag for when someone (might be us) succeeds in mining.
START_NODES = struct.pack(">I", 0xbeefbeef)  # {Instead of unpacking and comparing to the number everytime we
START_BLOCKS = struct.pack(">I", 0xdeaddead)  # {will compare the raw string to the packed number.
backup = open("backup.bin", "r+b")
activeNodes = {}  # formatted as: {(ip, port): node(ip, port, name, ts),...}
blockList = []  # formatted as a binary list of all blocks - [block_bin_0, block_bin_1,...]
nodes_lock = threading.Lock()
blocks_lock = threading.Lock()  # locks prevent threads from changing the node and block lists at the same time
time.sleep(0)


def strAddress(addr_tup):
	return addr_tup[0] + ": " + str(addr_tup[1])


def datestr(secs):
	dateobj = time.gmtime(secs)
	return str(dateobj.tm_mday) + "/" + str(dateobj.tm_mon) + "/" + str(dateobj.tm_year) + " - " + str(dateobj.tm_hour) + ":" + str(dateobj.tm_min) + ":" + str(dateobj.tm_sec)


# takes (ip,port) and returns "ip: port"


class Node(object):
	def __init__(self, host, port, name, ts):
		self.host = host
		self.port = port
		self.name = name
		self.ts = ts

	def __eq__(self, other):
		return self.__dict__ == other.__dict__

	def __repr__(self):
		return repr(self.__dict__)

	def __getitem__(self, index):
		return (self.host, self.port, self.name, self.ts)[index]


if send_self_node: SELF_NODE = Node(SELF_IP, SELF_PORT, TEAM_NAME, int(time.time()))
else: SELF_NODE = []


class CutError(IndexError):
	pass  # Will be used later


class Cutstr(object):  # String with a self.cut(bytes) method which works like file.read(bytes).
	"""
	>>> CutObj = Cutstr("abcdefg")
	>>> CutObj.string
	"abcdefg
	>>> CutObj.cut(2)
	"ab"
	>>> CutObj.string
	"cdefg"
	"""
	def __init__(self, string):
		self.string = string

	def __len__(self):
		return len(self.string)

	def cut(self, bytes_to_cut):
		if bytes_to_cut > len(self.string):
			raise CutError("String too short for cutting by " + str(bytes_to_cut) + " bytes.")

		piece = self.string[:bytes_to_cut]
		self.string = self.string[bytes_to_cut:]
		return piece


def writeBackup(msg):
	global backup
	backup.seek(0)  # go to the start of the file
	backup.write(msg)  # write in the new backup
	backup.truncate()  # delete anything left from the previous backup
	backup.flush()  # save info.
	print Fore.CYAN + "- File backup is done"


def parseMsg(msg, desired_cmd):
	msg = Cutstr(msg)
	nodes = {}
	blocks = []
	if desired_cmd != struct.unpack(">I", msg.cut(4))[0]: raise ValueError("[parseMsg]: Wrong cmd accepted")
	if msg.cut(4) != START_NODES: raise ValueError("[parseMsg]: Wrong start_nodes")
	node_count = struct.unpack(">I", msg.cut(4))[0]
	for _ in xrange(node_count):
		name_len = struct.unpack("B", msg.cut(1))[0]
		name = msg.cut(name_len)
		host_len = struct.unpack("B", msg.cut(1))[0]
		host = msg.cut(host_len)
		port = struct.unpack(">H", msg.cut(2))[0]
		ts = struct.unpack(">I", msg.cut(4))[0]
		nodes[(host, port)] = Node(host, port, name, ts)

	if msg.cut(4) != START_BLOCKS: raise ValueError("[parseMsg]: Wrong start_blocks")
	block_count = struct.unpack(">I", msg.cut(4))[0]
	for _ in xrange(block_count):
		blocks.append(msg.cut(32))  # NEEDS CHANGES AT THE LATER STEP
	print '    [parseMsg]: finished parsing. block count: ', block_count
	return nodes, blocks


def createMsg(cmd, node_dict, block_list):
	parsed_cmd = struct.pack(">I", cmd)
	nodes_count = struct.pack(">I", len(node_dict))

	parsed_nodes = ''
	for node in node_dict:
		parsed_nodes += struct.pack("B", len(node.name)) + node.name + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	block_count = struct.pack(">I", len(block_list))
	parsed_blocks = ''
	for block in block_list:
		parsed_blocks += block

	return parsed_cmd + START_NODES + nodes_count + parsed_nodes + START_BLOCKS + block_count + parsed_blocks


def updateByNodes(nodes_dict):
	global activeNodes, nodes_updated
	with nodes_lock:
		for addr, node in nodes_dict.iteritems():
			if ((int(time.time()) - 60 * 60) < node.ts <= int(time.time())) and (LOCALHOST, SELF_PORT) != addr != (SELF_IP, SELF_PORT):  # If it's not a message from the future or from more than 30 minutes ago
				if addr not in activeNodes.keys():  # If it's a new node, add it
					nodes_updated = True
					activeNodes[addr] = node
				elif (activeNodes[addr].ts < node.ts):  # elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
					activeNodes[addr].ts = node.ts  # the node was seen later than what we have in activeNodes, so we update the ts
				#  else: print Fore.MAGENTA + "DIDN'T ACCEPT NODE OF " + strAddress(addr) + " DUE TO AN OLDER TIMESTAMP THAN OURS"
			#  else: print Fore.RED + "DIDN'T ACCEPT NODE OF " + strAddress(addr) + " DUE TO AN INVALID TIMESTAMP/ADDRESS: ", currentTime - 30 * 60 - node.ts, currentTime - node.ts, datestr(node.ts)


def updateByBlocks(blocks):
	# returns True if updated blockList, else - False
	global blockList, blocks_got_updated
	with blocks_lock:
		if len(blockList) <= 2:
			blockList = blocks
			return True
		# else: check if ((list is longer than ours) and (last block is valid)) and (the lists are connected)
		if (len(blockList) < len(blocks)):  # and (hashspeed2.IsValidBlock(blocks[-2],blocks[-1])==0) and hashspeed2.IsValidBlock(blockList[-1],blocks[len(blockList)])==0:
			blockList = blocks
			blocks_got_updated = True


def recvMsg(sock, desired_msg_cmd, timeout=15):
	data = ""
	watchdog = int(time.time())
	while int(time.time()) - watchdog < timeout:  # aborts if it lasts more than timeout
		data += sock.recv(1 << 10)  # KiloByte
		try:
			nodes, blocks = parseMsg(data, desired_msg_cmd)
		except CutError: continue
		except ValueError as err:
			print '[recvMsg]: invalid data received, error: ', err
			return {}, []
		else:
			print '[recvMsg]: message received successfully'
			return nodes, blocks


def handleInSock(sock, addr):
	try:
		nodes, blocks = recvMsg(sock, desired_msg_cmd=1)
		updateByNodes(nodes)
		updateByBlocks(blocks)
		sock.shutdown(socket.SHUT_RD)  # Finished receiving, now sending.
		out_message = createMsg(2, activeNodes.values() + [SELF_NODE], blockList)
		bytes_sent = 0
		while bytes_sent < len(out_message):
			bytes_sent += sock.send(out_message[bytes_sent:])
		sock.shutdown(2)

	except socket.timeout as err: print Fore.MAGENTA + '[handleInSock]: socket.timeout while connected to {}, error: "{}"'.format(strAddress(addr), err)
	except socket.error as err: print Fore.RED + '[handleInSock]: socket.error while connected to {}, error: "{}"'.format(strAddress(addr), err)  # Select will be added later
	else: print Fore.GREEN + '[handleInSock]: reply of %d bytes sent successfully back to: %s' % (bytes_sent, strAddress(addr))
	finally: sock.close()


backupMSG = backup.read()
if backupMSG:
	print 'Loading backup'
	BACKUP_NODES, _ = parseMsg(backupMSG, 1)  # get nodes from backup file
	updateByNodes(BACKUP_NODES)  # we don't want to updateByBlocks cause these blocks are probably outdated

# listen_socket is global
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind(('', SELF_PORT))

socket.setdefaulttimeout(5)  # All sockets except listen_socket need timeout. may be too short
# listen_socket will run on its own inputLoop thread and as so doesnt need timeout
out_messages_input = []


def inputLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		print Fore.GREEN + "[inputLoop]: got a connection from: " + strAddress(addr)
		handleInSockThread = threading.Thread(target=handleInSock, args=(sock, addr), name=strAddress(addr) + " inputThread")
		handleInSockThread.daemon = True
		handleInSockThread.start()


def miningLoop():
	global blockList, blocks_got_updated
	new_block = None
	while True:
		if blockList:  # blockList aint empty
			if hashspeed2.unpack_block_to_tuple(blockList[-1])[1] == SELF_WALLET:
				wallet = NOONE_WALLET
				print Fore.CYAN + '[miningLoop]: mining as "no_body". Mining in progress'
			else:
				wallet = SELF_WALLET
				print Fore.CYAN + '[miningLoop]: mining as "Lead". Mining in progress'

			for i in xrange(MINING_STARTPOINT, MINING_STOPPOINT):
				start_num = i * (1 << 16)
				new_block = hashspeed2.MineCoinAttempts(wallet, blockList[-1], start_num, 1 << 16)
				if blocks_got_updated or new_block is not None: break  # start all over again, we have a new block

			if new_block is not None:
				print Style.BRIGHT + Fore.BLUE + "[miningLoop]: Mining attempt succeeded (!) \a"
				blockList.append(new_block)
				blocks_got_updated = True
			elif blocks_got_updated: print Fore.YELLOW + "[miningLoop]: someone succeeded mining, trying again on the new block"
			else: print Fore.RED + "[miningLoop]: no success after %d*2^16 tries :,( " % (MINING_STOPPOINT - MINING_STARTPOINT)  # the for loop finished without breaking :(
			time.sleep(2)
		else:
			print Fore.YELLOW + "[miningLoop]: blockList is empty"
			time.sleep(3)  # wait, maybe blockList will get updated.
		time.sleep(0.1)


# >*****DEBUG*******
def addNode(ip, port, name, ts):
	global activeNodes
	activeNodes.update({(ip, port): Node(ip, port, name, ts)})


def debugLoop():  # 4th (!) thread for mostly printing wanted variables.
	global sendBuffer, periodicalBuffer, activeNodes, blockList, nodes_got_updated
	while True:
		try:
			inpt = raw_input(">")
			if inpt == "exit": exit()
			else: exec inpt
		except Exception as err: print err


debugThread = threading.Thread(target=debugLoop, name="debug")
debugThread.daemon = True
debugThread.start()

inputThread = threading.Thread(target=inputLoop, name="input")
inputThread.daemon = True
inputThread.start()

miningThread = threading.Thread(target=miningLoop, name="mining")
miningThread.daemon = True
miningThread.start()


def CommMain():  # Send and receive packets from Tal
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((TAL_IP, TAL_PORT))  # Tal's main server - TeamDebug
	out_msg = createMsg(1, [SELF_NODE], [])

	try:
		sock.sendall(out_msg)
		print "sent %d bytes to TeamDebug" % len(out_msg)
		nodes, blocks = recvMsg(sock, desired_msg_cmd=2)
		updateByNodes(nodes)
		updateByBlocks(blocks)
		print activeNodes.viewkeys()
	except socket.timeout as err: print Fore.MAGENTA + '[CommMain]: socket.timeout while connected to tal, error: ', err
	except socket.error as err: print Fore.RED + '[CommMain]: socket.error while connected to tal, error: ', err
	else: print Fore.GREEN + '[CommMain]: sent and received message successfully from Tal'
	finally: sock.close()


CommMain()

while True:
	if int(time.time()) - 5 * 60 >= periodicalBuffer:  # backup every 5 minutes:
		periodicalBuffer = int(time.time())  # Reset 5 min timer

		writeBackup(createMsg(1, activeNodes.viewvalues(), []))
		SELF_NODE.ts = int(time.time())  # Update our own node's timestamp.

		print Fore.CYAN + "activeNodes: " + str(activeNodes.viewkeys())

		CommMain()  # Ensure that we are still up with the main server (Tal)

	if nodes_got_updated or blocks_got_updated or int(time.time()) - TIME_BETWEEN_SENDS >= sendBuffer:  # Every 5 minutes, or when nodes_got_updated is true:
		sendBuffer = int(time.time())  # resetting the timer
		nodes_got_updated = blocks_got_updated = False  # Turn off the flag for triggering this very If nest.
		print "deleting event has started"
		# DELETE 30 MIN OLD NODES:
		for node in activeNodes.values():  # values rather than itervalues is important because we are deleting keys from the dictionary.
			if int(time.time()) - node.ts > 30 * 60:  # the node wasnt seen in 30 min:
				print Fore.YELLOW + "Deleted: {}'s node as it wasn't seen in 30 min".format(node[:3])
				del activeNodes[node[:2]]  # nod[:2] returns (host,port) which happens to also be nod's key in activeNodes

		for nod in random.sample(activeNodes.viewvalues(), min(3, len(activeNodes))):  # Random 3 addresses (or less when there are less than 3 available)
			out_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # creates a new socket to connect for every address. ***A better solution needs to be found
			print Fore.CYAN + "[outputLoop]: trying to send {} a message:".format(nod[:3])
			try:
				out_socket.connect(nod[:2])
				out_msg = createMsg(1, activeNodes.values() + [SELF_NODE], blockList)
				bytes_sent = 0
				while bytes_sent < len(out_msg):
					bytes_sent += out_socket.send(out_msg[bytes_sent:])
				out_socket.shutdown(socket.SHUT_WR)  # Finished sending, now listening.

				nodes, blocks = recvMsg(out_socket, desired_msg_cmd=2)
				updateByNodes(nodes)
				updateByBlocks(blocks)
				out_socket.shutdown(2)  # Shutdown both ends, optional but favorable.

			except socket.timeout as err:    print Fore.MAGENTA + '[outputLoop]: socket.timeout: while connected to {}, error: "{}"'.format(nod[:3], err)
			except socket.error as err:        print Fore.RED + '[outputLoop]: socket.error: while connected to {}, error: "{}"'.format(nod[:3], err)
			else:                            print Fore.GREEN + '[outputLoop]: Sent and received a message from: {}'.format(nod[:3])
			finally:                        out_socket.close()

	if exit_event.wait(1): break  # we dont want the laptop to hang. (returns True if exit event is set, otherwise returns False after a second.)

# we will get here somehow, probably user input from debugLoop:
print "Main thread ended, terminating program."
backup.close()  # sys.exit(0)

# TODO LIST:

# 1. Make more things into functions (ex. file backup should be a function)#did backupRewite func ~Marco

# BUGS:

# For some reason currentTime and our node's timestamps are a hour more than they're supposed to be (which causes updateByNodes to not accept any nodes)
# What's weird about this is that people still send back our node with the 1 hour-into-future timestamp
