import dataclasses, enum, types
from datetime import timedelta
from typing import Dict, Callable, TypeVar, Tuple, Any, Optional, NamedTuple, Iterable
from .rtan import typed_rets
from .minigraph import Minigraph

@dataclasses.dataclass
class Limiter:
    "rate limit spec + state; warning none of this works"
    n_per_denom: Optional[int] = None
    denom: Optional[timedelta] = timedelta(seconds=1)
    min_time: Optional[timedelta] = None

    def maybe_sleep(self):
        raise NotImplementedError

@dataclasses.dataclass
class QueueArgs:
    # number of concurrent queues to allow for this type
    concur: int = 1
    # rate limit
    limit: Limiter = dataclasses.field(default_factory=Limiter)


PipeEnum = TypeVar('PipeEnum', bound=enum.Enum)
@dataclasses.dataclass
class PipeTree:
    "work manager that pipelines objects through a dag of queues"
    # allowable states of the items
    state_enum: PipeEnum
    # state -> callable
    calls: Dict[PipeEnum, Callable[[Any], Tuple[PipeEnum, Any]]]
    # per-queue config overrides; optional
    queues: Dict[PipeEnum, QueueArgs] = dataclasses.field(default_factory=dict)

    def graph(self, mod: types.ModuleType):
        "make graph from calls"
        # todo: detect undeclared returns (i.e. implicit discards)
        edges = []
        for state, fn in self.calls.items():
            for ret in typed_rets(fn, mod):
                if ret is not None and not (isinstance(ret, tuple) and isinstance(ret[0], self.state_enum)):
                    raise TypeError(f"unhandled ret in {fn}. wanted None or tuple with first elt a {self.state_enum}, got {ret}")
                edges.append((state, ret and ret[0]))
        return Minigraph(edges)

    def check_graph(self, globals_):
        "make sure this is a dag we can deal with"
        mg = self.graph(globals_)
        ss = mg.source_sink()
        if len(ss.sources) != 1:
            raise ValueError(f"want exactly one source, got {len(ss.sources)}")
        if (cycles := list(mg.cycles(ss))):
            raise ValueError(f"want zero cycles, got {cycles}")
