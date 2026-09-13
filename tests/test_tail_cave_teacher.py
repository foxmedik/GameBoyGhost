import unittest

from gameboy_agent.tail_cave_teacher import BeetleTeacher
from gameboy_agent.tail_cave_recovery import DisengagingBeetleTeacher


class BeetleTeacherTests(unittest.TestCase):
    def test_right_wall_pin_disengages_left_with_shield(self):
        teacher = DisengagingBeetleTeacher()
        state = {'x': 151, 'y': 80}
        targets = [{'x': 154, 'y': 80}]
        self.assertEqual((['left', 'b'], 3), teacher.action(state, targets))

    def test_open_space_keeps_standard_teacher(self):
        state = {'x': 120, 'y': 80}
        targets = [{'x': 154, 'y': 80}]
        self.assertEqual(BeetleTeacher().action(state, targets),
                         DisengagingBeetleTeacher().action(state, targets))

    def test_shields_while_approaching_stance(self):
        teacher=BeetleTeacher()
        action,frames=teacher.action({'x':147,'y':67},[{'x':126,'y':57}])
        self.assertEqual((action,frames),(['down','b'],1))

    def test_close_swing_is_a_three_command_sequence(self):
        teacher=BeetleTeacher();state={'x':147,'y':67};targets=[{'x':140,'y':64}]
        self.assertEqual(teacher.action(state,targets),(['left'],1))
        self.assertEqual(teacher.action(state,targets),(['a'],10))
        self.assertEqual(teacher.action(state,targets),([],3))

    def test_aligned_stance_pushes_toward_top_pit(self):
        teacher=BeetleTeacher();state={'x':126,'y':81};targets=[{'x':126,'y':57}]
        self.assertEqual(teacher.action(state,targets),(['up'],1))


if __name__=='__main__':unittest.main()
