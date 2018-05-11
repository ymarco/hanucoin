from __future__ import print_function, division
from urllib2 import urlopen
from random import sample
from multiprocessing import Pool, TimeoutError
import threading, socket, hashspeed2, time, struct, sys, atexit, utils


class DictObj(object):
	def __init__(self, diction):
		self.__dict__ = diction


try:
	from colorama import Fore, Back, Style, init as initColorama

	initColorama(autoreset=True)
except ImportError:
	Fore = DictObj({"RED": "", "BLUE": "", "CYAN": "", "GREEN": "", "YELLOW": "", "MAGENTA": ""})  # If colorama isn't installed the colorama variables will all be ""
	Style = DictObj({"BRIGHT": "", "DIM": "", "NORMAL": ""})

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
TAL_PORT = 8080
mining_slice_1 = mining_slice_2 = 1
POOL_PROCESS_NUM = 3
# try to get port and stuff from user input:
try:
	SELF_PORT = int(sys.argv[1])
	mining_slice_1, mining_slice_2 = map(int, sys.argv[2].split('/'))
	# {we'll write what slice we want to mine in. useful when several copies of this server are running together.
	# {say we want to run 3 servers, we'll run the 1st in '1/3' slice, 2nd in '2/3' slice, 3rd in '3/3' slice
	# {so they try numbers for mining from different xranges.

	POOL_PROCESS_NUM = int(sys.argv[3])  # set to 0 if you don't want to mine at all

except IndexError: pass


MINING_STARTPOINT = ((mining_slice_1 - 1) * (1 << 16)) // mining_slice_2
MINING_STOPPOINT = (mining_slice_1 * (1 << 16)) // mining_slice_2

periodicalBuffer = sendBuffer = int(time.time())

nodes_got_updated = threading.Event()  # flag for when a new node is added.
blocks_got_updated = threading.Event()  # flag for when someone (might even be us) succeeds in mining.
we_mined_a_block = threading.Event()
START_NODES = struct.pack(">I", 0xbeefbeef)  # {Instead of unpacking and comparing to the number every time we
START_BLOCKS = struct.pack(">I", 0xdeaddead)  # {will compare the raw string to the packed number.
backup = open("backup.bin", "r+b")
activeNodes = {}  # formatted as: {(ip, port): Node(ip, port, name, ts),...}
blockList = []  # formatted as a binary list of all blocks - [block_bin_0, block_bin_1,...]
nodes_lock = threading.Lock()
blocks_lock = threading.Lock()  # locks prevent threads from changing the node and block lists at the same time
print_lock = threading.Lock()
time.sleep(0)


def safeprint(*args):
	with print_lock:
		print(*args)


# takes (ip,port) and returns "ip: port"


class Node(object):
	def __init__(self, host, port, name, ts):
		self.host = host
		self.port = port
		self.team = name
		self.ts = ts

	def __eq__(self, other):
		return self.__dict__ == other.__dict__

	def __repr__(self):
		return repr(self.__dict__)

	def __getitem__(self, index):
		return (self.host, self.port, self.team, self.ts)[index]


SELF_NODE = Node(SELF_IP, SELF_PORT, TEAM_NAME, int(time.time()))


class CutError(IndexError):
	pass


