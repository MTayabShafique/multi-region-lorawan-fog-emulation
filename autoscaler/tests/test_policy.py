import unittest

from policy import ScalingDecisionEngine, ScalingPolicy


class ScalingDecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.policy = ScalingPolicy(
            minimum_replicas=2,
            maximum_replicas=8,
            target_messages_per_second=20,
            scale_down_utilization=0.5,
            backlog_scale_up_threshold=10,
            scale_up_periods=2,
            scale_down_periods=3,
            scale_up_step=2,
            scale_down_step=1,
            cooldown_seconds=60,
        )
        self.engine = ScalingDecisionEngine(self.policy)

    def test_scale_up_requires_stabilization_and_limits_step(self):
        first = self.engine.evaluate("eu868", 2, 100, 0, now=0)
        second = self.engine.evaluate("eu868", 2, 100, 0, now=10)

        self.assertEqual(first.action, "hold")
        self.assertEqual(second.action, "scale_up")
        self.assertEqual(second.desired_replicas, 4)

    def test_backlog_triggers_scale_up(self):
        self.engine.evaluate("eu868", 2, 0, 10, now=0)
        decision = self.engine.evaluate("eu868", 2, 0, 10, now=10)

        self.assertEqual(decision.action, "scale_up")
        self.assertEqual(decision.desired_replicas, 3)

    def test_scale_down_is_slow_and_one_replica_at_a_time(self):
        self.engine.evaluate("eu868", 4, 5, 0, now=0)
        self.engine.evaluate("eu868", 4, 5, 0, now=10)
        decision = self.engine.evaluate("eu868", 4, 5, 0, now=20)

        self.assertEqual(decision.action, "scale_down")
        self.assertEqual(decision.desired_replicas, 3)

    def test_backlog_prevents_scale_down(self):
        for now in (0, 10, 20, 30):
            decision = self.engine.evaluate("eu868", 4, 0, 1, now=now)

        self.assertEqual(decision.action, "hold")
        self.assertEqual(decision.desired_replicas, 4)

    def test_cooldown_blocks_repeated_scaling(self):
        self.engine.evaluate("eu868", 2, 100, 0, now=0)
        self.engine.evaluate("eu868", 2, 100, 0, now=10)
        self.engine.record_successful_scale("eu868", now=10)
        decision = self.engine.evaluate("eu868", 4, 100, 0, now=20)

        self.assertEqual(decision.action, "hold")
        self.assertEqual(decision.reason, "cooldown")

    def test_policy_rejects_invalid_bounds(self):
        with self.assertRaises(ValueError):
            ScalingPolicy(minimum_replicas=3, maximum_replicas=2)


if __name__ == "__main__":
    unittest.main()
