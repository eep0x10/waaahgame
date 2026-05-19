import os
from app import create_app
from app.extensions import socketio

_config_name = 'prod' if os.environ.get('FLASK_ENV') == 'production' else 'dev'
app = create_app(_config_name)

if __name__ == '__main__':
    is_prod = os.environ.get('FLASK_ENV') == 'production'
    socketio.run(
        app,
        host='0.0.0.0',
        port=5555,
        debug=not is_prod,
        allow_unsafe_werkzeug=True,
    )
