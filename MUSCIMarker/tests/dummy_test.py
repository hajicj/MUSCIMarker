import unittest

def inc(x):
    return x + 1

class DummyTest(unittest.TestCase):
    def test_simple_increment(self):
        assert inc(4) == 5


if __name__ == '__main__':
    unittest.main()
