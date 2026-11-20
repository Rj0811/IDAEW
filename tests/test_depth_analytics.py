import unittest

from src.iadew.depth_analytics import depth_metrics, liquidity_changes


class DepthAnalyticsTests(unittest.TestCase):
    def test_imbalance_and_spread(self):
        bids = [{"price": 100 - i, "quantity": 10} for i in range(20)]
        asks = [{"price": 101 + i, "quantity": 5} for i in range(20)]
        result = depth_metrics(bids, asks)
        self.assertEqual(result["best_bid"], 100)
        self.assertEqual(result["best_ask"], 101)
        self.assertEqual(result["spread"], 1)
        self.assertAlmostEqual(result["imbalance_5"], 33.333333, places=4)

    def test_liquidity_change_matches_price(self):
        before = [{"price": 100, "quantity": 20}]
        after = [{"price": 100, "quantity": 12}, {"price": 99, "quantity": 4}]
        changes = liquidity_changes(before, [], after, [])
        self.assertEqual(len(changes), 2)
        self.assertEqual(changes[0]["change_qty"], -8)
        self.assertEqual(changes[1]["change_qty"], 4)


if __name__ == "__main__":
    unittest.main()
