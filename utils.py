import itertools, time


def exrange(a, b=None):  # Extended xrange, bypasses the limit of xrange(n) (n < 2**31-1)
	if b:
		return iter(itertools.count(a).next, b)
	return iter(itertools.count().next, a)


def strAddress(addr_tup):  # Converts an address tuple into a string e.g. (v)
	return addr_tup[0] + ":" + str(addr_tup[1])


def stdDate(secs):
	date_obj = time.gmtime(secs)
	return "%s/%s/%s - %s:%s:%s" % (str(date_obj.tm_mday), str(date_obj.tm_mon), str(date_obj.tm_year), str(date_obj.tm_hour), str(date_obj.tm_min), str(date_obj.tm_sec))


def addStrToTupList(tuple_list, string):
	for Tup in tuple_list:
		yield (Tup[0], Tup[1], string)