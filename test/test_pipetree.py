import enum
from rtan.pipetree import PipeTree

class TreeEnum(enum.Enum):
    start = 0
    cached = 1
    lookup = 2
    slow_lookup = 3
    insert = 4
    apply = 5

pt = PipeTree(
    state_enum=TreeEnum,
    calls={
        TreeEnum.start: lambda x: (TreeEnum.apply, x) if x % 4 == 0 else (TreeEnum.lookup, x),
        TreeEnum.lookup: lambda x: (TreeEnum.insert, x) if x % 3 == 0 else (TreeEnum.slow_lookup, x),
        TreeEnum.slow_lookup: lambda x: (TreeEnum.insert, x),
        TreeEnum.insert: lambda x: (TreeEnum.apply, x),
        TreeEnum.apply: lambda x: None,
    }
)

def test_pt_graph():
    mg = pt.graph(globals())
    assert set(mg.edges) == {
        (TreeEnum.start, TreeEnum.apply),
        (TreeEnum.start, TreeEnum.lookup),
        (TreeEnum.lookup, TreeEnum.insert),
        (TreeEnum.lookup, TreeEnum.slow_lookup),
        (TreeEnum.slow_lookup, TreeEnum.insert),
        (TreeEnum.insert, TreeEnum.apply),
        (TreeEnum.apply, None),
    }

def test_pt_check():
    # exercise-only
    pt.check_graph(globals())
