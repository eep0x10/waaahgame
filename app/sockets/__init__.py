def register_sockets(socketio):
    from .match import register_match_sockets
    register_match_sockets(socketio)
