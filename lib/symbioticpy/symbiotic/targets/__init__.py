from . klee import SymbioticTool as KleeTool
from . witchklee import SymbioticTool as WitchKleeTool
from . ceagle import SymbioticTool as CeagleTool
from . cbmc import SymbioticTool as CbmcTool
from . cbmcsvcomp import SymbioticTool as CbmcSVCOMPTool
from . esbmc import SymbioticTool as EsbmcTool
from . ikos import SymbioticTool as IkosTool
from . map2check import SymbioticTool as Map2CheckTool
from . cpachecker import SymbioticTool as CpaTool
from . skink import SymbioticTool as SkinkTool
from . smack import SymbioticTool as SmackTool
from . seahorn import SymbioticTool as SeahornTool
from . nidhugg import SymbioticTool as NidhuggTool
from . divine import SymbioticTool as DivineTool
from . divinesvc import SymbioticTool as DivineSvcompTool
from . ultimateautomizer import SymbioticTool as UltimateTool
from . svcomp import SymbioticTool as SVCompTool
from . testcomp import SymbioticTool as TestCompTool
from . slowbeast import SymbioticTool as SlowbeastTool
from . predatorhp import SymbioticTool as PredatorHPTool
from . predator import SymbioticTool as PredatorTool
from . twols import SymbioticTool as TwolsTool
from . cc import CCTarget

targets = {
    'klee':               KleeTool,
    'witch-klee':         WitchKleeTool,
    'ceagle':             CeagleTool,
    'ikos':               IkosTool,
    'cbmc':               CbmcTool,
    'cbmc-svcomp':        CbmcSVCOMPTool,
    'esbmc':              EsbmcTool,
    'map2check':          Map2CheckTool,
    'cpachecker':         CpaTool,
    'cpa':                CpaTool,
    'skink':              SkinkTool,
    'smack':              SmackTool,
    'seahorn':            SeahornTool,
    'nidhugg':            NidhuggTool,
    'divine':             DivineTool,
    'divine-svcomp':      DivineSvcompTool,
    'ultimateautomizer':  UltimateTool,
    'ultimate':           UltimateTool,
    'uautomizer':         UltimateTool,
    'ua':                 UltimateTool,
    'svcomp':             SVCompTool,
    'testcomp':           TestCompTool,
    'slowbeast':          SlowbeastTool,
    'sb':                 SlowbeastTool,
    'predatorhp':         PredatorHPTool,
    'predator':           PredatorTool,
    '2ls':                TwolsTool,
    'cc':                 CCTarget
}

