#include <stdio.h>
#include <string.h>
#include "md5.h"

int FindPuzzle(const char* base_str,int n_zeros,unsigned int puzzle_int,unsigned char *stop_flag){
	char puzzle[4];
	char sig[16];
	MD5_CTX obj;
	while (!*stop_flag){
		puzzle[4] = {puzzle_num>>24,(puzzle_num>>16)&0xFF,(puzzle_num>>8)&0xFF,puzzle_num&0xFF,'\0'} // puzzle=struct.pack(">I",puzzle_int)
		MD5_Init(&obj); // Clear hash
		MD5_Update(&obj, base_str, 16); // 16 Bytes to hash (full block - puzzle - signature)
		MD5_Update(&obj, puzzle, 4); // Update puzzle part
		MD5_Final(sig, &obj); // Output hash into sig
		puzzle_int++; // Increase puzzle_int, when it will reach the int cap it will overflow back to 0 (good for our slices)
		if (16-strlen(sig) >= n_zeros/8 && !(sig[15 - n_zeros/8] & (1 << n_zeros%8)-1)){ //If the signature is valid
			return puzzle;
		}



	}
}



