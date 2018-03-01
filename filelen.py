import sys
op=open(sys.argv[1],"rb")
print("binary len:", len(op.read()))
op2=open(sys.argv[1],"r")
print("text len:", len(op2.read()))