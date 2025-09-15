import gradio as gr
import random
import time
import os
import wave
import pyaudio
import threading
from datetime import datetime

recording = False
audio_frames = []
audio_stream = None
p = None


def start_recording():
    """Start audio recording"""
    global recording, audio_frames, audio_stream, p

    try:
        if recording:
            return "⚠️ Already recording! Stop current recording first."

        p = pyaudio.PyAudio()
        audio_frames = []
        recording = True

        # Audio settings
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 44100

        audio_stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        # Start recording in a separate thread
        def record_audio():
            while recording:
                try:
                    data = audio_stream.read(CHUNK)
                    audio_frames.append(data)
                except:
                    break

        recording_thread = threading.Thread(target=record_audio)
        recording_thread.daemon = True
        recording_thread.start()

        return "🎤 Recording started... Speak now!", "🔴 Currently Recording..."

    except Exception as e:
        return f"❌ Error starting recording: {str(e)}", "⏹️ Not Recording"


def stop_recording():
    """Stop audio recording and save the file"""
    global recording, audio_frames, audio_stream, p

    try:
        if not recording:
            return "⚠️ Not currently recording!"

        recording = False

        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
            audio_stream = None

        if audio_frames and len(audio_frames) > 0:
            # Create recordings directory if it doesn't exist
            os.makedirs("recordings", exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recordings/recording_{timestamp}.wav"

            # Save the audio file
            wf = wave.open(filename, "wb")
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(44100)
            wf.writeframes(b"".join(audio_frames))
            wf.close()

            # Clear the frames for next recording
            audio_frames = []

            if p:
                p.terminate()
                p = None

            return f"✅ Recording saved as: {filename}", "⏹️ Not Recording"
        else:
            return "❌ No audio data recorded", "⏹️ Not Recording"

    except Exception as e:
        return f"❌ Error stopping recording: {str(e)}", "⏹️ Not Recording"


def get_recording_status():
    """Get current recording status"""
    if recording:
        return "🔴 Currently Recording..."
    else:
        return "⏹️ Not Recording"


# Create the Gradio interface
with gr.Blocks(title="Shato Project", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 Shato Project")
    # gr.Markdown("Click the buttons below to see different interactive features!")
    with gr.Tab("Normal Interaction"):
        gr.Markdown("## Normal Interaction")
        gr.Markdown("How can I help you today?")

    with gr.Tab("Voice Interaction"):
        gr.Markdown("## 🎤 Voice Interaction")
        gr.Markdown("Interact with me! 😀")

        with gr.Row():
            with gr.Column():
                start_record_btn = gr.Button(
                    "🔴 Start Recording", variant="stop", size="lg"
                )
                stop_record_btn = gr.Button(
                    "⏹️ Stop Recording", variant="secondary", size="lg"
                )

                recording_status = gr.Textbox(
                    label="Recording Status", value="⏹️ Not Recording", interactive=False
                )

                recording_output = gr.Textbox(
                    label="Recording Result", lines=3, interactive=False
                )

            with gr.Column():
                gr.Markdown("### Instructions:")
                gr.Markdown(
                    """
                1. **Click "Start Recording"** to begin capturing audio
                2. **Speak clearly** into your microphone
                3. **Click "Stop Recording"** when you're done
                """
                )

                gr.Markdown("### Recording Settings:")
                gr.Markdown(
                    """
                - **Format**: WAV (uncompressed)
                - **Sample Rate**: 44.1 kHz
                - **Channels**: Mono
                - **Bit Depth**: 16-bit
                """
                )

        # Connect recording buttons
        start_record_btn.click(
            fn=start_recording, outputs=[recording_output, recording_status]
        )

        stop_record_btn.click(
            fn=stop_recording, outputs=[recording_output, recording_status]
        )

    with gr.Tab("About Us"):
        gr.Markdown(
            """
        ## About Us
        
        This is Shato Project. We add a mind to a robot through adding AI to think and respond to an interaction using voice or buttons.
        It's made by Group 1 (MIA Training)
        
        **Features:**
        - Interact throug buttons and text fields to enter the paramtars.
        - Voice interaction to use your voice instead of the first type.
        
        We hope you like this project.
        Thanks for reading❤️.
        """
        )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, debug=True)
