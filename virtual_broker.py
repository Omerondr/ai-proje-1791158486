import time
import logging
from typing import Dict, Any, List, Optional
from broker.base import BaseBroker
from config import CONFIG

logger = logging.getLogger("APEX.VirtualBroker")


class VirtualBroker(BaseBroker):
    """
    10.000 USDT sanal bakiye ve gerçekçi borsa kuralları (komisyon, slippage)
    ile emir icra eden test/simülasyon motoru.
    """

    def __init__(self, initial_cash: float = CONFIG.INITIAL_CASH_USDT, commission_rate: float = CONFIG.COMMISSION_RATE):
        self.initial_balance = initial_cash
        self.cash_usdt = initial_cash
        self.asset_btc = 0.0
        self.commission_rate = commission_rate

        self.open_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []

    async def get_balance(self) -> Dict[str, float]:
        return {
            "USDT": self.cash_usdt,
            "BTC": self.asset_btc
        }

    def get_open_position(self) -> Optional[Dict[str, Any]]:
        return self.open_position

    def get_trade_history(self) -> List[Dict[str, Any]]:
        return self.trade_history

    async def execute_order(self, symbol: str, side: str, quantity: float, price: float, reason: str) -> Dict[str, Any]:
        timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S")

        if side.upper() == "BUY":
            gross_cost = quantity * price
            commission = gross_cost * self.commission_rate
            total_required = gross_cost + commission

            if total_required > self.cash_usdt:
                # Bakiye yetersizse alınabilecek maksimum miktar
                max_cost = self.cash_usdt / (1.0 + self.commission_rate)
                quantity = round(max_cost / price, 5)
                gross_cost = quantity * price
                commission = gross_cost * self.commission_rate
                total_required = gross_cost + commission

            if quantity <= 0.00001:
                return {"status": "REJECTED", "reason": "Yetersiz nakit bakiye"}

            self.cash_usdt -= total_required
            self.asset_btc += quantity

            self.open_position = {
                "symbol": symbol,
                "side": "LONG",
                "entry_price": price,
                "quantity": quantity,
                "entry_time": timestamp_str,
                "reason": reason,
                "commission_paid": commission
            }

            order_record = {
                "order_id": f"SIM-BUY-{int(time.time()*1000)}",
                "time": timestamp_str,
                "symbol": symbol,
                "side": "BUY",
                "price": price,
                "quantity": quantity,
                "total": gross_cost,
                "commission": commission,
                "reason": reason,
                "pnl": 0.0,
                "pnl_pct": 0.0
            }
            logger.info(f"[SIMULASYON ALIM] {quantity} BTC @ {price:.2f} USDT | Komisyon: {commission:.2f} USDT")
            return {"status": "FILLED", "order": order_record}

        elif side.upper() == "SELL":
            if not self.open_position or self.asset_btc <= 0:
                return {"status": "REJECTED", "reason": "Satılacak aktif pozisyon yok"}

            quantity = self.asset_btc
            gross_proceeds = quantity * price
            commission = gross_proceeds * self.commission_rate
            net_proceeds = gross_proceeds - commission

            entry_price = self.open_position["entry_price"]
            net_pnl = net_proceeds - (quantity * entry_price + self.open_position["commission_paid"])
            pnl_pct = (net_pnl / (quantity * entry_price)) * 100.0

            self.cash_usdt += net_proceeds
            self.asset_btc = 0.0

            closed_order = {
                "order_id": f"SIM-SELL-{int(time.time()*1000)}",
                "time": timestamp_str,
                "symbol": symbol,
                "side": "SELL",
                "entry_price": entry_price,
                "price": price,
                "quantity": quantity,
                "total": gross_proceeds,
                "commission": commission + self.open_position["commission_paid"],
                "reason": reason,
                "pnl": round(net_pnl, 2),
                "pnl_pct": round(pnl_pct, 2)
            }

            self.trade_history.append(closed_order)
            self.open_position = None

            logger.info(f"[SIMULASYON SATIM] {quantity} BTC @ {price:.2f} USDT | Net PnL: {net_pnl:.2f} USDT (%{pnl_pct:.2f})")
            return {"status": "FILLED", "order": closed_order}

        return {"status": "REJECTED", "reason": "Geçersiz işlem yönü"}

    def get_portfolio_summary(self, current_price: float) -> Dict[str, Any]:
        asset_value = self.asset_btc * current_price
        total_equity = self.cash_usdt + asset_value
        total_net_pnl = total_equity - self.initial_balance
        total_net_pnl_pct = (total_net_pnl / self.initial_balance) * 100.0

        unrealized_pnl = 0.0
        unrealized_pnl_pct = 0.0
        if self.open_position and self.open_position["quantity"] > 0:
            entry_val = self.open_position["quantity"] * self.open_position["entry_price"]
            curr_val = self.open_position["quantity"] * current_price
            unrealized_pnl = curr_val - entry_val
            unrealized_pnl_pct = (unrealized_pnl / entry_val) * 100.0

        # Başarı oranı (Win Rate)
        wins = sum(1 for t in self.trade_history if t.get("pnl", 0) > 0)
        total_closed = len(self.trade_history)
        win_rate = (wins / total_closed * 100.0) if total_closed > 0 else 0.0

        return {
            "initial_balance": self.initial_balance,
            "cash_usdt": round(self.cash_usdt, 2),
            "asset_btc": round(self.asset_btc, 6),
            "asset_value_usdt": round(asset_value, 2),
            "total_equity": round(total_equity, 2),
            "total_net_pnl": round(total_net_pnl, 2),
            "total_net_pnl_pct": round(total_net_pnl_pct, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "unrealized_pnl_pct": round(unrealized_pnl_pct, 2),
            "win_rate": round(win_rate, 1),
            "total_trades": total_closed
        }