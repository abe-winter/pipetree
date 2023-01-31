import dataclasses, enum, types, asyncio, warnings, collections, logging
from datetime import timedelta
from typing import Dict, Callable, TypeVar, Tuple, Any, Optional, NamedTuple, Iterable
from .rtan import typed_rets
from .minigraph import Minigraph

logger = logging.getLogger(__name__)

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
    # number of concurrent queues to allow for this type. reason to do this: you're hitting a resource that is slow but can be accessed in parallel
    concur: int = 1
    # passed to asyncio.Queue ctor
    maxsize: int = 0
    # rate limit
    limit: Limiter = dataclasses.field(default_factory=Limiter)
    # todo: error tolerance

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
        if ss.sources[0] != (firstkey := next(iter(self.calls))):
            raise ValueError(f"wanted graph source to match first dict key, they don't: {ss.sources[0]} vs {firstkey}")
        if (cycles := list(mg.cycles(ss))):
            raise ValueError(f"want zero cycles, got {cycles}")
        if len(self.state_enum) != len(self.calls):
            logger.debug(f"state length mismatch: %s %d vs %s %d", self.state_enum, len(self.state_enum), self.calls.keys(), len(self.calls))
            warnings.warn(f"state length mismatch -- see debug log for details")
            # todo: also warn on unused output states

    def create_queues(self):
        "return a dict of queues"
        return {key: asyncio.Queue() for key in calls}

    @classmethod
    async def proc(cls, key: PipeEnum, fn: callable, queues: asyncio.Queue(), counter: collections.Counter):
        "worker proc for each queue"
        queue = queues[key]
        is_async = asyncio.iscoroutinefunction(fn)
        try:
            while 1:
                item = await queue.get()
                raw = fn(item)
                ret = (await raw) if is_async else raw
                if ret is None:
                    dest = None
                else:
                    dest, val = ret
                    await queues[dest].put(val)
                counter[key, dest] += 1
                queue.task_done()
        except asyncio.CancelledError:
            pass

    @classmethod
    async def feed(cls, source: Iterable, queue: asyncio.Queue):
        for item in source:
            await queue.put(item)

    async def run(self, source: Iterable):
        # todo: consider using rxpy for the actual running
        if self.queues:
            raise NotImplementedError("sorry, we don't support QueueArgs yet")
        counter = collections.Counter()
        queues = {key: asyncio.Queue() for key in self.calls}
        procs = [
            self.proc(key, fn, queues, counter)
            for key, fn in self.calls.items()
        ]
        logger.info('starting %d procs', len(procs))
        bg = asyncio.gather(*procs)
        await self.feed(source, next(iter(queues.values())))
        logger.info('feed finished, waiting for downstream')
        while 1:
            await asyncio.gather(*(q.join() for q in queues.values()))
            if all(q.qsize() == 0 for q in queues.values()):
                logger.info('all queues synchronously 0, finished')
                break
        bg.cancel()
        try: await bg
        except asyncio.CancelledError:
            pass
        return counter
