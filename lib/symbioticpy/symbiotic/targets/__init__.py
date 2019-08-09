from . klee import SymbioticTool as KleeTool
from . ceagle import SymbioticTool as CeagleTool
from . cbmc import SymbioticTool as CbmcTool
from . ikos import SymbioticTool as IkosTool
from . map2check import SymbioticTool as Map2CheckTool
from . cpachecker import SymbioticTool as CpaTool
from . skink import SymbioticTool as SkinkTool
from . smack import SymbioticTool as SmackTool
from . seahorn import SymbioticTool as SeahornTool
from . nidhugg import SymbioticTool as NidhuggTool
from . divine import SymbioticTool as DivineTool
from . ultimateautomizer import SymbioticTool as UltimateTool
from . cc import CCTarget

targets = {
    'klee':               KleeTool,
    'ceagle':             CeagleTool,
    'ikos':               IkosTool,
    'cbmc':               CbmcTool,
    'map2check':          Map2CheckTool,
    'cpachecker':         CpaTool,
    'cpa':                CpaTool,
    'skink':              SkinkTool,
    'smack':              SmackTool,
    'seahorn':            SeahornTool,
    'nidhugg':            NidhuggTool,
    'divine':             DivineTool,
    'ultimateautomizer':  UltimateTool,
    'ultimate':           UltimateTool,
    'cc':                 CCTarget
}

