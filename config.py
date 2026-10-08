"""All project settings in ONE place. Change values here, restart the app."""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
MODELS_DIR = os.path.join(BASE_DIR, "models")
DB_PATH = os.path.join(BASE_DIR, "traffic.db")

# ---------- Demo mode ----------
# True  -> dashboard shows clearly labelled SAMPLE ("DEMO DATA") values.
# False -> dashboard shows real results of the YOLO analysis.
DEMO_MODE = False

# ---------- Upload ----------
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}
MAX_UPLOAD_MB = 500

# ---------- YOLO / performance (CPU friendly) ----------
DETECTOR_BACKEND = "auto"        # "auto" | "ultralytics" (.pt) | "onnx" (OpenCV only, for low-spec PCs)
ONNX_INPUT_SIZE = 320            # must match the size used when exporting the .onnx model
MODEL_FILE = "yolo11n.pt"        # any other .pt in models/ is used if this one is missing
CONFIDENCE_THRESHOLD = 0.45
FRAME_SKIP = 2                   # process every 2nd frame (3 = faster, 1 = every frame)
INPUT_WIDTH = 640                # frames are resized to this width before detection
MAX_ANALYSIS_SECONDS = 60        # analyse at most this much video (0 = whole video)
SAVE_OUTPUT_VIDEO = True         # write annotated video into outputs/

# ---------- Tracking / counting ----------
TRACK_MAX_DISTANCE = 90          # max centroid jump (pixels, resized frame) between processed frames
TRACK_MAX_MISSED = 6             # processed frames a vehicle may vanish before its track ends
MIN_TRACK_HITS = 3               # a vehicle is counted only after being seen this many times

# ---------- Speed estimation (approximate / demo calibration) ----------
FPS = 25                         # used only if the video does not report its own FPS
PIXELS_PER_METER = 8.0           # pixels (in resized frame) that represent 1 metre on the road
MAX_SPEED_KMH = 120              # estimates above this are treated as noise and ignored
SPEED_MIN_SAMPLES = 4            # positions needed before a speed is calculated

# ---------- Traffic density / congestion (project-level estimation) ----------
# DENSITY_BASIS: "average" = average vehicles visible per processed frame
#                "peak"    = most vehicles visible in one frame
#                "total"   = total unique vehicles counted in the clip
DENSITY_BASIS = "average"
DENSITY_THRESHOLDS = [(10, "LOW"), (20, "MEDIUM"), (35, "HIGH")]   # above the last -> CRITICAL
CONGESTION_REFERENCE = 40        # density value that equals 100 % congestion

# ---------- Signal timing (seconds) ----------
SIGNAL_TIMINGS = {
    "LOW":      {"green": 60, "yellow": 5, "red": 30},
    "MEDIUM":   {"green": 45, "yellow": 5, "red": 45},
    "HIGH":     {"green": 30, "yellow": 5, "red": 60},
    "CRITICAL": {"green": 20, "yellow": 5, "red": 90},
}

# ---------- Sample data used when DEMO_MODE = True ----------
DEMO_DATA = {
    "video_name": "DEMO DATA (sample)",
    "analysis_date": "Sample",
    "total_vehicles": 42, "cars": 24, "motorcycles": 11, "buses": 3, "trucks": 4, "bicycles": 0,
    "average_speed": 31.0, "traffic_density": "HIGH", "congestion_level": 82,
    "signal_status": "GREEN", "recommended_green_time": 30,
    "timeline": [{"t": i * 3, "n": n} for i, n in enumerate([8, 11, 15, 19, 24, 28, 31, 27, 30, 33, 29, 26, 22])],
    "vehicle_speeds": [{"id": 12, "type": "car", "speed": 34.0}, {"id": 7, "type": "motorcycle", "speed": 41.5},
                       {"id": 3, "type": "bus", "speed": 22.0}, {"id": 18, "type": "truck", "speed": 27.5}],
}
