from pipetree.minigraph import Minigraph, SourceSink, Degree

mg = Minigraph([('x', 'y')])
cyclic = Minigraph([
    ('a', 'b'),
    ('b', 'c'),
    ('c', 'd'),
    ('c', 'b'),
])
cyc2 = Minigraph(['xy', 'yy'])
converge = Minigraph([
    ('a', 'b'),
    ('a', 'c'),
    ('b', 'd'),
    ('c', 'd'),
])

def test_degree():
    assert set(mg.degrees()) == {Degree('x', 0, 1), Degree('y', 1, 0)}
    assert mg.source_sink() == SourceSink(['x'], ['y'])

def test_outlinks():
    assert mg.outlinks() == {'x': ['y']}

def test_cycles():
    assert not list(mg.cycles())
    assert list(cyclic.cycles()) == [('b', 'c', 'b')]
    assert not list(converge.cycles())
    assert list(cyc2.cycles()) == [('y', 'y')]

def test_to_dot():
    # exercise-only
    mg.to_dot()
    cyclic.to_dot()
