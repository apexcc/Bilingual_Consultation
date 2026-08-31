# Bilingual Consultation - Flask callback service

This repository contains a Flask-based callback service that accepts a voice message (MP3/ogg/m4a/wav), transcribes Traditional Chinese input, optionally uses an LLM for translation/understanding, and returns translated text plus a synthesized voice (MP3).

Features
- POST /callback accepts multipart/form-data with an `audio` file field.
- Supports local Whisper or OpenAI for ASR (configurable via env vars).
- Optional LLM translation/processing using OpenAI.
- TTS output using gTTS by default.

Quick start
1. Install system dependencies: ffmpeg
2. Create a virtualenv and install Python deps:
   pip install -r requirements.txt
3. Set environment variables as needed:
   - OPENAI_API_KEY (if using OpenAI)
   - ASR_BACKEND (whisper or openai)
   - LLM_BACKEND (openai or none)
4. Run:
   python app.py

Example request
curl -X POST "http://localhost:5000/callback" \
  -F "audio=@/path/to/input.mp3" \
  -F "input_lang=zh-TW" \
  -F "target_lang=en" \
  -F "use_llm=true"

Output JSON
- original_text: transcribed text (Traditional Chinese)
- translated_text: translated/processed text (English by default)
- voice_base64: base64-encoded mp3 of the TTS result

Notes
- For production, add authentication, input validation, background job processing, and better TTS providers if higher quality is required.
