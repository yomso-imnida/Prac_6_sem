import unittest
import prog

class TestSome(unittest.TestCase):

    def test_normal(self):
        """Normal division."""
        self.assertEqual(prog.funct(1, 2), 1.5)
        self.assertEqual(prog.funct(1, 3), (1 / 9) * 12)

    def test_exception(self):
        """Zero division."""
        with self.assertRaises(ZeroDivisionError):
            prog.funct(1, 0)

    def test_untype(self):
        """Incorrect type."""
        with self.assertRaises(TypeError):
            prog.funct(1, 'ss')
