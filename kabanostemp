import struct
import time
hanukc = open("hanukcoin.bin")
cmd=struct.unpack(">I",hanukc.read(4))
start_nodes=struct.unpack(">I",hanukc.read(4))
node_count=struct.unpack(">I",hanukc.read(4))
nodes={}
for x in xrange(node_count):
	name_len=struct.unpack("B",hanukc.read(1))
	name=hanukc.read(name_len)
	host_len=struct.unpack("B",hanukc.read(1))
	host=hanukc.read(host_len)
	port=struct.unpack(">H",hanukc.read(2))
	last_seen_ts=struct.unpack(">I",hanukc.read(4))
	nodes[name]=(host,port,last_seen_ts)

start_blocks=struct.unpack(">I",hanukc.read(4))
block_count=struct.unpack(">I",hanukc.read(4))
for x in xrange(block_count):
	serial_number=struct.unpack(">I",hanukc.read(4))
	wallet=