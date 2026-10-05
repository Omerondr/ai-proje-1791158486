from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseBroker(ABC):
    """
    Tüm borsa ve simülasyon ortamlarının uyması gereken soyut arayüz.
    """

    @abstractmethod
    async def get_balance(self) -> Dict[str, float]:
        """
        Mevcut serbest ve kilitli bakiyeleri döner: {'USDT': float, 'BTC': float}
        """
        pass

    @abstractmethod
    async def execute_order(self, symbol: str, side: str, quantity: float, price: float, reason: str) -> Dict[str, Any]:
        """
        Piyasa emri açar veya kapatır.
        """
        pass

    @abstractmethod
    def get_open_position(self) -> Optional[Dict[str, Any]]:
        """
        Açıkta duran aktif pozisyon bilgisini döner.
        """
        pass

    @abstractmethod
    def get_trade_history(self) -> List[Dict[str, Any]]:
        """
        Kapanmış ve icra edilmiş işlem defterini (ledger) döner.
        """
        pass

    @abstractmethod
    def get_portfolio_summary(self, current_price: float) -> Dict[str, Any]:
        """
        Portföy toplam değeri, net PnL ve bakiye özetini döner.
        """
        pass