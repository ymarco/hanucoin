import hashlib
import struct
import random

def Log2(n):
    """Log2(n) - how many times n can be be divided by2 before it is zero.
    >>> Log2(0)
    0
    >>> Log2(5)
    3
    """
    for i in xrange(32):
        # mask is i ones in binary
        # i==0  => mask==0b0
        # i==1  => mask==0b1
        # i==2  => mask==0b11
        mask = (1L << i) - 1
        if (n & mask) == n:
            return i
    return 99

g_puzzle_bits0 = 20  # put in a variable so we can make it lower for testing
def NumberOfZerosForPuzzle(block_serial_number):
    """Given a block serial number - how many zeros should be at the end of its signature
    >>> NumberOfZerosForPuzzle(1000)
    30
    """
    return g_puzzle_bits0 + Log2(block_serial_number)


def WalletCode(member_names_list):
    """Given list of the names of wallet owners - return a 32 bit number - wallet number.
    >>> WalletCode(["Foo Bar", "Bar Vaz"])
    3622990312
    """
    member_names_str = ",".join(sorted(member_names_list))
    m = hashlib.md5()
    m.update(member_names_str.lower())
    data = m.digest()
    # take lower 32 bit of member's name digest
    # Note - unpack returns a tuple of size 1 - we use [0] to get the number
    return struct.unpack(">L", data[:4])[0]

# Block is 32 byte/256bit long.
# record/block format:
# 32 bit serial number
# 32 bit wallet number
# 64 bit prev_sig[:8]highest bits  (first half ) of previous block's signature (including all the block)
# 32 bit puzzle answer
# 96 bit sig[:12] - md5 - the first 12 bytes of md5 of above fields. need to make last N bits zero

def CreateBlock0_TestStage():
    block0 = [0, 0, "BLOCKNUM", 2016330331, ""]
    m = hashlib.md5()
    block0_bin = struct.pack(">LL8sL", *block0[:4])
    m.update(block0_bin)
    block0_bin += m.digest()[:12]
    return block0_bin



def CheckSignature(sig, n_zeros): #used only in CheckBlockSignature()
    # check tha last n_zeros bits of signature.
    # look at them byte by bye (8 bits together)
    sig_index = 15  # look at last byte
    while n_zeros >= 8:
        b = ord(sig[sig_index])
        if b != 0:
            return False  # bad signature
        sig_index -= 1
        n_zeros -= 8 # we checked one byte
    if n_zeros == 0:
        return True  # this happens when n_zeros was divisible by 8
    mask = (1L << n_zeros) - 1
    b = ord(sig[sig_index])
    return (b & mask) == 0


def CheckBlockSignature(serial, wallet, prev_sig, puzzle, block_sig):
    """Given a block fields - check that signature is valid and puzzle is solved.
    return 0 if OK, reason for erro if not.
    """
    block_data = struct.pack(">LL8sL", serial, wallet, prev_sig, puzzle)
    m = hashlib.md5()
    m.update(block_data)
    sig = m.digest()
    # check sig has right number of zeros at the end
    n_zeros = NumberOfZerosForPuzzle(serial)
    if not CheckSignature(sig, n_zeros):
        return 4
    # check that the signature is part of the block
    if block_sig != sig[:12]:
        return 5
    return 0

def unpack_block_to_tuple(block_bin):#used only in other funcs
    return struct.unpack(">LL8sL12s", block_bin)

def IsValidBlock(prev_block_bin, block_bin):
    """Check if block_bin is valid given the previous block.
    return 0 if Block ok, a reason number if not.
    """
    prev_block = unpack_clock_to_tuple(prev_block_bin)
    block = unpack_clock_to_tuple(block_bin)
    return IsValidBlockUnpacked(prev_block, block)


def IsValidBlock(prev_block_bin, block_bin):
    """returns 0 if block is valid, else returns issue num: see below """
    block_tuple = unpack_block_to_tuple(block_bin)
    prev_block_tuple = unpack_block_to_tuple(prev_block_bin)
    # check serial number
    if block_tuple[0] != prev_block_tuple[0] + 1:
        return 1
    # check that not same wallet number
    if block_tuple[1] == prev_block_tuple[1]:
        return 2
    # check that new block contins part of prev block signature
    if block_tuple[2] != prev_block_tuple[4][:8]:
        return 3
    #calculate the signature for the block
    return CheckBlockSignature(*block_tuple)


def MineCoinAttempts(my_wallet, prev_block_bin, attempts_count):
    prev_block = unpack_block_to_tuple(prev_block_bin)
    serial, w, prev_prev_sig, prev_puzzle, prev_sig  = prev_block
    new_serial = serial + 1
    prev_half = prev_sig[:8]
    n_zeros = NumberOfZerosForPuzzle(new_serial)
    for try_puzzle in xrange(attempts_count):
        #print new_serial, my_wallet, prev_half, try_puzzle
        block_bin = struct.pack(">LL8sL", new_serial, my_wallet, prev_half, try_puzzle)
        m = hashlib.md5()
        m.update(block_bin)
        sig = m.digest()
        if CheckSignature(sig, n_zeros):
            block_bin += sig[:12]
            return block_bin # new block
    return None # could not find block in attempts_count

def MineCoin(my_wallet, prev_block_bin):
    new_block = None
    while not new_block:
        new_block = MineCoinAttempts(my_wallet, prev_block_bin, 10000)
    return new_block


def TestMining():
    prev_block = CreateBlock0_TestStage()
    wallet1 = WalletCode(["Tal Franji"])
    wallet2 = WalletCode(["Foo Bar"])
    for _ in xrange(1000):
        new_block = MineCoin(wallet1, prev_block)
        if IsValidBlock(prev_block, new_block) != 0:
            print "BAD"
            break
        print repr(prev_block)
        prev_block = new_block
        wallet1, wallet2 = wallet2, wallet1

#To test this module:
#TestMining()