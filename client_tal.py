from parseIGN import *
import threading, socket, hashspeed, time, Queue, struct, random, sys
print sys.argv
nodes=[node(sys.argv[1],int(sys.argv[2]),sys.argv[3],eval(sys.argv[4]))]
msg=createMessage(1,nodes,[])
soc=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
soc.connect(("34.244.16.40",8080))
soc.send(msg)
dat=soc.recv(1<<20)
cmd,nodes,blocks=parseMsg(dat)
