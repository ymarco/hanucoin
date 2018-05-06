import itertools

def exrange(a,b=None): #Extended xrange, bypasses the limit of xrange(n) (n < 2**31-1)
	if b:
		return iter(itertools.count(a).next,b)
	return iter(itertools.count().next,a)


def strAddress(addr_tup): #Converts an adress tuple into a string e.g. (v)
	return addr_tup[0] + ":" + str(addr_tup[1])


def stdDate(secs):
	dateobj = time.gmtime(secs)
	return str(dateobj.tm_mday) + "/" + str(dateobj.tm_mon) + "/" + str(dateobj.tm_year) + " - " + str(dateobj.tm_hour) + ":" + str(dateobj.tm_min) + ":" + str(dateobj.tm_sec)

