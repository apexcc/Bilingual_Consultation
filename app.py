from flask import Flask, request, jsonify
import os
import tempfile
import base64
from pydub import AudioSegment
from io import BytesIO

# Optional imports (import when used to avoid heavy startup cost)
# import whisper
# import openai
from gtts import gTTS

app = Flask(__name__)

# Configuration via environment variables
ASR_BACKEND = os.getenv("ASR_BACKEND", "whisper")  # "whisper" or "openai"
LLM_BACKEND = os.getenv("LLM_BACKEND", "openai")   # "openai" or "none"
TTS_BACKEND = os.getenv("TTS_BACKEND", "gtts")     # "gtts" or other
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", None)

# Helper: convert uploaded audio to WAV PCM 16k mono
def convert_to_wav_bytes(audio_file_bytes, input_format):
    audio = AudioSegment.from_file(BytesIO(audio_file_bytes), format=input_format)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    out_buf = BytesIO()
    audio.export(out_buf, format="wav")
    out_buf.seek(0)
    return out_buf.read()

# ASR: local Whisper (example) or OpenAI placeholder
def transcribe_with_whisper(wav_bytes, input_language="zh"):
    import whisper
    model = whisper.load_model("small")
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        tmp_path = tmp.name
    result = model.transcribe(tmp_path, language=input_language, task="transcribe")
    os.unlink(tmp_path)
    return result.get("text", "").strip()

def transcribe_with_openai(wav_bytes, input_language="zh"):
    import openai
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY env missing")
    openai.api_key = OPENAI_API_KEY
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_bytes)
        tmp.flush()
        tmp_path = tmp.name
    with open(tmp_path, "rb") as fh:
        # Adjust this call depending on the OpenAI SDK version you use
        transcript = openai.Audio.transcribe("gpt-4o-transcribe", fh, (('language', input_language),))
    os.unlink(tmp_path)
    return transcript.get("text", "").strip()

# LLM-based translation/understanding (optional)
def translate_with_openai(text, target_lang="en"):
    import openai
    openai.api_key = OPENAI_API_KEY
    system = "You are a translation assistant. Translate the user's input into the requested target language, keep it fluent and natural."
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Translate the following text to {target_lang}: {text}"},
    ]
    # ChatCompletion usage varies by SDK; this is an example compatible with older openai sdk
    resp = openai.ChatCompletion.create(model="gpt-4o-mini", messages=messages, max_tokens=1000)
    return resp["choices"][0]["message"]["content"].strip()

# TTS: simple gTTS usage
def tts_gtts(text, lang="en"):
    tts = gTTS(text=text, lang=lang)
    out_buf = BytesIO()
    tts.write_to_fp(out_buf)
    out_buf.seek(0)
    return out_buf.read()

@app.route("/callback", methods=["POST"])
def callback():
    """
    Expected POST multipart form:
      - audio: file (mp3/ogg/m4a/wav)
      - input_lang: optional (default zh-TW)
      - target_lang: optional (default en)
      - use_llm: optional "true"/"false" (default true)
    Returns JSON:
      { original_text, translated_text, voice_base64, voice_mime, success }
    """
    if "audio" not in request.files:
        return jsonify({"error": "no audio file sent", "success": False}), 400

    file = request.files["audio"]
    filename = file.filename or "upload"
    input_format = filename.rsplit(".", 1)[-1].lower() if "." in filename else "mp3"

    input_lang = request.form.get("input_lang", request.args.get("input_lang", "zh-TW"))
    target_lang = request.form.get("target_lang", request.args.get("target_lang", "en"))
    use_llm = request.form.get("use_llm", request.args.get("use_llm", "true")).lower() in ("1", "true", "yes")

    audio_bytes = file.read()
    try:
        wav_bytes = convert_to_wav_bytes(audio_bytes, input_format)
    except Exception as ex:
        return jsonify({"error": f"audio conversion failed: {ex}", "success": False}), 500

    # ASR
    try:
        if ASR_BACKEND == "whisper":
            lang_code = "zh" if input_lang.startswith("zh") else input_lang
            original_text = transcribe_with_whisper(wav_bytes, input_language=lang_code)
        elif ASR_BACKEND == "openai":
            original_text = transcribe_with_openai(wav_bytes, input_language=input_lang)
        else:
            return jsonify({"error": f"Unsupported ASR_BACKEND: {ASR_BACKEND}", "success": False}), 500
    except Exception as ex:
        return jsonify({"error": f"ASR failed: {ex}", "success": False}), 500

    # Translate / understand
    translated_text = original_text
    try:
        if use_llm and LLM_BACKEND == "openai":
            translated_text = translate_with_openai(original_text, target_lang=target_lang)
        else:
            if ASR_BACKEND == "whisper" and LLM_BACKEND == "none":
                import whisper
                model = whisper.load_model("small")
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp.write(wav_bytes); tmp.flush(); tpath = tmp.name
                res = model.transcribe(tpath, task="translate", language="zh")
                os.unlink(tpath)
                translated_text = res.get("text", "").strip()
            else:
                translated_text = original_text
    except Exception as ex:
        return jsonify({"error": f"Translation/LLM failed: {ex}", "success": False}), 500

    # TTS
    try:
        tts_lang = target_lang if target_lang in ("en", "zh", "zh-cn", "zh-tw", "zh-TW", "zh-CN") else target_lang
        tts_lang = "zh" if str(tts_lang).startswith("zh") else "en"
        voice_mp3 = tts_gtts(translated_text, lang=tts_lang)
        voice_b64 = base64.b64encode(voice_mp3).decode("ascii")
    except Exception as ex:
        return jsonify({"error": f"TTS failed: {ex}", "success": False}), 500

    resp = {
        "original_text": original_text,
        "translated_text": translated_text,
        "voice_base64": voice_b64,
        "voice_mime": "audio/mpeg",
        "success": True,
    }
    return jsonify(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
