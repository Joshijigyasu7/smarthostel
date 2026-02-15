import os
import logging
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, session, jsonify, send_file
from pymongo import MongoClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from io import BytesIO

load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "hostel_secret_123"

ADMIN_USER = "admin"
ADMIN_PASSWORD = "admin123"

MONGODB_URI = os.environ.get("MONGODB_URI")
MONGODB_DB = os.environ.get("MONGODB_DB", "hostel_db")
STUDENTS_COLLECTION = os.environ.get("MONGODB_STUDENTS_COLLECTION", "students")
ROOMS_COLLECTION = os.environ.get("MONGODB_ROOMS_COLLECTION", "rooms")
TRANSACTIONS_COLLECTION = os.environ.get("MONGODB_TRANSACTIONS_COLLECTION", "transactions")

if not MONGODB_URI:
    logger.error("MONGODB_URI is not set. Set it before starting the app.")
    raise RuntimeError("MONGODB_URI is not set. Set it before starting the app.")

try:
    mongo_client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
    mongo_client.server_info()  # Test connection
    logger.info("✓ MongoDB connected successfully")
except Exception as e:
    logger.error(f"✗ MongoDB connection failed: {e}")
    raise

db = mongo_client[MONGODB_DB]
students_collection = db[STUDENTS_COLLECTION]
rooms_collection = db[ROOMS_COLLECTION]
transactions_collection = db[TRANSACTIONS_COLLECTION]

# Health check route
@app.route("/health")
def health():
    return jsonify({"status": "ok", "message": "App is running"}), 200

# Favicon route
@app.route("/favicon.ico")
def favicon():
    return send_file("static/favicon.ico", mimetype="image/x-icon")

# Error handlers
@app.errorhandler(404)
def not_found(e):
    logger.error(f"404 Error: {request.path}")
    return jsonify({"error": "Not found", "path": request.path}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 Error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        sid = request.form.get("sid")
        pwd = request.form.get("pwd")

        user = students_collection.find_one({"sid": sid, "password": pwd})

        if user:
            session["sid"] = sid
            return redirect("/rooms")
        else:
            return "Invalid Login"

    return render_template("login.html")

# ---------------- ROOMS ----------------
@app.route("/rooms")
def rooms():
    if "sid" not in session:
        return redirect("/")

    rooms = list(rooms_collection.find({}, {"_id": 0}))
    rooms_map = {room["room"]: room.get("status", "available") for room in rooms}
    assigned_room = rooms_collection.find_one(
        {"assignedSid": session["sid"], "status": "occupied"},
        {"_id": 0, "room": 1}
    )

    return render_template(
        "rooms.html",
        rooms=rooms,
        rooms_map=rooms_map,
        assigned_room=assigned_room
    )

# ------------- SELECT ROOM -------------
@app.route("/select_room", methods=["POST"])
def select_room():
    if "sid" not in session:
        return redirect("/")

    already_assigned = rooms_collection.find_one(
        {"assignedSid": session["sid"], "status": "occupied"},
        {"_id": 0, "room": 1}
    )
    if already_assigned:
        return "You already have an allotted room"

    room = request.form.get("room")
    if not room:
        return "Please select a room"

    room_doc = rooms_collection.find_one({"room": room}, {"_id": 0, "status": 1})
    if room_doc and room_doc.get("status") == "occupied":
        return "Room already occupied"

    session["room"] = room
    return redirect("/payment")

# ---------------- PAYMENT ----------------
@app.route("/payment")
def payment():
    if "sid" not in session or "room" not in session:
        return redirect("/")

    return render_template(
        "payment.html",
        sid=session["sid"],
        room=session["room"]
    )

# ---------------- MARK PAID ----------------
@app.route("/mark_paid", methods=["POST"])
def mark_paid():
    if "sid" not in session:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    room = data.get("room")
    tx_hash = data.get("txHash")
    if not room:
        return jsonify({"ok": False, "error": "Room is required"}), 400
    if not tx_hash:
        return jsonify({"ok": False, "error": "Transaction hash is required"}), 400

    result = rooms_collection.update_one(
        {"room": room, "status": {"$ne": "occupied"}},
        {"$set": {"status": "occupied", "assignedSid": session["sid"]}}
    )

    if result.matched_count == 0:
        return jsonify({"ok": False, "error": "Room already occupied"}), 409

    transactions_collection.insert_one({
        "sid": session["sid"],
        "room": room,
        "txHash": tx_hash,
        "createdAt": datetime.now(timezone.utc).isoformat()
    })

    return jsonify({"ok": True})

# ---------------- DOWNLOAD RECEIPT ----------------
@app.route("/download_receipt", methods=["POST"])
def download_receipt():
    if "sid" not in session:
        return jsonify({"ok": False, "error": "Not logged in"}), 401

    data = request.get_json(silent=True) or {}
    room = data.get("room")
    tx_hash = data.get("txHash")
    date_utc = data.get("dateUtc")

    if not all([room, tx_hash, date_utc]):
        return jsonify({"ok": False, "error": "Missing receipt data"}), 400

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Logo
    try:
        logo_path = os.path.join(app.static_folder, "logo.png")
        logo = ImageReader(logo_path)
        c.drawImage(logo, 40, height - 100, width=80, height=80, preserveAspectRatio=True)
    except:
        pass

    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 60, "National Institute of Electronics and Information Technology")
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 80, "Ajmer Campus")
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 110, "Hostel Room Allotment Receipt")

    # Details
    c.setFont("Helvetica", 11)
    y = height - 160
    details = [
        ("Student ID:", session["sid"]),
        ("Room Allotted:", room),
        ("Amount Paid:", "1 ETH"),
        ("Transaction Hash:", tx_hash),
        ("Date (UTC):", date_utc),
    ]

    for label, value in details:
        c.drawString(80, y, label)
        c.drawString(250, y, value)
        y -= 25

    # Signatory
    c.setFont("Helvetica-Italic", 10)
    c.drawString(width - 200, 100, "Authorized Signatory")
    c.line(width - 200, 95, width - 60, 95)

    c.showPage()
    c.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"receipt_{session['sid']}.pdf", mimetype="application/pdf")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect("/admin")

