import asyncio
import json
import logging
from collections import deque
from typing import Callable, Optional, Dict, Any, List
import aiohttp
import pandas as pd
from config import CONFIG

logger = logging.getLogger("APEX.MarketData")


class MarketDataManager:
    """
    Binance WebSocket ve REST API veri akışını yönetir.
    Kopma durumlarında exponential-backoff ile otomatik yeniden bağlanır.
    """

    def __init__(self, on_candle_update: Optional[Callable[[Dict[str, Any]], Any]] = None):
        self.symbol = CONFIG.SYMBOL.lower()
        self.interval = CONFIG.INTERVAL
        self.ws_url = f"{CONFIG.BINANCE_WS_URL}/{self.symbol}@kline_{self.interval}"
        self.rest_url = f"{CONFIG.BINANCE_REST_URL}/api/v3/klines"
        self.on_candle_update = on_candle_update
        
        # Sabit hafızalı Ring-Buffer: Bellek sızıntısını engeller
        self.candle_buffer: deque = deque(maxlen=CONFIG.CANDLE_BUFFER_SIZE)
        self.is_running: bool = False
        self.last_candle: Optional[Dict[str, Any]] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def initialize_history(self) -> None:
        """
        WebSocket başlatılmadan önce REST API üzerinden geçmiş 100 mumu çeker
        ve indikatör tamponunu önceden doldurur (Warm-up fazı).
        """
        logger.info(f"Binance REST üzerinden {CONFIG.SYMBOL} geçmiş mumları çekiliyor...")
        params = {
            "symbol": CONFIG.SYMBOL.upper(),
            "interval": self.interval,
            "limit": 100
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.rest_url, params=params, timeout=10) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for item in data:
                            # [open_time, open, high, low, close, volume, close_time, ...]
                            candle = {
                                "timestamp": int(item[0]),
                                "open": float(item[1]),
                                "high": float(item[2]),
                                "low": float(item[3]),
                                "close": float(item[4]),
                                "volume": float(item[5]),
                                "is_closed": True
                            }
                            self.candle_buffer.append(candle)
                        if self.candle_buffer:
                            self.last_candle = self.candle_buffer[-1]
                        logger.info(f"Başlangıç için {len(self.candle_buffer)} adet mum yüklendi.")
                    else:
                        logger.warning(f"REST mum çekimi başarısız. HTTP Durum: {resp.status}")
        except Exception as e:
            logger.error(f"Geçmiş veri çekilirken hata oluştu: {str(e)}")

    def get_dataframe(self) -> pd.DataFrame:
        """
        Mevcut tamponu teknik analiz için Pandas DataFrame formatında sunar.
        """
        if not self.candle_buffer:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = pd.DataFrame(list(self.candle_buffer))
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        return df

    async def start_stream(self) -> None:
        """
        WebSocket bağlantısını başlatır ve exponential backoff ile canlı tutar.
        """
        self.is_running = True
        backoff_delay = 1
        max_backoff = 30

        await self.initialize_history()

        while self.is_running:
            try:
                logger.info(f"WebSocket bağlantısı kuruluyor: {self.ws_url}")
                async with aiohttp.ClientSession() as session:
                    self._session = session
                    async with session.ws_connect(self.ws_url, heartbeat=20.0) as ws:
                        logger.info("Binance WebSocket veri hattı BAŞARIYLA BAĞLANDI.")
                        backoff_delay = 1  # Başarılı bağlantıda backoff sıfırlanır

                        async for msg in ws:
                            if not self.is_running:
                                break

                            if msg.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(msg.data)
                                if "k" in payload:
                                    kline = payload["k"]
                                    candle = {
                                        "timestamp": int(kline["t"]),
                                        "open": float(kline["o"]),
                                        "high": float(kline["h"]),
                                        "low": float(kline["l"]),
                                        "close": float(kline["c"]),
                                        "volume": float(kline["v"]),
                                        "is_closed": bool(kline["x"])
                                    }
                                    
                                    # Tampon güncellemesi
                                    if self.candle_buffer and self.candle_buffer[-1]["timestamp"] == candle["timestamp"]:
                                        self.candle_buffer[-1] = candle
                                    else:
                                        self.candle_buffer.append(candle)

                                    self.last_candle = candle

                                    # Üst katman tetikleyici
                                    if self.on_candle_update:
                                        await self.on_candle_update(candle)

                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                logger.warning("WebSocket kapandı veya hata aldı.")
                                break

            except aiohttp.ClientConnectorError as ce:
                logger.error(f"Bağlantı hatası: {str(ce)}")
            except Exception as ex:
                logger.error(f"Beklenmeyen WebSocket hatası: {str(ex)}")

            if self.is_running:
                logger.warning(f"{backoff_delay} saniye içinde tekrar bağlanılıyor...")
                await asyncio.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, max_backoff)

    async def stop(self) -> None:
        """
        Veri akışını kontrollü şekilde sonlandırır.
        """
        self.is_running = False
        if self._session and not self._session.closed:
            await self._session.close()
        logger.info("Market veri akışı durduruldu.")