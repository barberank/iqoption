# IQ Option AI Assistant — MVP

MVP inicial para conectar una cuenta de IQ Option en modo **PRACTICE**, descargar velas y preparar la base para análisis técnico, backtesting y una capa conversacional de IA.

> La integración utilizada es comunitaria y no oficial. Este proyecto debe probarse únicamente con la cuenta demo durante el desarrollo.

## Etapa actual

- Conexión a IQ Option.
- Selección forzada de cuenta `PRACTICE`.
- Lectura del saldo demo.
- Descarga de velas históricas.
- Exportación a `data/candles.csv`.
- Sin ejecución de operaciones.

## Requisitos

- Python 3.10 o 3.11.
- Git.
- Cuenta demo de IQ Option.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Configuración

Copiá `.env.example` como `.env` y completá tus credenciales:

```env
IQ_EMAIL=tu_email
IQ_PASSWORD=tu_contraseña
IQ_ASSET=EURUSD
IQ_TIMEFRAME=60
IQ_CANDLE_COUNT=100
```

No subas `.env` al repositorio.

## Ejecución

```bash
python main.py
```

El programa mostrará la conexión, el saldo demo, las últimas cinco velas y creará `data/candles.csv`.

## Próximas etapas

1. Indicadores técnicos.
2. Backtesting de estrategias.
3. Comparación y optimización de parámetros.
4. Asistente de IA en lenguaje natural.
5. Ejecución controlada exclusivamente en modo demo.
