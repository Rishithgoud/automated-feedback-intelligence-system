import speech_recognition as sr
from pydub import AudioSegment
from langdetect import detect

def convert_voice_to_text(audio_path):
    recognizer = sr.Recognizer()

    # Convert to WAV if needed
    if audio_path.endswith(".mp3"):
        sound = AudioSegment.from_mp3(audio_path)
        audio_path = audio_path.replace(".mp3", ".wav")
        sound.export(audio_path, format="wav")

    with sr.AudioFile(audio_path) as source:
        audio = recognizer.record(source)

    try:
        # Auto language detection (Google handles this internally)
        text = recognizer.recognize_google(audio)
        language = detect(text)

        return text, language

    except:
        return "", "unknown"
