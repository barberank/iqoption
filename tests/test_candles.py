import unittest
from unittest.mock import Mock, patch

import pandas as pd

with patch.dict("sys.modules", {"iqoptionapi": Mock(), "iqoptionapi.stable_api": Mock()}):
    from main import download_candles


class DownloadCandlesTests(unittest.TestCase):
    def test_normalizes_and_sorts_candles(self):
        iq = Mock()
        iq.get_candles.return_value = [
            {
                "from": 200,
                "to": 260,
                "open": 1.2,
                "close": 1.3,
                "min": 1.1,
                "max": 1.4,
                "volume": 8,
            },
            {
                "from": 100,
                "to": 160,
                "open": 1.0,
                "close": 1.1,
                "min": 0.9,
                "max": 1.2,
                "volume": 5,
            },
        ]

        frame = download_candles(iq, "EURUSD", 60, 2)

        self.assertIsInstance(frame, pd.DataFrame)
        self.assertEqual(frame.iloc[0]["from"], 100)
        self.assertIn("low", frame.columns)
        self.assertIn("high", frame.columns)


if __name__ == "__main__":
    unittest.main()
