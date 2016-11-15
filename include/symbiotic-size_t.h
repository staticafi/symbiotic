#ifndef _SYMBIOTIC_SIZE_H_
#define _SYMBIOTIC_SIZE_H_

#ifdef __cplusplus
extern "C" {
#endif

#ifdef __SIZE_TYPE__
typedef __SIZE_TYPE__ size_t;
#else
# if __WORDSIZE == 64
typedef unsigned long int size_t;
#else
typedef unsigned int size_t;
#endif
#endif

#ifdef __cplusplus
}
#endif

#endif /* _SYMBIOTIC_SIZE_H_ */
