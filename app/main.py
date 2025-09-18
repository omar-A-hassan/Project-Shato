from fastapi import FastAPI
import sounddevice as sd
import wavio
import whisper
import threading
import numpy as np

app = FastAPI()

samplerate = 16000
channels = 1
filename = "recorded_audio.wav"

recording = False
frames = []
thread = None

def record_audio():
    global recording, frames
    with sd.InputStream(samplerate=samplerate, channels=channels, dtype='int16') as stream:
        while recording:
            data, _ = stream.read(1024)
            frames.append(data)

def save_audio():
    global frames
    audio_np = np.concatenate(frames, axis=0)  
    wavio.write(filename, audio_np, samplerate, sampwidth=2)
    print(f"Saved: {filename}")

def transcribe():
    model = whisper.load_model("base")
    result = model.transcribe(filename, language="en")
    return result["text"]

@app.post("/start")
def start_recording():
    global recording, frames, thread
    frames = []
    recording = True
    thread = threading.Thread(target=record_audio)
    thread.start()
    return {"status": "recording_started"}

@app.post("/stop")
def stop_recording():
    global recording, thread
    recording = False
    thread.join()
    save_audio()
    text = transcribe()
    return {"status": "recording_stopped", "transcription": text}
@app.get("/health")
def health():
    return {"status": "ok"}
