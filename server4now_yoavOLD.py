import threading
import Queue
import socket
import hashspeed


def HandleSoc(soc, socnum):
	socnum = {}
	#hanukc = open("hanukcoin.bin")
	socnum[cmd] = struct.unpack(">I",soc.read(4))
	socnum[start_nodes] = struct.unpack(">I",soc.read(4))
	socnum[node_count] = struct.unpack(">I",soc.read(4))
	socnum[nodes] = {}
	for x in xrange(socnum[node_count]):
		socnum[nodes][x] = {}
		socnum[nodes][x][name_len] = struct.unpack("B",soc.read(1))
		socnum[nodes][x][name] = soc.read(name_len)
		socnum[nodes][x][host_len] = struct.unpack("B",soc.read(1))
		socnum[nodes][x][host] = soc.read(host_len)
		socnum[nodes][x][port] = struct.unpack(">H",soc.read(2))
		socnum[nodes][x][last_seen_ts] = struct.unpack(">I",soc.read(4))


	socnum[start_blocks] = struct.unpack(">I",hanukc.read(4))
	socnum[block_count] = struct.unpack(">I",hanukc.read(4))
	socnum[blocks] = {}
	for x in xrange(socnum[block_count]):
		socnum[blocks][x] = {}
		socnum[blocks][x][serial_number] = struct.unpack(">I",hanukc.read(4))
		socnum[blocks][x][wallet] = struct.unpack(">I",soc.read(4))
		socnum[blocks][x][prev_sig] = hanukc.read(8)
		socnum[blocks][x][puzzle] = hanukc.read(4)
		socnum[blocks][x][sig] = hanukc.read(12)






#listen_socket is global
TCP_IP = '127.0.0.1'
TCP_PORT = 5005
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listen_socket.bind((TCP_IP, TCP_PORT))
listen_socket.listen(1)
g_queue = Queue.Queue()

def AcceptLoop():
   global g_queue
   while True:
       soc, addr = listen_socket.accept()  # synchronous, blocking
       g_queue.put(soc)


threading.Thread(target=AcceptLoop).start()



while True:
   # soc is a new accepted socket
   try:
       soc = g_queue.get()
       sockets.append(soc)  # add to list
   except Queue.Empty:
       soc = None

   #HandleAllSockets()  # handle sockets[i]
   #DoSomeCoinMining()
   time.sleep(0.1)  # if you don't want the laptop to hang.
