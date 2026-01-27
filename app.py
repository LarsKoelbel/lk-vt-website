from flask import Flask, send_from_directory, request, Response, jsonify
from pymongo import MongoClient

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Simple credentials
USERNAME = "admin"
PASSWORD = "123456"

# MongoDB Verbindung
client = MongoClient("mongodb://root:1kblHc616MFcMZadsYU0lBy2CoaGAulo89lCsroCv0ca6Kst24@192.168.178.180:27017/?authSource=admin")
db = client["events"]
collection = db["events"]

def check_auth(username, password):
    return username == USERNAME and password == PASSWORD

def authenticate():
    """Sends a 401 response that triggers the browser login prompt"""
    return Response(
        'Login required', 401,
        {'WWW-Authenticate': 'Basic realm="Protected"'}
    )

def requires_auth(f):
    """Decorator to protect routes"""
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    decorated.__name__ = f.__name__  # preserve function name
    return decorated

# Serve index.html at /
@app.route('/')
@requires_auth
def index():
    return send_from_directory('static', 'index.html')

@app.route('/events/info/tags')
def events_warnings_and_info():
    return send_from_directory('static', 'warning_and_info.html')

@app.route('/events')
def events():
    return send_from_directory('static', 'event_page.html')

# Event API
@app.route('/api/events', methods=['POST'])
def get_event():
    data = request.json
    event_id_raw = data.get('event_id')

    if not event_id_raw:
        return jsonify({"error": "Keine Event ID angegeben"}), 400

    try:
        # Konvertierung zu Int, da dein Schema "id": 12345 nutzt
        event_id = int(event_id_raw)

        # Suche in MongoDB (id ohne Unterstrich, wie in deinem Schema)
        event = collection.find_one({"id": event_id}, {"_id": 0})

        if event:
            return jsonify(event), 200
        else:
            return jsonify({
                "error": "Event nicht gefunden",
                "message": f"Das Event mit der ID {event_id} existiert nicht in unserer Datenbank."
            }), 404

    except ValueError:
        return jsonify({"error": "Ungültiges ID-Format"}), 400
    except Exception as e:
        return jsonify({"error": "Serverfehler", "details": str(e)}), 500


@app.route('/api/events/warnings_and_info', methods=['POST'])
def get_event_warnings_and_info():
    try:
        # Falls der Content-Type nicht exakt application/json ist,
        # könnte Flask hier scheitern. silent=True verhindert Abstürze.
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        event_id = data.get('id')

        # Suche in der MongoDB
        info_collection = client['events']['warnings_and_info']

        event_info = info_collection.find_one(
            {"id": int(event_id)},
            {"_id": 0}
        )

        print(event_info)

        if not event_info:
            return jsonify({"message": "Not found"}), 404

        return jsonify(event_info), 200

    except Exception as e:
        app.logger.error(f"Error in warnings_and_info: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/gear')
@requires_auth
def gear():
    return send_from_directory('static', 'gear.html')

# Serve everything else from static at the root
@app.route('/<path:path>')
@requires_auth
def static_files(path):
    return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(debug=True, port=3011, host='0.0.0.0')