class CutStr(object):  # String with a self.cut(bytes) method which works like file.read(bytes).
	"""
	>>> CutObj = CutStr("abcdefg")
	>>> CutObj.string
	"abcdefg"
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
			raise CutError("String too short for cutting by %d bytes." % bytes_to_cut)

		piece = self.string[:bytes_to_cut]
		self.string = self.string[bytes_to_cut:]
		return piece


def writeBackup(msg):
	global backup
	backup.seek(0)  # go to the start of the file
	backup.write(msg)  # write in the new backup
	backup.truncate()  # delete anything left from the previous backup
	backup.flush()  # save info.
	safeprint(Fore.CYAN + "- File backup is done")


def parseMsg(msg, desired_cmd):
	msg = CutStr(msg)
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
		blocks.append(msg.cut(32))
	return nodes, blocks


def createMsg(cmd, node_dict, block_list):
	parsed_cmd = struct.pack(">I", cmd)
	nodes_count = struct.pack(">I", len(node_dict))

	parsed_nodes = ''
	for node in node_dict:
		parsed_nodes += struct.pack("B", len(node.team)) + node.team + struct.pack("B", len(node.host)) + node.host + struct.pack(">H", node.port) + struct.pack(">I", node.ts)

	block_count = struct.pack(">I", len(block_list))
	parsed_blocks = ''
	for block in block_list:
		parsed_blocks += block

	return parsed_cmd + START_NODES + nodes_count + parsed_nodes + START_BLOCKS + block_count + parsed_blocks


def updateByNodes(nodes_dict):
	global activeNodes
	with nodes_lock:
		for addr, node in nodes_dict.iteritems():
			if (int(time.time()) - 30 * 60) >= node.ts <= int(time.time()) or (node.ts > int(time.time())) or (LOCALHOST, SELF_PORT) == addr or addr == (SELF_IP, SELF_PORT):
				continue  # If it's a node from the future or from more than 30 minutes ago

			if addr not in activeNodes.keys():  # If it's a new node, add it
				nodes_got_updated.set()
				activeNodes[addr] = node
			elif activeNodes[addr].ts < node.ts:  # elif prevents exceptions here (activeNodes[addr] exists - we already have this node)
				activeNodes[addr].ts = node.ts  # the node was seen later than what we have in activeNodes, so we update the ts
			#  else: print Fore.MAGENTA + "DIDN'T ACCEPT A NODE OF " + utils.strAddress(addr) + " DUE TO AN OLDER TIMESTAMP THAN OURS"
		#  else: print Fore.RED + "DIDN'T ACCEPT A NODE OF " + utils.strAddress(addr) + " DUE TO AN INVALID TIMESTAMP/ADDRESS: ", currentTime - 30 * 60 - node.ts,  # currentTime - node.ts, utils.stdDate(node.ts)


def updateByBlocks(blocks):
	global blockList
	with blocks_lock:
		if len(blockList) <= 2:
			blockList = blocks
		# else: check if ((list is longer than ours) and (last block is valid)) and (the lists are connected)
		elif (len(blockList) < len(blocks)) and (hashspeed2.IsValidBlock(blocks[-2], blocks[-1]) == 0):  # and hashspeed2.IsValidBlock(blockList[-1],blocks[len(blockList)])==0:
			blockList = blocks
			blocks_got_updated.set()


def recvMsg(sock, desired_msg_cmd, timeout=15):
	data = ""
	watchdog = int(time.time())
	while int(time.time()) - watchdog < timeout:  # aborts if it lasts more than timeout
		data += sock.recv(1 << 10)  # KiloByte
		try: nodes, blocks = parseMsg(data, desired_msg_cmd)
		except CutError: continue
		except ValueError as err:
			safeprint(Fore.MAGENTA + '[recvMsg]: invalid data received, error: ', err)
			return {}, []
		else:
			safeprint(Fore.GREEN + '[recvMsg]: message received successfully')
			return nodes, blocks
	return {}, []


def handleInSock(sock, address_info):
	try:
		nodes, blocks = recvMsg(sock, desired_msg_cmd=1)
		sock.shutdown(socket.SHUT_RD)  # Finished receiving, now sending.
		out_message = createMsg(2, activeNodes.values() + [SELF_NODE], blockList)
		sock.sendall(out_message)
		# while bytes_sent < len(out_message):
		# bytes_sent += sock.send(out_message[bytes_sent:])
		sock.shutdown(2)
		updateByNodes(nodes)
		updateByBlocks(blocks)

	except socket.timeout as err: safeprint(Fore.MAGENTA + '[handleInSock]: socket.timeout while connected to {}, error: "{}"'.format(address_info, err))
	except socket.error as err: safeprint(Fore.RED + '[handleInSock]: socket.error while connected to {}, error: "{}"'.format(address_info, err))  # Select will be added later
	else: safeprint(Fore.GREEN + '[handleInSock]: reply of %dkb sent successfully back to: %s' % (len(out_message)//(1 << 10), address_info))
	finally: sock.close()


if __name__ == "__main__":
	# listen_socket is global
	listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	listen_socket.bind(('', SELF_PORT))

	socket.setdefaulttimeout(15)  # All sockets except listen_socket (socket for accepting) need timeout. may be too short


def acceptLoop():
	listen_socket.listen(1)
	while True:
		sock, addr = listen_socket.accept()  # synchronous, blocking
		address_info = utils.strAddress(addr) + " (" + ("/".join([node.team for key, node in activeNodes.iteritems() if key[0] == addr[0]]) or "unknown team") + ")"
		#  ^ evaluates to "ip:port (team1/team2/team3)". usually each ip only has 1 team.
		safeprint(Fore.YELLOW + Style.BRIGHT + "[acceptLoop]: got a connection from: " + address_info)
		handleInSockThread = threading.Thread(target=handleInSock, args=(sock, address_info), name=utils.strAddress(addr) + " inputThread")
		handleInSockThread.daemon = True
		handleInSockThread.start()


def Miner((mining_range_start, mining_range_stop, block_to_mine_on)):
	if hashspeed2.unpack_block_to_tuple(block_to_mine_on)[1] == SELF_WALLET:
		wallet = NOONE_WALLET
		safeprint(Fore.CYAN + '[miningLoop]: mining as "no_body". Mining in progress')
	else:
		wallet = SELF_WALLET
		safeprint(Fore.CYAN + '[miningLoop]: mining as "Lead". Mining in progress')
	safeprint("Miner: we are  done with the if's")
	for i in xrange(mining_range_start, mining_range_stop):
		start_num = i * (1 << 16)
		new_block = hashspeed2.MineCoinAttempts(wallet, block_to_mine_on, start_num, 1 << 16)
		if new_block: return new_block  # success!
	return None


def miningLoop(mining_start_range=MINING_STARTPOINT, mining_stop_range=MINING_STOPPOINT):
	mining_ranges = []
	global blockList
	# preparing ranges for our workers to mine on:
	for num in xrange(POOL_PROCESS_NUM):
		start = mining_start_range + num*(mining_stop_range - mining_start_range)//POOL_PROCESS_NUM
		stop = mining_start_range + (num + 1)*(mining_stop_range - mining_start_range)//POOL_PROCESS_NUM
		mining_ranges.append((start, stop))

	time.sleep(10)  # wait for blockList to update
	while not blockList:
		safeprint(Fore.YELLOW + "[miningLoop]: blockList is empty")
		time.sleep(3)  # wait, maybe blockList will get an update

	while True:
		pool = Pool(processes=POOL_PROCESS_NUM)

		res_obj = pool.imap_unordered(Miner, utils.addStrToTupList(mining_ranges, blockList[-1]))
		while True:
			try:
				new_block = res_obj.next(2)  # raises TimeoutError if res_obj doesnt have results
				if not new_block: continue  # possible that the for loop in Miner finished without success - if so, it returns None
				# we DID mine!
				safeprint(Style.BRIGHT + Fore.GREEN + "[miningLoop]: Mining attempt succeeded (!) \a")
				pool.terminate()  # no need for the other Miners to continue mining on that block
				blockList.append(new_block)
				we_mined_a_block.set()
				pool.join()
				break
			except TimeoutError: pass  # no success? alright, keep trying
			except StopIteration: blocks_got_updated.wait()  # wait for someone else to mine

			if blocks_got_updated.isSet():
				pool.terminate()  # start mining again, on the new block
				blocks_got_updated.clear()
				safeprint(Fore.RED + "[miningLoop]: someone else succeeded mining D:")
				pool.join()
				break


# >*****DEBUG*******


def addNode(ip, port, name, ts):
	global activeNodes
	activeNodes.update({(ip, port): Node(ip, port, name, ts)})


def debugLoop():  # 4th (!) thread for mostly printing wanted variables.
	global sendBuffer, periodicalBuffer, activeNodes, blockList
	while True:
		try:
			inpt = raw_input(">")
			if inpt == "exit": exit()
			else: exec inpt
		except Exception as err: safeprint(err)


def CommOut(addr, team_info=""):  # Send and receive response (optional 'team' argument for prints)
	team_str = (team_info and " (" + team_info + ")")  # Will add '(<team>)' to the prints if team string is present.
	address_info = utils.strAddress(addr) + team_str
	safeprint(Fore.YELLOW + "[CommOut]: trying to communicate with {}:".format(address_info))
	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	sock.connect((TAL_IP, TAL_PORT))  # Tal's main server - TeamDebug
	out_msg = createMsg(1, activeNodes.values() + [SELF_NODE], blockList)

	try:
		sock.sendall(out_msg)
		safeprint(Fore.GREEN + "sent %dkb to %s" % (len(out_msg)//1000, address_info))
		sock.shutdown(socket.SHUT_WR)

		nodes, blocks = recvMsg(sock, desired_msg_cmd=2)
		updateByNodes(nodes)
		updateByBlocks(blocks)
		sock.shutdown(2)  # Shutdown both ends, optional but favorable
	except socket.timeout as err: safeprint(Fore.MAGENTA + '[CommOut]: socket.timeout while connected to {}, error: {}'.format(address_info, err))
	except socket.error as err: safeprint(Fore.RED + '[CommOut]: socket.error while connected to {}, error: '.format(address_info), err)
	else: safeprint(Fore.GREEN + '[CommOut]: sent and received message successfully from {}'.format(address_info))
	finally: sock.close()


def CommMain():  # Communicate with the main server (Tal's)
	CommOut((TAL_IP, TAL_PORT), team_info="CommMain: TeamDebug")


if __name__ == "__main__":  # MAIN PROGRAM

	acceptThread = threading.Thread(target=acceptLoop, name="accept")
	acceptThread.daemon = True
	acceptThread.start()

	CommMain()  # Communicate with Tal for the first time

	debugThread = threading.Thread(target=debugLoop, name="debug")
	debugThread.daemon = True
	debugThread.start()

	if POOL_PROCESS_NUM != 0:
		miningThread = threading.Thread(target=miningLoop, name="mining")
		miningThread.daemon = True
		miningThread.start()

	backupMSG = backup.read()
	if backupMSG:
		safeprint('Loading backup')
		BACKUP_NODES, _ = parseMsg(backupMSG, 1)  # get nodes from backup file
		updateByNodes(BACKUP_NODES)  # we don't want to updateByBlocks cause these blocks are probably outdated

	while True:
		if int(time.time()) - 5 * 60 >= periodicalBuffer:  # Backup every 5 minutes:
			periodicalBuffer = int(time.time())  # Reset 5 min timer

			writeBackup(createMsg(1, activeNodes.viewvalues(), []))
			SELF_NODE.ts = int(time.time())  # Update our own node's timestamp.
			safeprint(Fore.CYAN + "activeNodes: " + str(activeNodes.viewkeys()))
			CommMain()  # Ensure that we are still up with the main server (Tal)

			# DELETE 30 MIN OLD NODES:
			for node in activeNodes.values():  # using values rather than itervalues is important because we are deleting keys from the dictionary.
				if int(time.time()) - node.ts > 30 * 60:  # the node wasn't seen in 30 min:
					safeprint(Fore.YELLOW + "Deleted: {}'s node as it wasn't seen in 30 min".format(node[:3]))
					del activeNodes[node[:2]]  # node[:2] returns (host,port) which happens to also be node's key in activeNodes

		elif not activeNodes:
			safeprint(Fore.MAGENTA + "activeNodes is empty, attempting communication with TeamDebug:")
			CommMain()
			time.sleep(3)

		if nodes_got_updated.isSet() or we_mined_a_block.isSet() or int(time.time()) - 5*60 >= sendBuffer:  # Every 5 minutes, or when nodes_got_updated is true:
			sendBuffer = int(time.time())  # resetting the timer
			nodes_got_updated.clear()
			we_mined_a_block.clear()  # Turn off the flag for triggering this very If nest.
			# don't clear blocks_got_updated - miningLoop should clear it on its own
			for node in sample(activeNodes.viewvalues(), min(3, len(activeNodes))):  # Random 3 addresses (or less when there are less than 3 available)
				CommOutThread = threading.Thread(target=CommOut, args=(node[:2], node.team), name=utils.strAddress(node[:3]) + " CommOut")
				CommOutThread.daemon = True
				CommOutThread.start()

		if exit_event.wait(1): break  # we don't want the laptop to hang. (returns True if exit event is set, otherwise returns False after a second.)

	# we will get here somehow, probably user input from debugLoop:
	safeprint("Main thread ended, terminating program.")
	backup.close()  # sys.exit(0)

# TODO LIST:

# 1. Make more things into functions (ex. file backup should be a function) | did writeBackup func ~Marco | did CommOut() ~Banos
# 2. We should probably rename mining_slice_1 and 2 to something more readable ~Banos | im open to suggestions ~Marco
# 3. Simplify things regarding the exit event and the atexit registered function (add comments and improve variable names or thing of a different code design)
# 4.
# 5.

# BUGS:

# 1.
# 2.
# 3.
