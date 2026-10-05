import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class TradingConfig:
    # Borsa & Sembol Ayarları
    SYMBOL: str = os.getenv("SYMBOL", "BTCUSDT")
    INTERVAL: str = os.getenv("INTERVAL", "1m")
    BINANCE_WS_URL: str = "wss://stream.binance.com:9443/ws"
    BINANCE_REST_URL: str = "https://api.binance.com"

    # API Kimlik Bilgileri (Canlı Mod İçin)
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET: str = os.getenv("BINANCE_API_SECRET", "")

    # Çalışma Modu
    SIMULATION_MODE: bool = os.getenv("SIMULATION_MODE", "True").lower() in ("true", "1", "yes")

    # Sanal Bakiye ve Komisyon Yapısı
    INITIAL_CASH_USDT: float = float(os.getenv("INITIAL_CASH_USDT", "10000.0"))
    COMMISSION_RATE: float = float(os.getenv("COMMISSION_RATE", "0.001"))  # %0.1 Standart Spot

    # İndikatör Periyotları
    RSI_PERIOD: int = int(os.getenv("RSI_PERIOD", "14"))
    EMA_FAST: int = int(os.getenv("EMA_FAST", "9"))
    EMA_SLOW: int = int(os.getenv("EMA_SLOW", "21"))

    # Risk Yönetimi Oranları
    STOP_LOSS_PCT: float = float(os.getenv("STOP_LOSS_PCT", "0.015"))       # %1.5 Zarar Kes
    TAKE_PROFIT_PCT: float = float(os.getenv("TAKE_PROFIT_PCT", "0.030"))    # %3.0 Kâr Al
    POSITION_SIZE_PCT: float = float(os.getenv("POSITION_SIZE_PCT", "0.95")) # Bakiyenin %95'i ile işlem

    # Sistem Tampon Boyutları
    CANDLE_BUFFER_SIZE: int = 500
    TELEMETRY_LOG_SIZE: int = 200

    # Sunucu Konfigürasyonu
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))


CONFIG = TradingConfig()