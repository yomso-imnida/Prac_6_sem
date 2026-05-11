import unittest
import sqroosrv

class TestRoot(unittest.TestCase):

    def test_1_answer(self):
        """1 answer."""
        self.assertEqual(sqroosrv.sqroots("1 2 1"), "-1.0")

    def test_0_answers(self):
        """0 answers."""
        self.assertEqual(sqroosrv.sqroots("1 2 3"), "")

    def test_2_answers(self):
        """2 answers."""
        self.assertEqual(sqroosrv.sqroots("1 0 -1"), "-1.0 1.0")

    def test_ZeroDivisionError(self):
        """First param is null."""
        self.assertEqual(sqroosrv.sqroots("0 1 2"), "")

    def test_ValueError(self):
        """Wrong params."""
        self.assertEqual(sqroosrv.sqroots("1"))
