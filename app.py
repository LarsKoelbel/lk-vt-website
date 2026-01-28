from cgitb import handler
from time import process_time_ns

from flask import Flask, send_from_directory, request, Response, jsonify
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# Simple credentials
USERNAME = "musicadmin"
PASSWORD = "ionlyloveyouforyourbody"

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

@app.before_request
def track_visit():
    # Wir erfassen nur den aktuellen Zeitstempel
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open('log/visits.log', 'a') as f:
        f.write(f"Visit at: {timestamp}\n")

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

@app.route('/veranstaltungen')
def overview():
    return send_from_directory('static', 'event_overview_page.html')

@app.route('/event-creation-tool')
@requires_auth
def event_creation_tool():
    return send_from_directory('static', 'event_creation_tool.html')

@app.route('/event-admin-view')
@requires_auth
def event_admin_view():
    return send_from_directory('static', 'event_admin_page.html')

# Event API
@app.route('/api/events', methods=['POST'])
def get_event():
    data = request.json
    event_id_raw = data.get('event_id')
    if event_id_raw is None: event_id_raw = data.get('id')
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

        if not event_info:
            return jsonify({"message": "Not found"}), 404

        return jsonify(event_info), 200

    except Exception as e:
        app.logger.error(f"Error in warnings_and_info: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/events/participants', methods=['POST'])
def get_event_participants():
    try:
        # Falls der Content-Type nicht exakt application/json ist,
        # könnte Flask hier scheitern. silent=True verhindert Abstürze.
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        event_id = data.get('id')

        # Suche in der MongoDB
        info_collection = client['events']['participants']

        event_info = info_collection.find_one(
            {"id": int(event_id)},
            {"_id": 0}
        )

        if not event_info:
            return jsonify({"message": "Not found"}), 404

        return jsonify(event_info), 200

    except Exception as e:
        app.logger.error(f"Error in participants: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/upload/push-event', methods=['POST'])
@requires_auth
def upload_push_event():
    try:
        # Falls der Content-Type nicht exakt application/json ist,
        # könnte Flask hier scheitern. silent=True verhindert Abstürze.
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        push_type = data.get('upload-type')
        if push_type == 'event-main':
            handler = collection
        elif push_type == 'event-info':
            handler = client['events']['warnings_and_info']
        elif push_type == 'event-participants':
            handler = client['events']['participants']
        else:
            return jsonify({"error": "Unknown upload type"}), 404

        payload = data.get('payload')

        if payload is None:
            return jsonify({"error": "No payload in upload"}), 404

        payload['id'] = int(payload['id'])

        handler.replace_one(
            {'id': payload['id']},
            payload,
            upsert=True
        )

        return jsonify({"upload-success": True}), 200

    except Exception as e:
        app.logger.error(f"Error in warnings_and_info: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/events/drop-event-data-complete', methods=['POST'])
@requires_auth
def drop_event_complete():
    try:
        # Falls der Content-Type nicht exakt application/json ist,
        # könnte Flask hier scheitern. silent=True verhindert Abstürze.
        data = request.get_json(silent=True)

        if not data:
            return jsonify({"error": "Invalid JSON"}), 400

        id = data.get('id')
        if id is None:
            return jsonify({"error": "No id found"}), 404

        id = int(id)

        h = collection
        h.delete_one({"id": id})

        h = client['events']['warnings_and_info']
        h.delete_one({"id": id})

        h = client['events']['participants']
        h.delete_one({"id": id})

        return jsonify({"delete-success": True}), 200

    except Exception as e:
        app.logger.error(f"Error in warnings_and_info: {e}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route('/api/events/overview', methods=['GET'])
def get_event_overview():
    try:

        result = {
            "event_overview_list": []
        }

        for doc in collection.find():
            id = doc.get('id')
            if id is None or len(str(id)) < 5: continue
            element = {
                "id": doc.get('id'),
                "title": doc.get('title'),
                "main_image_source": doc.get('main_image'),
                "dates": doc.get('dates'),
                'artist': doc.get('artist'),
                'location': doc.get('location'),
                'overview_info': doc.get('overview_info')
            }
            result['event_overview_list'].append(element)

        return jsonify(result), 200

    except Exception as e:
        app.logger.error(f"Error in event overview: {e}")
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
