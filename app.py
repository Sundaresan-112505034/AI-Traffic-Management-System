"""AI Traffic Management System - Flask backend (runs fully offline)."""
import json
import os
import sqlite3
import threading
import time
import traceback
import webbrowser
from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.utils import secure_filename

import config
from ai.detector import DetectorError, ModelNotFoundError
from ai.signal_controller import get_signal_plan
from ai.traffic_analysis import AnalysisError, analyze_video

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
analysis_lock = threading.Lock()

for folder in (config.UPLOAD_DIR, config.OUTPUT_DIR, config.MODELS_DIR):
    os.makedirs(folder, exist_ok=True)

COLUMNS = {  # column -> SQL type (extra columns beyond the required fields are used by the result page)
    "video_name": "TEXT", "analysis_date": "TEXT", "total_vehicles": "INTEGER", "cars": "INTEGER",
    "motorcycles": "INTEGER", "buses": "INTEGER", "trucks": "INTEGER", "bicycles": "INTEGER",
    "average_speed": "REAL", "traffic_density": "TEXT", "congestion_level": "INTEGER",
    "signal_status": "TEXT", "recommended_green_time": "INTEGER",
    "snapshot": "TEXT", "output_video": "TEXT", "details_json": "TEXT",
}


# ---------------------------------------------------------------- database
def db():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create traffic.db and the table automatically (also adds missing columns to an old table)."""
    with db() as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS traffic_analysis (id INTEGER PRIMARY KEY AUTOINCREMENT)")
        existing = {r["name"] for r in conn.execute("PRAGMA table_info(traffic_analysis)")}
        for name, sql_type in COLUMNS.items():
            if name not in existing:
                conn.execute("ALTER TABLE traffic_analysis ADD COLUMN %s %s" % (name, sql_type))


def save_result(video_name, r):
    details = json.dumps({"timeline": r["timeline"], "vehicle_speeds": r["vehicle_speeds"],
                          "frames_processed": r["frames_processed"], "density_value": r["density_value"]})
    with db() as conn:
        cur = conn.execute(
            "INSERT INTO traffic_analysis (video_name, analysis_date, total_vehicles, cars, motorcycles, buses,"
            " trucks, bicycles, average_speed, traffic_density, congestion_level, signal_status,"
            " recommended_green_time, snapshot, output_video, details_json)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (video_name, datetime.now().strftime("%Y-%m-%d %H:%M"), r["total_vehicles"], r["cars"],
             r["motorcycles"], r["buses"], r["trucks"], r["bicycles"], r["average_speed"], r["traffic_density"],
             r["congestion_level"], r["signal_status"], r["recommended_green_time"], r["snapshot"],
             r["output_video"], details))
        return cur.lastrowid


def row_to_dict(row):
    d = dict(row)
    details = json.loads(d.pop("details_json", None) or "{}")
    d["timeline"] = details.get("timeline", [])
    d["vehicle_speeds"] = details.get("vehicle_speeds", [])
    d["frames_processed"] = details.get("frames_processed")
    d["plan"] = get_signal_plan(d.get("traffic_density"))
    d["demo"] = False
    return d


def demo_dict():
    d = dict(config.DEMO_DATA)
    d["id"] = 0
    d["plan"] = get_signal_plan(d["traffic_density"])
    d["demo"] = True
    return d


# ---------------------------------------------------------------- helpers
def allowed(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS


def friendly_page(message, code=500):
    html = ("<!doctype html><meta charset='utf-8'><link rel='stylesheet' href='/static/css/style.css'>"
            "<body><main class='container'><div class='panel'><h2>Something went wrong</h2><p>%s</p>"
            "<a class='btn' href='/'>Back to Home</a></div></main></body>" % message)
    return html, code


@app.context_processor
def inject_flags():
    return {"demo_mode": config.DEMO_MODE}


# ---------------------------------------------------------------- pages
@app.route("/")
def index():
    return render_template("index.html", extensions=sorted(config.ALLOWED_EXTENSIONS))


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", result_id=None)


@app.route("/history")
def history():
    with db() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM traffic_analysis ORDER BY id DESC")]
    return render_template("history.html", rows=rows)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/results/<int:result_id>")
def results(result_id):
    with db() as conn:
        row = conn.execute("SELECT * FROM traffic_analysis WHERE id=?", (result_id,)).fetchone()
    if row is None:
        return friendly_page("That analysis result was not found. It may have been deleted.", 404)
    return render_template("analysis.html", r=row_to_dict(row))


# ---------------------------------------------------------------- media
@app.route("/media/uploads/<path:name>")
def media_upload(name):
    return send_from_directory(config.UPLOAD_DIR, name)


@app.route("/media/outputs/<path:name>")
def media_output(name):
    return send_from_directory(config.OUTPUT_DIR, name, as_attachment=request.args.get("download") == "1")


# ---------------------------------------------------------------- actions
@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("video")
    if file is None or not file.filename:
        return jsonify(ok=False, error="Please choose a traffic video file first."), 400
    if not allowed(file.filename):
        return jsonify(ok=False, error="Unsupported file. Please upload a valid MP4, AVI, MOV or MKV traffic video."), 400
    safe = secure_filename(file.filename) or "video.mp4"
    stored = "%d_%s" % (int(time.time()), safe)
    file.save(os.path.join(config.UPLOAD_DIR, stored))
    return jsonify(ok=True, filename=stored, url="/media/uploads/" + stored)


@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json(silent=True) or {}
    filename = secure_filename(data.get("filename", ""))
    if not filename or not allowed(filename):
        return jsonify(ok=False, error="Please upload a valid MP4 traffic video first."), 400
    path = os.path.join(config.UPLOAD_DIR, filename)
    if not os.path.isfile(path):
        return jsonify(ok=False, error="Video not found on the server. Please upload it again."), 404
    if not analysis_lock.acquire(blocking=False):
        return jsonify(ok=False, error="Another analysis is running. Please wait until it finishes."), 409
    try:
        result = analyze_video(path, os.path.splitext(filename)[0])
        new_id = save_result(filename.split("_", 1)[-1], result)
        return jsonify(ok=True, id=new_id, redirect="/results/%d" % new_id)
    except (AnalysisError, ModelNotFoundError, DetectorError) as exc:
        return jsonify(ok=False, error=str(exc)), 422
    except Exception:
        traceback.print_exc()          # traceback goes to the console only, never to the browser
        return jsonify(ok=False, error="Analysis failed for this video. Please try another MP4 file."), 500
    finally:
        analysis_lock.release()


@app.route("/delete/<int:result_id>", methods=["POST"])
def delete(result_id):
    with db() as conn:
        row = conn.execute("SELECT snapshot, output_video FROM traffic_analysis WHERE id=?", (result_id,)).fetchone()
        conn.execute("DELETE FROM traffic_analysis WHERE id=?", (result_id,))
    if row:
        for name in (row["snapshot"], row["output_video"]):
            if name:
                try:
                    os.remove(os.path.join(config.OUTPUT_DIR, name))
                except OSError:
                    pass
    return jsonify(ok=True)


# ---------------------------------------------------------------- API
@app.route("/api/dashboard")
def api_dashboard():
    result_id = request.args.get("id", type=int)
    if config.DEMO_MODE and not result_id:
        return jsonify(demo_dict())
    with db() as conn:
        if result_id:
            row = conn.execute("SELECT * FROM traffic_analysis WHERE id=?", (result_id,)).fetchone()
        else:
            row = conn.execute("SELECT * FROM traffic_analysis ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        return jsonify(empty=True)
    return jsonify(row_to_dict(row))


@app.route("/api/history")
def api_history():
    with db() as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM traffic_analysis ORDER BY id DESC")]
    for r in rows:
        r.pop("details_json", None)
    return jsonify(rows)


# ---------------------------------------------------------------- errors
@app.errorhandler(413)
def too_large(_):
    return jsonify(ok=False, error="File too large. Maximum size is %d MB." % config.MAX_UPLOAD_MB), 413


@app.errorhandler(Exception)
def any_error(exc):
    if isinstance(exc, HTTPException):
        if exc.code == 404:
            return friendly_page("Page not found.", 404)
        return friendly_page("Request could not be completed.", exc.code or 400)
    traceback.print_exc()
    return friendly_page("An unexpected error occurred. Please go back and try again.", 500)


init_db()

if __name__ == "__main__":
    threading.Timer(1.2, lambda: webbrowser.open("http://127.0.0.1:5000/")).start()
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
