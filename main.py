import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from iqoptionapi.stable_api import IQ_Option


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta configurar {name} en el archivo .env")
    return value


def connect_practice(email: str, password: str) -> IQ_Option:
    iq = IQ_Option(email, password)
    connected, reason = iq.connect()

    if not connected:
        raise RuntimeError(f"No se pudo conectar a IQ Option: {reason}")

    iq.change_balance("PRACTICE")

    if not iq.check_connect():
        raise RuntimeError("La conexión se perdió después de iniciar sesión.")

    return iq


def download_candles(
    iq: IQ_Option,
    asset: str,
    timeframe: int,
    count: int,
) -> pd.DataFrame:
    candles = iq.get_candles(asset, timeframe, count, time.time())

    if not candles:
        raise RuntimeError(
            f"IQ Option no devolvió velas para {asset}. "
            "Verificá que el activo esté disponible."
        )

    frame = pd.DataFrame(candles)
    frame["datetime"] = pd.to_datetime(frame["from"], unit="s", utc=True)
    frame = frame.rename(columns={"min": "low", "max": "high"})

    wanted = [
        column
        for column in [
            "datetime",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "from",
            "to",
        ]
        if column in frame.columns
    ]
    return frame[wanted].sort_values("datetime")


def main() -> int:
    load_dotenv()

    email = require_env("IQ_EMAIL")
    password = require_env("IQ_PASSWORD")
    asset = os.getenv("IQ_ASSET", "EURUSD").strip().upper()
    timeframe = int(os.getenv("IQ_TIMEFRAME", "60"))
    count = int(os.getenv("IQ_CANDLE_COUNT", "100"))

    print("Conectando a IQ Option...")
    iq = connect_practice(email, password)

    print("Conexión correcta.")
    print("Cuenta seleccionada: PRACTICE")
    print(f"Saldo demo: {iq.get_balance()}")
    print(f"Descargando {count} velas de {asset}, timeframe {timeframe}s...")

    frame = download_candles(iq, asset, timeframe, count)

    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "candles.csv"
    frame.to_csv(output_file, index=False)

    print("\nÚltimas 5 velas:")
    print(frame.tail(5).to_string(index=False))
    print(f"\nArchivo creado: {output_file.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
