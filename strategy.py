from dataclasses import dataclass
from typing import Optional, Dict, Any
from engine.indicators import TechnicalIndicators
from config import CONFIG
import pandas as pd


@dataclass
class TradeSignal:
    action: str          # "BUY", "SELL", "HOLD"
    price: float
    rsi: float
    ema_fast: float
    ema_slow: float
    reasoning: str       # Kararın insani/finansal gerekçesi
    confidence: float    # 0.0 - 1.0 aralığı güven skoru


class StrategyEngine:
    """
    RSI Aşırı Satım/Alım ve EMA Kesişim (Golden/Death Cross) teyitli
    akıllı karar motoru ve insan mantığında gerekçelendirici (Reasoning Engine).
    """

    def __init__(self):
        self.rsi_period = CONFIG.RSI_PERIOD
        self.ema_fast_period = CONFIG.EMA_FAST
        self.ema_slow_period = CONFIG.EMA_SLOW

    def evaluate(self, df_candles: pd.DataFrame, current_position: Optional[str] = None) -> TradeSignal:
        """
        Mum geçmişini analiz ederek aksiyon, metrikler ve açıklayıcı neden üretir.
        """
        if len(df_candles) < self.ema_slow_period + 2:
            return TradeSignal(
                action="HOLD",
                price=0.0,
                rsi=50.0,
                ema_fast=0.0,
                ema_slow=0.0,
                reasoning="Yetersiz mum verisi: İndikatörler henüz stabilize olmadı.",
                confidence=0.1
            )

        indicators = TechnicalIndicators.compute_all(
            df_candles,
            rsi_period=self.rsi_period,
            ema_fast=self.ema_fast_period,
            ema_slow=self.ema_slow_period
        )

        rsi = indicators["rsi"]
        ema_f = indicators["ema_fast"]
        ema_s = indicators["ema_slow"]
        prev_ema_f = indicators["prev_ema_fast"]
        prev_ema_s = indicators["prev_ema_slow"]
        current_price = float(df_candles["close"].iloc[-1])

        # Kesişim Mantığı
        golden_cross = (prev_ema_f <= prev_ema_s) and (ema_f > ema_s)
        death_cross = (prev_ema_f >= prev_ema_s) and (ema_f < ema_s)
        bullish_alignment = ema_f > ema_s
        bearish_alignment = ema_f < ema_s

        # 1. ALIM SENARYOSU (BUY)
        # Pozisyon yokken EMA Fast > Slow ve RSI aşırı alımda değil (< 65) VEYA RSI aşırı satımdan dönüyor (< 35)
        if current_position is None:
            if golden_cross and rsi < 65:
                return TradeSignal(
                    action="BUY",
                    price=current_price,
                    rsi=rsi,
                    ema_fast=ema_f,
                    ema_slow=ema_s,
                    reasoning=f"GÜÇLÜ BOĞA TEYİDİ: EMA({self.ema_fast_period}) yukarı kesişim (Golden Cross) gerçekleştirdi. RSI ({rsi:.1f}) aşırı alım bölgesinde değil, momentum yükselişi destekliyor.",
                    confidence=0.88
                )
            elif bullish_alignment and rsi < 35:
                return TradeSignal(
                    action="BUY",
                    price=current_price,
                    rsi=rsi,
                    ema_fast=ema_f,
                    ema_slow=ema_s,
                    reasoning=f"DİP TEPKİSİ ALIMI: Trend pozitif (EMA{self.ema_fast_period} > EMA{self.ema_slow_period}) ve RSI ({rsi:.1f}) aşırı satım bölgesinden sert dönüş sinyali veriyor.",
                    confidence=0.79
                )

        # 2. SATIM SENARYOSU (SELL)
        # Pozisyon LONG iken Death Cross ya da RSI tepe doyumuna (> 75) ulaşırsa
        if current_position == "LONG":
            if death_cross:
                return TradeSignal(
                    action="SELL",
                    price=current_price,
                    rsi=rsi,
                    ema_fast=ema_f,
                    ema_slow=ema_s,
                    reasoning=f"TREND ÇÖKÜŞÜ: EMA({self.ema_fast_period}) aşağı kesişim (Death Cross) yaptı. Hızlı hareketli ortalama desteği kırıldı, pozisyon kapatılıyor.",
                    confidence=0.92
                )
            elif rsi > 75:
                return TradeSignal(
                    action="SELL",
                    price=current_price,
                    rsi=rsi,
                    ema_fast=ema_f,
                    ema_slow=ema_s,
                    reasoning=f"AŞIRI ALIM KÂR REALİZASYONU: RSI ({rsi:.1f}) kritik 75 eşiğini aştı. Alıcı yorgunluğu ve olası düzeltme riskine karşı çıkış yapılıyor.",
                    confidence=0.85
                )

        # 3. BEKLEME SENARYOSU (HOLD)
        reason = "Piyasa bekleme modunda: Belirgin bir kesişim veya aşırı uç fiyatlama bulunmuyor."
        if bullish_alignment:
            reason = f"Boğa trendi sürüyor (EMA{self.ema_fast_period} > EMA{self.ema_slow_period}), RSI ({rsi:.1f}) dengeli bölgede; yeni aksiyon için kırılım bekleniyor."
        elif bearish_alignment:
            reason = f"Ayı baskısı devam ediyor (EMA{self.ema_fast_period} < EMA{self.ema_slow_period}), RSI ({rsi:.1f}); risk almamak için nakitte bekleniyor."

        return TradeSignal(
            action="HOLD",
            price=current_price,
            rsi=rsi,
            ema_fast=ema_f,
            ema_slow=ema_s,
            reasoning=reason,
            confidence=0.50
        )