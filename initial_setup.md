# G.R.A.C.E. home-lab initial setup

The assistant name is configuration, not application logic. The default is **G.R.A.C.E.** — “Generally Reliable Assistant for Computing and Engineering.” Change `GRACE_NAME` and `GRACE_EXPANSION` in `.env` whenever the name evolves.

This document is the working product specification for the first MVP. The initial implementation in `app/` provides the API and dashboard; optional integrations can be installed as hardware becomes available.

## Hardware target

The first deployment target is a machine with a GTX 1070 (8 GB VRAM). Keep inference practical by using a small YOLO model, sampling the camera every 1–2 seconds, and sending scene summaries—not video frames—to a local 7B language model. GPU acceleration is optional during development.

## MVP boundary

Yes — the first MVP should be an assistant, but not a full “talking JARVIS” yet.

The highest-cool-factor MVP for your GTX 1070 is:

G.R.A.C.E. room assistant

A local website on your Wi-Fi where you can:

See your webcam feed.
See what the AI detects in the room.
Type commands to a local LLM.
Hear spoken responses through speakers.
Later add voice-to-text.

That gives you the “assistant” feeling immediately without getting stuck in microphone/wake-word complexity.

MVP v1: website + webcam + local LLM + speaker

Build this first:

Webcam
  ↓
YOLO object detection
  ↓
Local FastAPI backend
  ↓
Wi-Fi web dashboard
  ↓
Local LLM via Ollama
  ↓
Text-to-speech through speakers

The website could show:

G.R.A.C.E. HOME LAB

Live camera: [webcam feed]

Detected:
- person
- chair
- laptop
- backpack
- dog/cat if present
- phone

Assistant:
“You are at your desk. I see a laptop, chair, and backpack. No unusual movement.”

Ultralytics YOLO is a very practical fit because its Python package supports object detection, segmentation, classification, pose, and tracking workflows, and it can be used directly from Python or CLI.

Do you need voice-to-text immediately?

No. Voice-to-text is not required for the first MVP.

For the first pass, I would do this order:

Phase	Feature	Why
1	Web dashboard	Makes it accessible from any device on Wi-Fi
2	Webcam object detection	Gives it “Spider-Sense” immediately
3	Typed chat command box	Easier than voice and still feels like an assistant
4	Speaker output	Makes it feel alive
5	Voice-to-text	Add after the core loop works
6	Wake word	Add last

Voice is cool, but it adds complexity: microphone routing, background noise, push-to-talk, wake words, latency, and accidental activations. The first magical moment should be:

You open a website on your phone and it says what it sees.

That is the MVP. The dashboard is served by FastAPI at `http://<lab-machine>:8000`.

What the first version should actually do

Give it 5–8 commands:

/status
/what-do-you-see
/watch-room
/stop-watch
/summarize-last-10-minutes
/where-is-my-phone
/lab-mode
/help

Example behavior:

You type:
what do you see?

Assistant says aloud:
“I see a person, laptop, chair, and backpack. No motion changes in the last 30 seconds.”

You type:
watch the room

Assistant says aloud:
“Spider-Sense enabled. I’ll alert you if a person enters, a package appears, or something changes.”

That is already awesome.

Local LLM: yes, but keep it small

Use Ollama as the local LLM server. Ollama has a programmatic API and OpenAI-compatible endpoints, which makes it easy to connect your own web app to a local model.

For your GTX 1070, I’d start with:

Model	Use
qwen2.5-coder:7b	coding/helpful assistant
llama3.1:8b or similar 8B	general chat, if it runs acceptably
phi/small 3B models	faster response experiments

The LLM should not process every video frame. Let YOLO produce simple facts, then feed those facts to the LLM only when needed.

Example prompt to local LLM:

You are a local room assistant. The camera currently detects:
- person, confidence 0.91
- laptop, confidence 0.86
- chair, confidence 0.77

