from flask_login import current_user
from flask_socketio import join_room, leave_room
from app.extensions import db
from app.models.match import Match


def register_match_sockets(socketio):
    @socketio.on('join')
    def on_join(data):
        match_id = data.get('match_id')
        token = data.get('token')
        if not match_id:
            return
        match = db.session.get(Match, match_id)
        if match is None:
            return
        if current_user.is_authenticated and match.is_participant(current_user):
            join_room(f'match-{match_id}')
        elif token and match.public_token == token:
            join_room(f'match-{match_id}')

    @socketio.on('leave')
    def on_leave(data):
        match_id = data.get('match_id')
        if match_id:
            leave_room(f'match-{match_id}')
