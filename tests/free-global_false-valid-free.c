void free(void*);
int a = 5;
int main(void) {
	free(&a);
}