Recent events:
- person entered frame 12 seconds ago
- backpack disappeared 2 minutes ago

Answer the user's command: "what changed?"

That keeps the LLM useful without melting the GPU.

Voice-to-text: add as v2

For local voice-to-text, use Whisper-based tooling. whisper.cpp is designed for local Whisper inference, and Faster Whisper is another common option for GPU/CPU transcription setups.

But I’d add it as push-to-talk, not always-listening.

Better v2 flow:

Hold button on website
  ↓
Browser records audio
  ↓
Backend transcribes with Whisper
  ↓
Text command goes to assistant
  ↓
LLM responds
  ↓
Speaker speaks response

This avoids wake-word headaches.

The coolest realistic first demo

Build this:

G.R.A.C.E. v0.1

Features:

Web dashboard at something like http://tower.local:8000
Live webcam snapshot/feed
YOLO detections every 1–2 seconds
Event log:
“person entered”
“object appeared”
“object disappeared”
“motion detected”
Chat box:
“What do you see?”
“Has anything changed?”
“Describe the room like a suit AI.”
Speaker response:
use local text-to-speech
it talks from the tower speakers

That gives you the “assistant first pass” while staying achievable.

Suggested stack
Piece	Tool
Backend	FastAPI
Frontend	React / Next.js or simple HTML
Webcam	OpenCV
Vision	Ultralytics YOLO
LLM	Ollama
TTS	pyttsx3, Piper, or Windows TTS
Optional STT	whisper.cpp or faster-whisper
Realtime updates	WebSockets
Local network access	0.0.0.0:8000 + Wi-Fi IP
The architecture I’d use
Browser on phone/laptop
        ↓
 http://tower.local:8000
        ↓
FastAPI server
 ├─ /video-feed
 ├─ /detections
 ├─ /events
 ├─ /chat
 └─ /speak
        ↓
Workers
 ├─ camera_worker.py  → grabs frames
 ├─ vision_worker.py  → YOLO detections
 ├─ memory_worker.py  → event log
 ├─ llm_worker.py     → Ollama calls
 └─ tts_worker.py     → speaks responses
The part that makes it feel “alive”

Do not make it only answer questions. Make it maintain a small event memory.

Example internal state:

{
  "current_objects": ["person", "laptop", "chair"],
  "recent_events": [
    "person entered frame",
    "phone appeared on desk",
    "backpack disappeared"
  ],
  "room_status": "normal",
  "watch_mode": true
}

Then it can answer:

“What changed?”

Instead of just:

“I see a chair.”

That difference is huge.

Best build order
Step 1: Dashboard

Make a local webpage that shows:

camera frame
detected object list
event log
Step 2: YOLO loop

Run YOLO on one frame every 1–2 seconds. Do not try full 60 FPS at first.

Step 3: Event detection

Track changes:

object appeared
object disappeared
person entered
no motion for X minutes
object left in scene
Step 4: Typed assistant

Add a text input. Send command + current scene facts to Ollama.

Step 5: Speaker output

Have the assistant read responses aloud.

Step 6: Push-to-talk voice

Only after everything else works.

What I would not do first

Do not start with:

always-on wake word
custom model training
facial recognition
multi-camera mapping
autonomous drone
full smart-home integration
real-time 4K video
complex agent framework

Those can come later. The cool factor comes from seeing + remembering + talking, not from overbuilding.

Final answer

Yes: an assistant first pass is the right MVP, but make it a visual local assistant before making it a voice assistant.

The first MVP should be:

A Wi-Fi website connected to your GTX 1070 tower that watches through a webcam, detects objects/events, lets you ask typed questions, and speaks responses through speakers.

Then voice-to-text becomes the next layer, not the foundation.

Default name: G.R.A.C.E. The name and its expansion are configured through environment variables.

First magic command:

/what-changed

First magic response:

“A person entered the room 14 seconds ago. Your laptop and backpack are still visible. No other major changes detected.”
