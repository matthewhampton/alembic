from alembic.testing.fixtures import TestBase
from alembic.testing import eq_
from alembic.revision import RevisionMap, Revision


class DownwardsIterationTest(TestBase):
    def test_straight(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b', ('a',)),
                Revision('c', ('b',)),
            ]
        )

        eq_(
            [rev.revision for rev in map_._iterate_revisions("c", "a")],
            ["c", "b", "a"]
        )

    def test_diamond(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('c', ('b1', 'b2')),
                Revision('d', ('c',)),
            ]
        )

        eq_(
            [rev.revision for rev in map_.iterate_revisions("d", "a")],
            ["d", "c", "b1", "b2", "a"]
        )

    def test_many_branches(self):
        map_ = RevisionMap(
            lambda: [
                Revision('a', ()),
                Revision('b1', ('a',)),
                Revision('b2', ('a',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('d1cb1', ('cb1',)),
                Revision('d2cb1', ('cb1',)),
                Revision('d1cb2', ('cb2',)),
                Revision('d2cb2', ('cb2',)),
                Revision('d3cb2', ('cb2',)),
                Revision('d1d2cb2', ('d1cb2', 'd2cb2'))
            ]
        )
        eq_(
            [rev.revision for rev in map_._iterate_revisions("d1d2cb2", "a")],
            ['d1d2cb2', 'd1cb2', 'd2cb2', 'cb2', 'b2', 'a']
        )
        eq_(
            [rev.revision for rev in map_._iterate_revisions("d3cb2", "a")],
            ['d3cb2', 'cb2', 'b2', 'a']
        )

    def test_branch_travelling(self):
        """test the order of revs when going along multiple branches.

        We want depth-first along branches, but then we want to
        terminate all branches at their branch point before continuing
        to the nodes preceding that branch.

        """

        map_ = RevisionMap(
            lambda: [
                Revision('a1', ()),
                Revision('a2', ('a1',)),
                Revision('a3', ('a2',)),
                Revision('b1', ('a3',)),
                Revision('b2', ('a3',)),
                Revision('cb1', ('b1',)),
                Revision('cb2', ('b2',)),
                Revision('db1', ('cb1',)),
                Revision('db2', ('cb2',)),

                Revision('e1b1', ('db1',)),
                Revision('fe1b1', ('e1b1',)),

                Revision('e2b1', ('db1',)),
                Revision('e2b2', ('db2',)),
                Revision("merge", ('e2b1', 'e2b2'))
            ]
        )
        # here we want 'a3' as a "stop" branch point, but *not*
        # 'db1', as we don't have multiple traversals on db1
        eq_(
            [rev.revision for rev in map_._iterate_revisions("merge", "a1")],
            ['merge',
                'e2b1', 'db1', 'cb1', 'b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'a3',  # both terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )

        # in this case, both "a3" and "db1" are stop points
        eq_(
            [rev.revision for rev
             in map_._iterate_revisions(["merge", "fe1b1"], "a1")],
            ['merge',
                'e2b1',  # e2b1 branch
                'e2b2', 'db2', 'cb2', 'b2',  # e2b2 branch
                'fe1b1', 'e1b1',  # fe1b1 branch
                'db1',  # fe1b1 and e2b1 branches terminate at db1
                'cb1', 'b1',  # e2b1 branch continued....might be nicer
                              # if this was before the e2b2 branch...
                'a3',  # e2b1 and e2b2 branches terminate at a3
                'a2', 'a1'  # finish out
            ]  # noqa
        )