# ---------------- REVOKE ROOM (ADMIN) ----------------
@app.route("/admin/revoke_room", methods=["POST"])
def revoke_room():
    if not session.get("is_admin"):
        return jsonify({"ok": False, "error": "Not authorized"}), 401

    data = request.get_json(silent=True) or {}
    room_num = data.get("room")
    if not room_num:
        return jsonify({"ok": False, "error": "Room required"}), 400

    result = rooms_collection.update_one(
        {"room": room_num, "status": "occupied"},
        {"$set": {"status": "available"}, "$unset": {"assignedSid": ""}}
    )

    if result.matched_count == 0:
        return jsonify({"ok": False, "error": "Room not found"}), 404

    return jsonify({"ok": True})

# ------------ STUDENT DASHBOARD --------
@app.route("/student/dashboard")
def student_dashboard():
    if "sid" not in session:
        return redirect("/")

    assigned_room = rooms_collection.find_one(
        {"assignedSid": session["sid"], "status": "occupied"},
        {"_id": 0, "room": 1}
    )

    if not assigned_room:
        return redirect("/rooms")

    return render_template(
        "student_dashboard.html",
        sid=session["sid"],
        room=assigned_room["room"]
    )

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == ADMIN_USER and password == ADMIN_PASSWORD:
            session["is_admin"] = True
            return redirect("/admin/dashboard")

        return render_template("admin_login.html", error="Invalid admin login")

    return render_template("admin_login.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        return redirect("/admin")

    occupied_rooms = list(
        rooms_collection.find(
            {"status": "occupied"},
            {"_id": 0, "room": 1, "assignedSid": 1}
        )
    )

    transactions = list(
        transactions_collection.find(
            {},
            {"_id": 0, "sid": 1, "room": 1, "txHash": 1, "createdAt": 1}
        ).sort("createdAt", -1)
    )

    return render_template(
        "admin_dashboard.html",
        occupied_rooms=occupied_rooms,
        transactions=transactions
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)

