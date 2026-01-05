from flask import Flask, send_from_directory, request, Response

app = Flask(__name__)

# Simple credentials
USERNAME = "admin"
PASSWORD = "123456"

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

@app.route('/events')
@requires_auth
def events():
    return send_from_directory('static', 'events.html')

# Serve everything else from static at the root
@app.route('/<path:path>')
@requires_auth
def static_files(path):
    return send_from_directory('static', path)

if __name__ == "__main__":
    app.run(debug=True, port=3011, host='0.0.0.0')
