// warning: nothing works.

#include <stdio.h>
#include <string.h>
// function declaration
void *memcpy(void *str1, const void *str2, size_t n) //built in func. google it
char* StringSlice(char * str, size_t slice_start, size_t slice_end);
unsigned int* UnpackBlockToArray(char * block_bin); //int * var  ---> var is an array of ints. var[1], var[2]...
char* PackArrayToBlock(int block_arr[8]);
char* MineCoinAttempts(int my_wallet, int prev_block_bin, int start_num, int attempts_count);




int main() {




   /* my first program in C */
   printf("Hello, World! \n");
   
   return 0;

}



char * StringSlice(char *str_pos, size_t slice_start, size_t slice_end){
	char res[slice_end - slice_start];
	for(int i=0, i < slice_start, i++){
		res[i] = str[i];
	}
	res[i++] = \0;
	return &res;
}

unsigned int * UnpackBlockToArray(char * block_bin){
	unsigned int res[8];
	for(int i=0, i<8, i++){
		res[i] = StringSlice(block_bin, i*4, i*4+4);
	}
}

char * PackArrayToBlock(int block_arr[]){
	char * res;
	for(int i=0, ){
		strcat();
	}
}



/* int MineCoinAttempts(int my_wallet, int prev_block_bin, int start_num, int attempts_count){

	int prev_block = unpack(">LL8s4s12s", prev_block_bin)
	serial, w, prev_prev_sig, prev_puzzle, prev_sig = prev_block
	new_serial = serial + 1
	prev_half = prev_sig[:8]
	n_zeros = NumberOfZerosForPuzzle(new_serial)
	if start_num + attempts_count > 1 << 32: attempts_count = 1 << 32 - start_num
	for puzzle in utils.exrange(start_num, start_num + attempts_count):  // same as xrange but for numbers bigger than 32 bit (utils.py)
		# print new_serial, my_wallet, prev_half, puzzle
		block_bin = struct.pack(">LL8sL", new_serial, my_wallet, prev_half, puzzle)
		m = hashlib.md5()
		m.update(block_bin)
		sig = m.digest()
		if CheckSignature(sig, n_zeros):
			block_bin += sig[:12]
			return block_bin  # new block
	return None
*/
