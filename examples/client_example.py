"""Simple example client that uploads an audio file to the /callback endpoint.

Usage:
  python examples/client_example.py /path/to/input.mp3

It prints the original and translated texts and saves the returned MP3 to out.mp3.
"""
import sys
import requests
import base64


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/client_example.py /path/to/input.mp3")
        return

    filepath = sys.argv[1]
    url = "http://localhost:5000/callback"
    files = {"audio": open(filepath, "rb")}
    data = {"input_lang": "zh-TW", "target_lang": "en", "use_llm": "true"}

    r = requests.post(url, files=files, data=data)
    r.raise_for_status()
    j = r.json()
    print("Original:", j.get("original_text"))
    print("Translated:", j.get("translated_text"))

    b64 = j.get("voice_base64")
    if b64:
        with open("out.mp3", "wb") as fh:
            fh.write(base64.b64decode(b64))
        print("Saved out.mp3")


if __name__ == "__main__":
    main()
