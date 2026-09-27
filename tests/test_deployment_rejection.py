"""Disposable native denial probe. This branch must never be integrated."""

import unittest


class NativeDenialProbe(unittest.TestCase):
    def test_intentional_candidate_failure(self):
        self.fail('Intentional Issue #36 native negative deployment probe')
