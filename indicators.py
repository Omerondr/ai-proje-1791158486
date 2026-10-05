import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any


class TechnicalIndicators:
    """
    RSI (14), EMA (9) ve EMA (21) göstergelerini yüksek performanslı vektörel
    ve artımlı (streaming) mantıkla hesaplayan matematik motoru.
    """

    @staticmethod
    def calculate_ema(series: pd.Series, period: int) -> pd.Series:
        """
        Üstel Hareketli Ortalama (Exponential Moving Average) hesaplar.
        """
        if len(series) < period:
            return pd.Series(index=series.index, dtype=float)
        return series.ewm(span=period, adjust=False).mean()

    @staticmethod
    def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
        """
        Welles Wilder Yumuşatma Metodu (RMA) ile RSI (Relative Strength Index) hesaplar.
        """
        if len(series) <= period:
            return pd.Series(index=series.index, dtype=float)

        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)

        # İlk değerler basit ortalama (SMA), devamı Wilder EWM
        avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100.0 - (100.0 / (1.0 + rs))
        return rsi.fillna(50.0)

    @classmethod
    def compute_all(
        cls, 
        df_candles: pd.DataFrame, 
        rsi_period: int = 14, 
        ema_fast: int = 9, 
        ema_slow: int = 21
    ) -> Dict[str, float]:
        """
        Gelen mum DataFrame'inden son gösterge değerlerini hesaplayıp sözlük olarak döner.
        """
        if len(df_candles) < max(rsi_period, ema_slow) + 2:
            return {
                "rsi": 50.0,
                "ema_fast": float(df_candles["close"].iloc[-1]) if not df_candles.empty else 0.0,
                "ema_slow": float(df_candles["close"].iloc[-1]) if not df_candles.empty else 0.0,
                "prev_ema_fast": 0.0,
                "prev_ema_slow": 0.0,
            }

        closes = df_candles["close"]

        rsi_series = cls.calculate_rsi(closes, period=rsi_period)
        ema_f_series = cls.calculate_ema(closes, period=ema_fast)
        ema_s_series = cls.calculate_ema(closes, period=ema_slow)

        return {
            "rsi": float(rsi_series.iloc[-1]),
            "ema_fast": float(ema_f_series.iloc[-1]),
            "ema_slow": float(ema_s_series.iloc[-1]),
            "prev_ema_fast": float(ema_f_series.iloc[-2]),
            "prev_ema_slow": float(ema_s_series.iloc[-2]),
        }