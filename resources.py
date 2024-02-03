from flask_restful import Api, Resource, reqparse
from flask import Flask,url_for
from models import *

api = Api()

# ==========================Api foor user ==========================================================================

user_parser = reqparse.RequestParser()
user_parser.add_argument('username', type=str, required=True, help="Username cannot be blank")
user_parser.add_argument('email', type=str, required=True, help="Email cannot be blank")
user_parser.add_argument('password', type=str)
user_parser.add_argument('is_creator', type=bool)
user_parser.add_argument('is_admin', type=bool)
user_parser.add_argument('is_blacklisted', type=bool)

class UserResource(Resource):
    def get(self, user_id):
        user = User.query.get(user_id)
        if user:
            return {'username': user.username, 'email': user.email}, 200
        return {'message': 'User not found'}, 404

    def put(self, user_id):
        args = user_parser.parse_args()
        user = User.query.get(user_id)
        if user:
            user.username = args['username']
            user.email = args['email']
            user.password=args['password']
            db.session.commit()
            return {'message': 'User updated'}, 200
        return {'message': 'User not found'}, 404

class UserListResource(Resource):
    def get(self):
        users = User.query.all()
        return [{'username': user.username, 'email': user.email} for user in users], 200

    def post(self):
        args = user_parser.parse_args()
        new_user = User(username=args['username'], email=args['email'], password=args['password'])
        db.session.add(new_user)
        db.session.commit()
        return {'message': 'User created Successfully', 'user_id': new_user.id}, 201


api.add_resource(UserResource, '/users/<int:user_id>')
api.add_resource(UserListResource, '/users')



# ==============================================album===========================================================================

album_parser = reqparse.RequestParser()
album_parser.add_argument('name', type=str, required=True, help="Name cannot be blank")
album_parser.add_argument('release_date', type=lambda x: datetime.strptime(x, '%Y-%m-%d').date())
album_parser.add_argument('genre_id', type=int, required=True, help="Genre ID cannot be blank")
album_parser.add_argument('user_id', type=int, required=True, help="User ID cannot be blank")

class AlbumResource(Resource):
    def get(self, album_id):
        album = Album.query.get(album_id)
        if album:
            return {
                'name': album.name, 
                'release_date': album.release_date.strftime('%Y-%m-%d'), 
                'genre_id': album.genre_id,
                'user_id': album.user_id
            }, 200
        return {'message': 'Album not found'}, 404

    def delete(self, album_id):
        album = Album.query.get(album_id)
        if album:
            db.session.delete(album)
            db.session.commit()
            return {'message': 'Album deleted'}, 200
        return {'message': 'Album not found'}, 404

    def put(self, album_id):
        args = album_parser.parse_args()
        album = Album.query.get(album_id)
        if album:
            album.name = args['name']
            album.release_date = args['release_date'] if args['release_date'] else album.release_date
            album.genre_id = args['genre_id']
            album.user_id = args['user_id']
            db.session.commit()
            return {'message': 'Album updated'}, 200
        return {'message': 'Album not found'}, 404

class AlbumListResource(Resource):
    def get(self):
        albums = Album.query.all()
        return [{
            'name': album.name, 
            'release_date': album.release_date.strftime('%Y-%m-%d'), 
            'genre_id': album.genre_id,
            'user_id': album.user_id
        } for album in albums], 200

    def post(self):
        args = album_parser.parse_args()
        new_album = Album(
            name=args['name'],
            release_date=args['release_date'] if args['release_date'] else date.today(),
            genre_id=args['genre_id'],
            user_id=args['user_id']
        )
        db.session.add(new_album)
        db.session.commit()
        return {'message': 'Album created', 'album_id': new_album.id}, 201

api.add_resource(AlbumResource, '/albums/<int:album_id>')
api.add_resource(AlbumListResource, '/albums')


# ==============================================songs===========================================================================

song_parser = reqparse.RequestParser()
song_parser.add_argument('title', type=str, required=True, help="Title cannot be blank")
song_parser.add_argument('artist', type=str, required=True, help="Artist cannot be blank")
song_parser.add_argument('duration', type=float)
song_parser.add_argument('lyrics', type=str)
song_parser.add_argument('filename', type=str, required=True, help="Filename cannot be blank")
song_parser.add_argument('album_id', type=int, required=True, help="Album ID cannot be blank")
song_parser.add_argument('user_id', type=int, required=True, help="User ID cannot be blank")


