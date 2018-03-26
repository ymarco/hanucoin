import itertools
def exrange(a,b=None):
	if b:
		return iter(itertools.count(a).next,b)
	return iter(itertools.count().next,a)