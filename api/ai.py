import json
import os

import pandas as pd
from flask import Flask, jsonify, request
from openai import OpenAI

from main import (
    add_indicators,
    calculate_signal,
    calculate_trend,
    candle_to_dict,
    connect_practice,
    download_candles,
    require_env,
)

app = Flask(__name__)


def build_market_context() -> dict:
    email = require_env("IQ_EMAIL")
    password = require_env("IQ_PASSWORD")
    asset = os.getenv("IQ_ASSET", "EURUSD").strip().upper()
    timeframe = int(os.getenv("IQ_TIMEFRAME", "60"))
    count = int(os.getenv("IQ_CANDLE_COUNT", "1000"))

    if count < 21 or count > 1000:
        raise ValueError("IQ_CANDLE_COUNT debe estar entre 21 y 1000")

    iq = connect_practice(email, password)
    frame = add_indicators(download_candles(iq, asset, timeframe, count))
    latest = frame.iloc[-1]
    signal, reason = calculate_signal(frame)

    return {
        "mode": "PRACTICE_ONLY",
        "execution_enabled": False,
        "asset": asset,
        "timeframe": timeframe,
        "count": len(frame),
        "balance": iq.get_balance(),
        "trend": calculate_trend(frame),
        "indicators": {
            "ema9": round(float(latest["ema9"]), 6),
            "ema21": round(float(latest["ema21"]), 6),
            "rsi14": None
            if pd.isna(latest["rsi14"])
            else round(float(latest["rsi14"]), 2),
        },
        "signal": {"value": signal, "reason": reason},
        "last_candle": candle_to_dict(latest),
        "last_20_candles": [
            candle_to_dict(row) for _, row in frame.tail(20).iterrows()
        ],
    }


def read_question() -> str:
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        question = str(payload.get("question", "")).strip()
    else:
        question = request.args.get(
            "question", "¿Entrarías ahora? Explicá por qué."
        ).strip()

    if not question:
        raise ValueError("Falta la pregunta")
    if len(question) > 1000:
        raise ValueError("La pregunta no puede superar 1000 caracteres")
    return question


@app.route("/", methods=["GET", "POST"])
@app.route("/api/ai", methods=["GET", "POST"])
def ai_analysis():
    try:
        api_key = require_env("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
        question = read_question()
        market = build_market_context()

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=model,
            store=False,
            instructions=(
                "Sos un analista cuantitativo para una cuenta demo de IQ Option. "
                "Analizá únicamente los datos recibidos. No prometas ganancias, no inventes "
                "datos y no afirmes que una señal garantiza un resultado. La ejecución está "
                "deshabilitada. Respondé en español, de forma clara y breve. Indicá siempre "
                "si tu conclusión es CALL, PUT o NO_TRADE y justificála."
            ),
            input=(
                f"Pregunta del usuario: {question}\n\n"
                f"Contexto de mercado JSON:\n{json.dumps(market, ensure_ascii=False)}"
            ),
        )

        return jsonify(
            {
                "status": "ok",
                "mode": "PRACTICE_ONLY",
                "execution_enabled": False,
                "model": model,
                "question": question,
                "analysis": response.output_text,
                "market": market,
            }
        )
    except ValueError as exc:
        return jsonify({"status": "error", "error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"status": "error", "error": str(exc)}), 500