class SongResource(Resource):
    def get(self, song_id):
        song = Song.query.get(song_id)
        if song:
            file_url = url_for('static', filename=f'audios/{song.filename}', _external=True)
            return {
                'title': song.title,
                'artist': song.artist,
                'duration': song.duration,
                'lyrics': song.lyrics,
                'date_added': song.date_added.strftime('%Y-%m-%d %H:%M:%S'),
                'filename': file_url,
                'album_id': song.album_id,
                'user_id': song.user_id
            }, 200
        return {'message': 'Song not found'}, 404

    def put(self, song_id):
        song = Song.query.get(song_id)
        if song:
            args = song_parser.parse_args()
            song.title = args['title']
            song.artist = args['artist']
            song.duration = args['duration']
            song.lyrics = args['lyrics']
            song.album_id = args['album_id']
            song.user_id = args['user_id']
            db.session.commit()
            return {'message': 'Song updated'}, 200
        return {'message': 'Song not found'}, 404

    def delete(self, song_id):
        song = Song.query.get(song_id)
        if song:
            db.session.delete(song)
            db.session.commit()
            return {'message': 'Song deleted'}, 200
        return {'message': 'Song not found'}, 404

class SongListResource(Resource):
    def get(self):
        songs = Song.query.all()
        return [{
            'title': song.title,
            'artist': song.artist,
            'duration': song.duration,
            'lyrics': song.lyrics,
            'date_added': song.date_added.strftime('%Y-%m-%d %H:%M:%S'),
            'filename': url_for('static', filename=f'audios/{song.filename}', _external=True),
            'album_id': song.album_id,
            'user_id': song.user_id
        } for song in songs], 200

    def post(self):
        args = song_parser.parse_args()
        new_song = Song(
            title=args['title'],
            artist=args['artist'],
            duration=args['duration'],
            lyrics=args['lyrics'],
            filename=args['filename'],
            album_id=args['album_id'],
            user_id=args['user_id']
        )
        db.session.add(new_song)
        db.session.commit()
        return {'message': 'Song created', 'song_id': new_song.id}, 201


api.add_resource(SongResource, '/songs/<int:song_id>')
api.add_resource(SongListResource, '/songs')
# ==============================================Playlist===========================================================================

class PlaylistResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=str, required=True, help="Name cannot be blank")

    def get(self, playlist_id):
        playlist = Playlist.query.get(playlist_id)
        if playlist:
            return {'name': playlist.name}, 200
        return {'message': 'Playlist not found'}, 404

    def put(self, playlist_id):
        data = PlaylistResource.parser.parse_args()
        playlist = Playlist.query.get(playlist_id)

        if playlist:
            playlist.name = data['name']
            db.session.commit()
            return {'message': 'Playlist updated successfully'}, 200
        return {'message': 'Playlist not found'}, 404

    def delete(self, playlist_id):
        playlist = Playlist.query.get(playlist_id)
        if playlist:
            db.session.delete(playlist)
            db.session.commit()
            return {'message': 'Playlist deleted'}, 200
        return {'message': 'Playlist not found'}, 404


class PlaylistListResource(Resource):
    def get(self):
        playlists = Playlist.query.all()
        return {'playlists': [{'id': playlist.id, 'name': playlist.name} for playlist in playlists]}

    def post(self):
        data = PlaylistResource.parser.parse_args()
        new_playlist = Playlist(name=data['name'], user_id=1)
        db.session.add(new_playlist)
        db.session.commit()
        return {'message': 'New playlist created', 'playlist_id': new_playlist.id}, 201

api.add_resource(PlaylistResource, '/playlists/<int:playlist_id>')
api.add_resource(PlaylistListResource, '/playlists')

# ==============================================playlistsong===========================================================================

class PlaylistSongResource(Resource):
    parser = reqparse.RequestParser()
    parser.add_argument('song_id', type=int, required=True, help="Song ID cannot be blank")

    def post(self, playlist_id):
        data = PlaylistSongResource.parser.parse_args()
        if not Playlist.query.get(playlist_id):
            return {'message': 'Playlist not found'}, 404

        if not Song.query.get(data['song_id']):
            return {'message': 'Song not found'}, 404

        new_playlist_song = PlaylistSong(playlist_id=playlist_id, song_id=data['song_id'])
        db.session.add(new_playlist_song)
        db.session.commit()

        return {'message': 'Song added to playlist'}, 201

    def delete(self, playlist_id, song_id):
        playlist_song = PlaylistSong.query.filter_by(playlist_id=playlist_id, song_id=song_id).first()
        if playlist_song:
            db.session.delete(playlist_song)
            db.session.commit()
            return {'message': 'Song removed from playlist'}, 200
        return {'message': 'Song not found in the specified playlist'}, 404

api.add_resource(PlaylistSongResource, '/playlists/<int:playlist_id>/songs', '/playlists/<int:playlist_id>/songs/<int:song_id>')










