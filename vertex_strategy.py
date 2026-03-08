import json
import os
import re


def _target_from_risk(entry_price, stop_loss, signal_type):
    risk = abs(entry_price - stop_loss)
    points = min(max(1.5 * risk, 20.0), 35.0)
    if signal_type == "CALL":
        return round(entry_price + points, 2)
    return round(entry_price - points, 2)


def _extract_json_blob(text):
    if not text:
        return None

    fenced = re.search(r"```json\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)

    inline = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if inline:
        return inline.group(1)

    return None


def get_vertex_signal(df):
    """
    Return strategy signal using Vertex AI.
    Falls back to None on any error so caller can use manual strategy.
    """
    try:
        import vertexai
        from vertexai.generative_models import GenerativeModel
    except Exception as exc:
        print(f"⚠️ Vertex AI SDK unavailable: {exc}")
        return None

    project_id = os.environ.get("VERTEX_PROJECT_ID", "").strip()
    location = os.environ.get("VERTEX_LOCATION", "us-central1").strip()
    model_name = os.environ.get("VERTEX_MODEL", "gemini-1.5-flash-002").strip()
    min_confidence = float(os.environ.get("VERTEX_MIN_CONFIDENCE", "0.55"))

    if not project_id:
        print("⚠️ VERTEX_PROJECT_ID not configured")
        return None

    try:
        payload_df = df[
            ["open", "high", "low", "close", "volume", "EMA9", "EMA15", "RSI"]
        ].tail(25)
        payload = payload_df.round(2).to_dict(orient="records")
    except Exception as exc:
        print(f"⚠️ Failed to prepare Vertex payload: {exc}")
        return None

    prompt = (
        "You are a NIFTY intraday options strategy assistant.\n"
        "Analyze the latest OHLCV + indicators and return STRICT JSON only:\n"
        '{"signal_type":"CALL|PUT|NONE","confidence":0.0,"reason":"short"}\n'
        "Rules:\n"
        "- Use CALL for bullish momentum continuation.\n"
        "- Use PUT for bearish momentum continuation.\n"
        "- Use NONE when signal quality is low.\n"
        "- confidence must be between 0 and 1.\n"
        f"Candles: {json.dumps(payload)}"
    )

    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel(model_name)
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or ""
    except Exception as exc:
        print(f"⚠️ Vertex AI request failed: {exc}")
        return None

    json_blob = _extract_json_blob(raw_text)
    if not json_blob:
        print("⚠️ Vertex AI returned non-JSON output")
        return None

    try:
        result = json.loads(json_blob)
    except Exception as exc:
        print(f"⚠️ Vertex AI JSON parse error: {exc}")
        return None

    signal_type = str(result.get("signal_type", "NONE")).upper()
    confidence = float(result.get("confidence", 0.0))

    if signal_type not in {"CALL", "PUT"}:
        return None

    if confidence < min_confidence:
        print(f"ℹ️ Vertex AI confidence too low ({confidence:.2f})")
        return None

    latest = df.iloc[-1]
    entry_price = round(float(latest["close"]), 2)
    if signal_type == "CALL":
        stop_loss = round(min(float(latest["low"]), float(latest["EMA15"])), 2)
    else:
        stop_loss = round(max(float(latest["high"]), float(latest["EMA15"])), 2)

    return {
        "symbol": "NIFTY",
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target": _target_from_risk(entry_price, stop_loss, signal_type),
        "signal_type": signal_type,
        "source": "vertex_ai",
        "confidence": round(confidence, 2),
        "reason": str(result.get("reason", ""))[:160],
    }
