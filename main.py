import os
import sys
import time
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from iqoptionapi.stable_api import IQ_Option

load_dotenv()
app = Flask(__name__)


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Falta configurar {name} en las variables de entorno")
    return value


def connect_practice(email: str, password: str) -> IQ_Option:
    iq = IQ_Option(email, password)
    connected, reason = iq.connect()

    if not connected:
        raise RuntimeError(f"No se pudo conectar a IQ Option: {reason}")

    iq.change_balance("PRACTICE")

    if not iq.check_connect():
        raise RuntimeError("La conexión se perdió después de iniciar sesión")

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


def add_indicators(frame: pd.DataFrame) -> pd.DataFrame:
    if "close" not in frame.columns:
        raise RuntimeError("No existe la columna close para calcular indicadores")

    if len(frame) < 21:
        raise RuntimeError("Se necesitan al menos 21 velas para calcular los indicadores")

    result = frame.copy()
    close = pd.to_numeric(result["close"], errors="coerce")

    if close.isna().any():
        raise RuntimeError("Hay valores inválidos en los precios de cierre")

    result["ema9"] = close.ewm(span=9, adjust=False).mean()
    result["ema21"] = close.ewm(span=21, adjust=False).mean()

    delta = close.diff()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)
    average_gain = gains.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    average_loss = losses.ewm(alpha=1 / 14, adjust=False, min_periods=14).mean()
    relative_strength = average_gain / average_loss.replace(0, float("nan"))
    result["rsi14"] = 100 - (100 / (1 + relative_strength))

    return result


@app.get("/")
def home():
    return jsonify(
        {
            "status": "ok",
            "service": "IQ Option AI MVP",
            "mode": "PRACTICE_ONLY",
            "message": "API online. Usá /api/candles o /api/indicators.",
        }
    )


@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "mode": "PRACTICE_ONLY"})


@app.get("/api/candles")
def candles_api():
    try:
        email = require_env("IQ_EMAIL")
        password = require_env("IQ_PASSWORD")
        asset = request.args.get("asset", os.getenv("IQ_ASSET", "EURUSD")).strip().upper()
        timeframe = int(request.args.get("timeframe", os.getenv("IQ_TIMEFRAME", "60")))
        count = int(request.args.get("count", os.getenv("IQ_CANDLE_COUNT", "100")))

        if timeframe not in {5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600}:
            return jsonify({"status": "error", "error": "Timeframe no permitido"}), 400

        if count < 1 or count > 1000:
            return jsonify({"status": "error", "error": "count debe estar entre 1 y 1000"}), 400

        iq = connect_practice(email, password)
        frame = download_candles(iq, asset, timeframe, count)
        records = frame.assign(datetime=frame["datetime"].astype(str)).to_dict(orient="records")

        return jsonify(
            {
                "status": "ok",
                "mode": "PRACTICE_ONLY",
                "asset": asset,
                "timeframe": timeframe,
                "count": len(records),
                "balance": iq.get_balance(),
                "candles": records,
            }
        )
    except ValueError:
        return jsonify({"status": "error", "error": "Parámetros numéricos inválidos"}), 400
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


@app.get("/api/indicators")
def indicators_api():
    try:
        email = require_env("IQ_EMAIL")
        password = require_env("IQ_PASSWORD")
        asset = request.args.get("asset", os.getenv("IQ_ASSET", "EURUSD")).strip().upper()
        timeframe = int(request.args.get("timeframe", os.getenv("IQ_TIMEFRAME", "60")))
        count = int(request.args.get("count", os.getenv("IQ_CANDLE_COUNT", "1000")))

        if timeframe not in {5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600}:
            return jsonify({"status": "error", "error": "Timeframe no permitido"}), 400

        if count < 21 or count > 1000:
            return jsonify({"status": "error", "error": "count debe estar entre 21 y 1000"}), 400

        iq = connect_practice(email, password)
        frame = add_indicators(download_candles(iq, asset, timeframe, count))
        latest = frame.iloc[-1]

        return jsonify(
            {
                "status": "ok",
                "mode": "PRACTICE_ONLY",
                "asset": asset,
                "timeframe": timeframe,
                "count": len(frame),
                "datetime": str(latest["datetime"]),
                "close": round(float(latest["close"]), 6),
                "ema9": round(float(latest["ema9"]), 6),
                "ema21": round(float(latest["ema21"]), 6),
                "rsi14": None if pd.isna(latest["rsi14"]) else round(float(latest["rsi14"]), 2),
            }
        )
    except ValueError:
        return jsonify({"status": "error", "error": "Parámetros numéricos inválidos"}), 400
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500


def run_cli() -> int:
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

    frame = download_candles(iq, asset, timeframe, count)
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / "candles.csv"
    frame.to_csv(output_file, index=False)

    print(frame.tail(5).to_string(index=False))
    print(f"Archivo creado: {output_file.resolve()}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(run_cli())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
