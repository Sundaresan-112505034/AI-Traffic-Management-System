# AI Traffic Management System (MCA Mini Project)
Flask + OpenCV + Ultralytics YOLO + SQLite. Runs fully offline on Windows (CPU only). No API keys, no paid services.

## 1. Install (Windows, Python 3.13)
```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
## 2. Get the free YOLO model (needs internet ONCE)
```
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
move yolo11n.pt models\yolo11n.pt
```
(Or copy any existing yolov8n.pt / yolo11n.pt into the `models` folder.)

## 3. Run
```
python app.py
```
Browser opens http://127.0.0.1:5000/

## 4. Settings
Everything is in `config.py`: DEMO_MODE, CONFIDENCE_THRESHOLD, FRAME_SKIP, INPUT_WIDTH, PIXELS_PER_METER, FPS,
density thresholds, signal timings, MAX_ANALYSIS_SECONDS (default 60 s of video for CPU safety).

## 5. Test procedure
1 App starts (`python app.py`) -> 2 Home loads -> 3 Upload section visible -> 4 upload an MP4, preview appears ->
5-7 click Analyze Traffic: model loads, boxes/counts appear in result snapshot -> 8 density badge -> 9 signal countdown ->
10-11 History page lists the saved row -> 12 Dashboard shows the latest analysis.

## 6. Demo procedure
1. Open Home, upload a short (20-60 s) traffic MP4 (side/elevated camera works best), click Analyze Traffic.
2. Show the result page: annotated frame, counts, density, congestion, signal countdown (use 10x timer speed).
3. Show History (view / delete) and Dashboard.
4. Fallback if analysis is slow or no video: set `DEMO_MODE = True` in config.py, restart; the dashboard shows
   sample data under a visible "DEMO DATA" banner. Set it back to False for real results.

## 7. Viva answers (short)
1. **What is it?** A system that analyses traffic video with AI to count vehicles, estimate density/speed and suggest signal timing.
2. **Why this project?** Traffic congestion is a real problem; fixed-time signals waste time; AI vision gives cheap data.
3. **YOLO?** "You Only Look Once" - a fast neural network that finds objects and their class in an image in one pass.
4. **OpenCV?** A free library for reading videos, resizing frames and drawing boxes.
5. **Detection?** Each frame is resized to 640 px; YOLO returns boxes, class and confidence; we keep car, motorcycle, bus, truck, bicycle above 0.45 confidence.
6. **Counting?** Every tracked vehicle is counted once, after it is seen in at least 3 processed frames.
7. **Tracking?** Giving the same ID to the same vehicle in consecutive frames by matching the nearest box centre.
8. **Density?** Average number of vehicles visible per frame, mapped to LOW (0-10), MEDIUM (11-20), HIGH (21-35), CRITICAL (36+).
9. **Congestion?** Density value / 40 x 100, capped at 100 %. A project-level estimate, not calibrated science.
10. **Speed?** Distance moved in pixels / PIXELS_PER_METER gives metres; divide by elapsed time (frames / FPS); x 3.6 gives km/h. Approximate.
11. **Adaptive signal?** The density level selects a green/yellow/red timing table; JavaScript runs the GREEN-YELLOW-RED countdown.
12. **Flask?** Lightweight Python web framework, easy to run locally.
13. **SQLite?** Serverless file database (traffic.db), nothing to install, created automatically.
14. **Zero cost?** All libraries and the YOLO model are free/open source; no API, cloud or key; runs on a college PC.
15. **Limitations?** Estimated speed depends on calibration; simple tracker can swap IDs in dense traffic; accuracy depends on camera angle and light; CPU is slow.
16. **Future?** Multi-lane/junction control, license-plate recognition, live CCTV stream, GPU, better tracker (ByteTrack), real signal hardware.

## Features
Upload and preview, YOLO detection, tracking and counting, speed estimate, density and congestion, adaptive signal with countdown,
dashboard with charts, SQLite history with view/delete, annotated video + snapshot download, DEMO mode, friendly error messages.

## Low-spec / 32-bit laptop mode (no PyTorch)
Install only: `pip install -r requirements-lite.txt`. Put `yolov8n.onnx` (exported with imgsz=320) in `models\`.
The app detects the .onnx file automatically (DETECTOR_BACKEND = "auto" in config.py).
Export once on any 64-bit machine / Google Colab:
    pip install ultralytics
    python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx', imgsz=320, opset=12)"
Suggested config for a slow laptop: FRAME_SKIP = 5, MAX_ANALYSIS_SECONDS = 15, INPUT_WIDTH = 480.
