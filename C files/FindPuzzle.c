#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "md5.h"

int FindPuzzle(const char *base_str,int n_zeros,unsigned int puzzle_int,unsigned char *stop_flag){
	/*
    :param *base_str:
	:param n_zeros:
	:param puzzle_int:
	:param *stop_flag:

	:return:

    */
	char *puzzle = malloc(4);
	puzzle[4] = '\0';
	char sig[16];
	MD5_CTX obj;
	while (!*stop_flag){
		puzzle[0] = puzzle_int >> 24;
		puzzle[1] = (puzzle_int >> 16) & 0xFF;
		puzzle[2] = (puzzle_int >> 8) & 0xFF;
		puzzle[3] = puzzle_int & 0xFF; // puzzle=struct.pack(">I",puzzle_int)
		MD5_Init(&obj); // Clear hash
		MD5_Update(&obj, base_str, 16); // 16 Bytes to hash (full block - puzzle - signature)
		MD5_Update(&obj, puzzle, 4); // Update puzzle part
		MD5_Final(sig, &obj); // Output hash into sig
		puzzle_int++; // Increase puzzle_int, when it reaches the int cap it will overflow back to 0 (good for our slices)
		if (16 - strlen(sig) >= n_zeros/8 && !(sig[15 - n_zeros/8] & (1 << n_zeros%8) - 1)){ //If the signature is valid
			return puzzle;
		}
	}
}



