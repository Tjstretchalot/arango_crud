import unittest
import helper  # noqa: F401
from arango_crud import (  # noqa: E402
    StepBackOffStrategy
)


class Test(unittest.TestCase):
    def test_step_back_off(self):
        steps = [0.1, 0.2, 0.5, 1]
        strat = StepBackOffStrategy(steps=steps)
        for idx, step in enumerate(steps):
            self.assertEqual(
                strat.get_back_off(idx + 1),
                step
            )
        self.assertIsNone(strat.get_back_off(len(steps) + 1))


if __name__ == '__main__':
    unittest.main()
