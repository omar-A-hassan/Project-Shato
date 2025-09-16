import gradio as gr
import random
import time
import os
import wave
import pyaudio
import threading
import requests
import base64
import io
import uuid
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Service URLs from environment variables
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://localhost:8001")
STT_URL = os.getenv("STT_URL", "http://localhost:8003")  # Reserved for future STT integration
TTS_URL = os.getenv("TTS_URL", "http://localhost:8004")

logger.info(f"[UI-SERVICE] Orchestrator URL: {ORCHESTRATOR_URL}")
logger.info(f"[UI-SERVICE] TTS URL: {TTS_URL}")
logger.info(f"[UI-SERVICE] STT URL: {STT_URL} (reserved for future)")

# Global recording variables
recording = False
audio_frames = []
audio_stream = None
p = None

def start_recording():
    """Start audio recording"""
    global recording, audio_frames, audio_stream, p

    try:
        if recording:
            return "⚠️ Already recording! Stop current recording first.", "🔴 Currently Recording..."

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
        logger.error(f"[UI-SERVICE-ERROR] Error starting recording: {str(e)}")
        return f"❌ Error starting recording: {str(e)}", "⏹️ Not Recording"

def stop_recording():
    """Stop audio recording and save the file"""
    global recording, audio_frames, audio_stream, p

    try:
        if not recording:
            return "⚠️ Not currently recording!", "⏹️ Not Recording", None

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

            return f"✅ Recording saved as: {filename}", "⏹️ Not Recording", filename
        else:
            return "❌ No audio data recorded", "⏹️ Not Recording", None

    except Exception as e:
        logger.error(f"[UI-SERVICE-ERROR] Error stopping recording: {str(e)}")
        return f"❌ Error stopping recording: {str(e)}", "⏹️ Not Recording", None

