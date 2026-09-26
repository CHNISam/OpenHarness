import unittest

class DeploymentNegative(unittest.TestCase):
    def test_intentional_rejection(self):
        self.fail("Deliberately invalid deployment candidate")
