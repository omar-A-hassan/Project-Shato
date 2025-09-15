import torch
from parler_tts import ParlerTTSForConditionalGeneration
from transformers import AutoTokenizer
import soundfile as sf

device = "cuda:0" if torch.cuda.is_available() else "cpu"

model_path = "parler-tts/parler-tts-tiny-v1"
model = ParlerTTSForConditionalGeneration.from_pretrained(model_path).to(device)
tokenizer = AutoTokenizer.from_pretrained(model_path)
prompt = "Hello, are you ready to start your journey with Parler TTS?"

description = "A female speaker delivers a slightly expressive and animated speech with pitch. The recording is of very high quality, with the speaker's voice sounding clear and very close up."

desc_inputs = tokenizer(description, return_tensors="pt", padding=True)
prompt_inputs = tokenizer(prompt, return_tensors="pt", padding=True)

input_ids = desc_inputs.input_ids.to(device)
attention_mask = desc_inputs.attention_mask.to(device)

prompt_input_ids = prompt_inputs.input_ids.to(device)
prompt_attention_mask = prompt_inputs.attention_mask.to(device)

generation = model.generate(
    input_ids=input_ids,
    attention_mask=attention_mask,
    prompt_input_ids=prompt_input_ids,
    prompt_attention_mask=prompt_attention_mask,
)

audio_arr = generation.cpu().numpy().squeeze()
sf.write("parler_tts_out.wav", audio_arr, model.config.sampling_rate)
