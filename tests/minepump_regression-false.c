extern void __VERIFIER_error() __attribute__ ((__noreturn__));

extern int __VERIFIER_nondet_int(void);

void lowerWaterLevel(void) ;
void printPump(void) ;
int pumpRunning  =    0;
int systemActive  =    1;
int waterLevel  =    1;
int methaneLevelCritical  =    0;
void processEnvironment(void) ;
void changeMethaneLevel(void) ;
void stopSystem(void) ;
void timeShift(void) ;

void lowerWaterLevel(void) 
{
  if (waterLevel > 0)
    --waterLevel;
}

void waterRise(void)
{
  if (waterLevel < 2)
    ++waterLevel;
}

void __utac_acc__Specification4_spec__1(void)
{
  if (waterLevel) {
    if (pumpRunning)
      __VERIFIER_error();
  }
}

void timeShift(void)
{
  if (pumpRunning)
    lowerWaterLevel();

  if (systemActive)
    processEnvironment();

  __utac_acc__Specification4_spec__1();
}

int isHighWaterLevel(void)
{
  if (waterLevel < 2)
    return 0;
  else
    return 1;
}

void processEnvironment(void)
{
  if (! pumpRunning) {
    if (isHighWaterLevel())
      pumpRunning = 1;
  }
}

void stopSystem(void)
{
  if (pumpRunning)
    pumpRunning = 0;

  systemActive = 0;
}

void changeMethaneLevel(void)
{
}

void test(void)
{
  int splverifierCounter ;

  splverifierCounter = 0;
  while (1) {
    if (splverifierCounter >= 4)
	break;

    if (__VERIFIER_nondet_int())
      waterRise();

    if (__VERIFIER_nondet_int())
      changeMethaneLevel();

    if (__VERIFIER_nondet_int())
      stopSystem();

    timeShift();
  }
}

int main(void)
{
  test();
  return 0;
}

