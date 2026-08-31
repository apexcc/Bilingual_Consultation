import io
import base64
import wave

import app as app_module


def generate_silent_wav(duration_sec=1, framerate=16000):
    """Generate a silent WAV byte string (16-bit PCM, mono)."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(framerate)
        nframes = int(duration_sec * framerate)
        wf.writeframes(b'\x00\x00' * nframes)
    return buf.getvalue()


def test_callback_success(monkeypatch):
    wav = generate_silent_wav()

    # Monkeypatch heavy external functions to deterministic stubs
    monkeypatch.setattr(app_module, 'transcribe_with_whisper', lambda wav_bytes, input_language='zh': "測試中文")
    monkeypatch.setattr(app_module, 'translate_with_openai', lambda text, target_lang='en': "Test Chinese")
    monkeypatch.setattr(app_module, 'tts_gtts', lambda text, lang='en': b"FAKEMP3DATA")

    client = app_module.app.test_client()

    data = {
        'audio': (io.BytesIO(wav), 'test.wav'),
        'input_lang': 'zh-TW',
        'target_lang': 'en',
        'use_llm': 'true'
    }

    resp = client.post('/callback', data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    j = resp.get_json()
    assert j['original_text'] == "測試中文"
    assert j['translated_text'] == "Test Chinese"
    assert base64.b64decode(j['voice_base64']) == b"FAKEMP3DATA"
    assert j['success'] is True


def test_callback_no_file():
    client = app_module.app.test_client()
    resp = client.post('/callback', data={})
    assert resp.status_code == 400
    j = resp.get_json()
    assert j['success'] is False
