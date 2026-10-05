import logging
from typing import Dict, Any, Optional, Tuple
from config import CONFIG

logger = logging.getLogger("APEX.RiskManager")


class RiskManager:
    """
    Sermaye koruma kurallarını, dinamik Stop-Loss (%1.5),
    Take-Profit (%3.0) ve pozisyon büyüklüğü hesaplamalarını yönetir.
    """

    def __init__(
        self,
        stop_loss_pct: float = CONFIG.STOP_LOSS_PCT,
        take_profit_pct: float = CONFIG.TAKE_PROFIT_PCT,
        position_size_pct: float = CONFIG.POSITION_SIZE_PCT
    ):
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.position_size_pct = position_size_pct

    def calculate_position_order(self, current_cash: float, current_price: float) -> Tuple[float, float, float]:
        """
        Mevcut serbest nakde göre güvenli işlem büyüklüğünü, Stop-Loss ve Take-Profit fiyatlarını döner.
        Dönüş: (alınacak_miktar_btc, sl_fiyati, tp_fiyati)
        """
        if current_price <= 0 or current_cash <= 10.0:
            return 0.0, 0.0, 0.0

        usable_cash = current_cash * self.position_size_pct
        qty = round(usable_cash / current_price, 5)

        sl_price = round(current_price * (1.0 - self.stop_loss_pct), 2)
        tp_price = round(current_price * (1.0 + self.take_profit_pct), 2)

        return qty, sl_price, tp_price

    def check_exit_triggers(
        self, 
        entry_price: float, 
        current_price: float, 
        sl_price: float, 
        tp_price: float
    ) -> Tuple[bool, Optional[str], float]:
        """
        Fiyat hareketine göre Stop-Loss veya Take-Profit tetiklenmesini denetler.
        Dönüş: (tetiklendi_mi, cikis_sebebi, pnl_yuzdesi)
        """
        if entry_price <= 0:
            return False, None, 0.0

        pnl_pct = (current_price - entry_price) / entry_price

        # Stop-Loss Kontrolü
        if current_price <= sl_price:
            return (
                True, 
                f"STOP-LOSS TETİKLENDİ: Fiyat ({current_price:.2f}) SL seviyesini ({sl_price:.2f}) kırdı. Risk sınırı korundu.",
                pnl_pct
            )

        # Take-Profit Kontrolü
        if current_price >= tp_price:
            return (
                True, 
                f"TAKE-PROFIT GERÇEKLEŞTİ: Hedef fiyat ({tp_price:.2f}) vuruldu ({current_price:.2f}). Kâr realize edildi.",
                pnl_pct
            )

        return False, None, pnl_pct