def process_text_input(text_input):
    """Process text input through the orchestrator"""
    if not text_input.strip():
        return "❌ Please enter some text", None, "No response"

    try:
        correlation_id = str(uuid.uuid4())[:8]
        
        logger.info("ui_text_request", extra={
            "correlation_id": correlation_id,
            "user_input": text_input,
            "service": "ui-service"
        })

        # Send to orchestrator
        response = requests.post(
            f"{ORCHESTRATOR_URL}/process",
            json={
                "user_input": text_input,
                "correlation_id": correlation_id
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            response_text = data.get("response", "No response from system")
            command = data.get("command")
            
            # Log the response
            logger.info("ui_orchestrator_response", extra={
                "correlation_id": correlation_id,
                "response": response_text,
                "command": command,
                "service": "ui-service"
            })
            
            # Generate TTS audio
            audio_file = generate_tts_audio(response_text, correlation_id)
            
            return response_text, audio_file, response_text
        else:
            error_msg = f"❌ Orchestrator error: {response.status_code}"
            logger.error(f"[UI-SERVICE-ERROR] {error_msg}")
            return error_msg, None, "Error occurred"
            
    except requests.exceptions.RequestException as e:
        error_msg = f"❌ Connection error: {str(e)}"
        logger.error(f"[UI-SERVICE-ERROR] {error_msg}")
        return error_msg, None, "Connection error"
    except Exception as e:
        error_msg = f"❌ Unexpected error: {str(e)}"
        logger.error(f"[UI-SERVICE-ERROR] {error_msg}")
        return error_msg, None, "Unexpected error"

def generate_tts_audio(text, correlation_id):
    """Generate TTS audio from text response"""
    try:
        logger.info(f"[UI-SERVICE] Generating TTS audio correlation_id={correlation_id}")
        
        response = requests.post(
            f"{TTS_URL}/synthesize",
            json={
                "text": text,
                "correlation_id": correlation_id
            },
            timeout=None
        )
        
        if response.status_code == 200:
            data = response.json()
            audio_base64 = data.get("audio_data", "")
            
            if audio_base64:
                # Decode base64 audio and save to temporary file
                audio_data = base64.b64decode(audio_base64)
                os.makedirs("tts_audio", exist_ok=True)
                audio_filename = f"tts_audio/response_{correlation_id}.wav"
                
                with open(audio_filename, "wb") as f:
                    f.write(audio_data)
                
                logger.info(f"[UI-SERVICE] TTS audio saved: {audio_filename}")
                return audio_filename
        else:
            logger.error(f"[UI-SERVICE-ERROR] TTS error: {response.status_code}")
            
    except Exception as e:
        logger.error(f"[UI-SERVICE-ERROR] TTS generation failed: {str(e)}")
    
    return None

def process_voice_recording(audio_file_path):
    """Process voice recording (STT placeholder + orchestrator + TTS)"""
    if not audio_file_path:
        return "❌ No audio file provided", None, "No audio"
    
    try:
        # STT PLACEHOLDER - For now, return placeholder text
        # TODO: Integrate with STT service when available
        placeholder_text = "Hello SHATO, move to position 5 and 7"
        
        logger.info(f"[UI-SERVICE] Processing voice recording: {audio_file_path}")
        logger.info(f"[UI-SERVICE] STT PLACEHOLDER - Using text: {placeholder_text}")
        
        # Process through orchestrator (same as text input)
        result_text, audio_response, response_text = process_text_input(placeholder_text)
        
        # Add STT placeholder info to response
        full_result = f"🎤 Voice Input (STT Placeholder): {placeholder_text}\n\n{result_text}"
        
        return full_result, audio_response, response_text
        
    except Exception as e:
        error_msg = f"❌ Voice processing error: {str(e)}"
        logger.error(f"[UI-SERVICE-ERROR] {error_msg}")
        return error_msg, None, "Voice processing error"

# Create the Gradio interface
with gr.Blocks(title="SHATO Project", theme=gr.themes.Soft()) as demo:
    gr.Markdown("# 🤖 SHATO Voice-Controlled Robot Assistant")
    gr.Markdown("Interact with SHATO through text or voice commands!")
    
    with gr.Tab("💬 Text Interaction"):
        gr.Markdown("## Text-Based Interaction")
        gr.Markdown("Type your command or question for SHATO:")
        
        with gr.Row():
            with gr.Column():
                text_input = gr.Textbox(
                    label="Your Message",
                    placeholder="Type your message here... (e.g., 'move to position 5 and 7')",
                    lines=3
                )
                text_submit_btn = gr.Button("🚀 Send Message", variant="primary", size="lg")
                
            with gr.Column():
                text_response = gr.Textbox(
                    label="SHATO Response",
                    lines=8,
                    interactive=False
                )
                
                text_audio_output = gr.Audio(
                    label="🔊 Audio Response",
                    interactive=False
                )
        
        # Connect text interaction
        text_submit_btn.click(
            fn=process_text_input,
            inputs=[text_input],
            outputs=[text_response, text_audio_output, gr.State()]
        )
    
    with gr.Tab("🎤 Voice Interaction"):
        gr.Markdown("## Voice-Based Interaction")
        gr.Markdown("Record your voice command for SHATO:")
        
        with gr.Row():
            with gr.Column():
                start_record_btn = gr.Button(
                    "🔴 Start Recording", variant="stop", size="lg"
                )
                stop_record_btn = gr.Button(
                    "⏹️ Stop Recording", variant="secondary", size="lg"
                )
                
                recording_status = gr.Textbox(
                    label="Recording Status", 
                    value="⏹️ Not Recording", 
                    interactive=False
                )
                
                process_voice_btn = gr.Button(
                    "🎯 Process Voice Command", variant="primary", size="lg"
                )
                
            with gr.Column():
                recording_output = gr.Textbox(
                    label="Recording Result", 
                    lines=3, 
                    interactive=False
                )
                
                voice_response = gr.Textbox(
                    label="SHATO Voice Response",
                    lines=8,
                    interactive=False
                )
                
                voice_audio_output = gr.Audio(
                    label="🔊 Audio Response",
                    interactive=False
                )
        
        # Hidden state for audio file path
        audio_file_state = gr.State()
        
        # Connect voice interaction
        start_record_btn.click(
            fn=start_recording,
            outputs=[recording_output, recording_status]
        )
        
        stop_record_btn.click(
            fn=stop_recording,
            outputs=[recording_output, recording_status, audio_file_state]
        )
        
        process_voice_btn.click(
            fn=process_voice_recording,
            inputs=[audio_file_state],
            outputs=[voice_response, voice_audio_output, gr.State()]
        )
    
    with gr.Tab("🔧 System Status"):
        gr.Markdown("## Service Status")
        
        def check_service_status():
            """Check status of all services"""
            services = {
                "Orchestrator": ORCHESTRATOR_URL,
                "TTS Service": TTS_URL,
                "STT Service": STT_URL + " (Not implemented yet)"
            }
            
            status_text = "### Service Health Check:\n"
            for service_name, url in services.items():
                try:
                    if "Not implemented" in url:
                        status_text += f"- **{service_name}**: 🔄 Reserved for future implementation\n"
                    else:
                        response = requests.get(f"{url.split(' ')[0]}/health", timeout=5)
                        if response.status_code == 200:
                            status_text += f"- **{service_name}**: ✅ Healthy\n"
                        else:
                            status_text += f"- **{service_name}**: ⚠️ Unhealthy ({response.status_code})\n"
                except Exception as e:
                    status_text += f"- **{service_name}**: ❌ Unreachable\n"
            
            return status_text
        
        status_output = gr.Markdown()
        check_status_btn = gr.Button("🔍 Check Service Status", variant="secondary")
        
        check_status_btn.click(
            fn=check_service_status,
            outputs=[status_output]
        )
        
        # Auto-check on load
        demo.load(fn=check_service_status, outputs=[status_output])
    
    with gr.Tab("ℹ️ About"):
        gr.Markdown(
            """
        ## About SHATO Project
        
        This is the SHATO Voice-Controlled Robotic Assistant. A complete AI-powered system that combines:
        
        **🧠 Core Services:**
        - **LLM Service**: Fine-tuned Gemma 270M for robot command understanding
        - **Orchestrator**: Central routing system managing the entire pipeline
        - **Robot Validator**: Strict command validation and robot simulation
        - **TTS Service**: Parler TTS for natural voice responses
        - **UI Service**: This Gradio interface for user interaction
        
        **🔄 Integration Flow:**
        1. **Text Path**: UI → Orchestrator → LLM → Validator → Response → TTS → Audio
        2. **Voice Path**: UI → [STT] → Orchestrator → LLM → Validator → Response → TTS → Audio
        
        **🎯 Supported Commands:**
        - `move_to`: Navigate to coordinates (x, y)
        - `rotate`: Rotate by angle in specified direction  
        - `start_patrol`: Begin predefined patrol routes
        
        **👥 Development Team:**
        Group 1 (MIA Training) - Building the future of voice-controlled robotics!
        
        **🚀 Features:**
        - Real-time voice interaction
        - Strict command validation 
        - Natural language understanding
        - Professional TTS responses
        - Complete request tracking with correlation IDs
        
        Thank you for using SHATO! 🤖❤️
        """
        )

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        debug=True
    )