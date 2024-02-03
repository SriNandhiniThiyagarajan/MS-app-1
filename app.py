from flask import Flask, render_template, redirect, url_for, flash, request
from models import *
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from sqlalchemy.sql.expression import func
from resources import *
from datetime import datetime,date
import time
import os

# ==========================configuration==========================================================================

app=Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI']="sqlite:///database.sqlite3"
app.config['SECRET_KEY'] = 'my_secret_key'

app.config['UPLOAD_FOLDER'] = 'static/audios'

# api.init_app(app)
db.init_app(app)
app.app_context().push()
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


# =============================controllers========================================================================
ALLOWED_EXTENSIONS = {'mp3', 'wav', 'flac', 'aac','m4a', 'ogg', 'wma', 'alac', 'aiff'}
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@login_manager.user_loader
def load_user(user_id):
    if user_id is not None:
        return User.query.get(int(user_id))
    return None

@app.route('/')
def index():
    return render_template('index.html') 


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()

        if existing_user:
            flash('Username or Email already exists.')
            return render_template('register.html')

        if not password:
            flash('Password should not be empty.')
            return render_template('register.html')

        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.get(current_user.id)
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user and existing_user.id != current_user.id:
            flash('Username or email already exists.')
            return redirect(url_for('profile'))

        if user:
            user.username = username
            user.email = email
            if password: 
                user.password = password

            db.session.commit()
            flash('Profile updated successfully!')
            return redirect(url_for('profile'))
    return render_template('profile.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

# ==========================admin==========================================================================

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('You are not authorized to access this page.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name')
        existing_genre = Genre.query.filter_by(name=name).first()

        if not existing_genre:
            new_genre = Genre(name=name)
            db.session.add(new_genre)
            db.session.commit()
            flash('Genre added successfully!', 'success')
        else:
            flash('Genre already exists.', 'error')


    normal_user_count = User.query.filter_by(is_admin=False).count()
    creator_count = User.query.filter_by(is_creator=True).count()
    track_count = Song.query.count()
    genre_count = Genre.query.count()
    album_count = Album.query.count()
    return render_template('admin_dashboard.html', normal_user_count=normal_user_count, creator_count=creator_count, track_count=track_count, genre_count=genre_count, album_count=album_count)

@app.route('/admin/manage_users')
@login_required
def manage_users():
    users = User.query.all()
    return render_template('manage_users.html', users=users)

@app.route('/admin/blacklist_user/<int:user_id>', methods=['POST'])
@login_required
def blacklist_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blacklisted = True
    db.session.commit()
    flash(f'User {user.username} has been blacklisted.')
    return redirect(url_for('manage_users'))

@app.route('/admin/whitelist_user/<int:user_id>', methods=['POST'])
@login_required
def whitelist_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_blacklisted = False
    db.session.commit()
    flash(f'User {user.username} has been whitelisted.')
    return redirect(url_for('manage_users'))


@app.route('/manage_songs/<int:user_id>')
@login_required 
def manage_songs(user_id):
    user = User.query.get_or_404(user_id)
    songs = Song.query.filter_by(user_id=user.id).all()
    return render_template('manage_songs.html', user=user, songs=songs)

@app.route('/flag_song/<int:song_id>', methods=['POST'])
@login_required
def flag_song(song_id):
    song = Song.query.get_or_404(song_id)
    if current_user.is_admin:
        db.session.delete(song)
        db.session.commit()
        flash('Song deleted successfully!', 'success')
    else:
        flash('You do not have permission to flag this song.', 'error')
    return redirect(url_for('manage_songs', user_id=current_user.id))

# ==========================user==========================================================================
@app.route('/user_dashboard', methods=['GET'])
@login_required
def user_dashboard():
    filter_type = request.args.get('filter_type', '')
    filter_value = request.args.get('filter_value', '')
    query = Song.query
    
    if filter_type and not filter_value:
        if filter_type == 'title':
            flash('No title specified for filtering.')
        elif filter_type == 'rating':
            flash('No rating value specified for filtering.')
        elif filter_type == 'artist':
            flash('No artist name specified for filtering.')
        return render_template('user_dashboard.html', songs=[], genres=[], playlists=[])

    if filter_value:
        if filter_type == 'title':
            query = query.filter(Song.title.ilike(f"%{filter_value}%"))
        elif filter_type == 'rating':
            try:
                rating_value = float(filter_value)
                query = query.join(Ratings).group_by(Song.id).having(db.func.avg(Ratings.rating) == rating_value)
            except ValueError:
                flash('Invalid rating value.')
                return render_template('user_dashboard.html', songs=[], genres=[], playlists=[])
        elif filter_type == 'artist':
            query = query.filter(Song.artist.ilike(f"%{filter_value}%"))

    songs = query.all()
    recommended_songs = Song.query.order_by(func.random()).limit(5).all()
    genres = Genre.query.all()
    albums = Album.query.all()
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('user_dashboard.html',filter_type=filter_type, albums=albums, songs=songs, genres=genres, playlists=playlists, recommended_songs=recommended_songs,current_user=current_user)

@app.route('/handle_creator_status')
@login_required
def handle_creator_status():
    if current_user.is_blacklisted:
        flash("Your account is restricted. Access to creator functionalities is denied.")
        return redirect(url_for('user_dashboard'))

    if current_user.is_creator:
        return redirect(url_for('creator_dashboard'))
    else:
        flash("You are not a creator. Would you like to register as one?")
        return redirect(url_for('ask_creator_registration'))


@app.route('/ask_creator_registration')
@login_required
def ask_creator_registration():
    return render_template('register_as_creator.html')

@app.route('/register_as_creator', methods=['POST'])
@login_required
def register_as_creator():
    current_user.is_creator = True
    db.session.commit()
    flash("You are now registered as a creator!")
    return redirect(url_for('creator_dashboard'))

@app.route('/songs_by_genre/<int:genre_id>')
@login_required
def songs_by_genre(genre_id):
    genre = Genre.query.get_or_404(genre_id)
    songs = Song.query.join(Album).filter(Album.genre_id == genre.id).all()
    return render_template('songs_by_genre.html', songs=songs, genre=genre)

@app.route('/songs_by_album/<int:album_id>')
@login_required
def songs_by_album(album_id):
    album = Album.query.get_or_404(album_id)
    songs = Song.query.filter_by(album_id=album.id).all()
    return render_template('songs_by_album.html', songs=songs, album=album)

@app.route('/view_playlists')
@login_required
def view_playlists():
    playlists = Playlist.query.filter_by(user_id=current_user.id).all()
    return render_template('view_playlists.html', playlists=playlists)

@app.route('/create_playlist', methods=['GET', 'POST'])
@login_required
def create_playlist():
    if request.method == 'POST':
        playlist_name = request.form.get('playlist_name')
        if playlist_name:
            existing_playlist = Playlist.query.filter_by(name=playlist_name, user_id=current_user.id).first()
            if existing_playlist:
                flash('A playlist with this name already exists.')
            else:
                new_playlist = Playlist(name=playlist_name, user_id=current_user.id)
                db.session.add(new_playlist)
                db.session.commit()
                flash('Playlist created successfully.')
                return redirect(url_for('view_playlists'))
        else:
            flash('Please enter a playlist name.')
    return render_template('create_playlist.html')

@app.route('/delete_playlist/<int:playlist_id>', methods=['POST'])
@login_required
def delete_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    if playlist.user_id != current_user.id:
        flash('You do not have permission to delete this playlist.')
        return redirect(url_for('view_playlists'))

    db.session.delete(playlist)
    db.session.commit()
    flash('Playlist deleted successfully.')

    return redirect(url_for('view_playlists'))

@app.route('/add_songs_to_playlist/<int:playlist_id>', methods=['GET', 'POST'])
@login_required
def add_songs_to_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)

    if playlist.user_id != current_user.id:
        flash('You do not have permission to modify this playlist.')
        return redirect(url_for('view_playlists'))

    if request.method == 'POST':
        selected_song_ids = request.form.getlist('song_ids')
        
        for song_id in selected_song_ids:
            existing_association = PlaylistSong.query.filter_by(song_id=song_id, playlist_id=playlist.id).first()
            if not existing_association:
                new_association = PlaylistSong(song_id=song_id, playlist_id=playlist.id)
                db.session.add(new_association)
                
        db.session.commit()
        flash('Songs added to playlist.')
        return redirect(url_for('view_playlists'))

    songs = Song.query.all()
    return render_template('add_songs_to_playlist.html', songs=songs, playlist=playlist)

@app.route('/show_playlist/<int:playlist_id>')
@login_required
def show_playlist(playlist_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        flash('You do not have permission to view this playlist.')
        return redirect(url_for('view_playlists'))
    songs = playlist.songs
    return render_template('show_playlist.html', playlist=playlist, songs=songs)

@app.route('/remove_song_from_playlist/<int:playlist_id>/<int:song_id>', methods=['POST'])
@login_required
def remove_song_from_playlist(playlist_id, song_id):
    playlist = Playlist.query.get_or_404(playlist_id)
    if playlist.user_id != current_user.id:
        flash('You do not have permission to modify this playlist.')
        return redirect(url_for('view_playlists'))

    song = Song.query.get_or_404(song_id)
    if song in playlist.songs:
        playlist.songs.remove(song)
        db.session.commit()
        flash('Song removed from playlist.')
    else:
        flash('Song not found in the playlist.')

    return redirect(url_for('show_playlist', playlist_id=playlist_id))
@app.route('/song/<int:song_id>')
@login_required
def song_detail_copy(song_id):
    song = Song.query.get_or_404(song_id) 
    return render_template('song_detail.html', song=song)

# ==========================creator==========================================================================

@app.route('/creator_dashboard')
@login_required
def creator_dashboard():
    if not current_user.is_creator:
        flash('You are not authorized to view this page.')
        return redirect(url_for('index'))

    album_count = Album.query.filter_by(user_id=current_user.id).count()
    song_count = Song.query.join(Album).filter(Album.user_id == current_user.id).count()

    return render_template('creator_dashboard.html', album_count=album_count, song_count=song_count)


@app.route('/creator_dashboard/upload_song', methods=['GET', 'POST'])
@login_required
def upload_song():
    if request.method == 'POST':
        album_name = request.form.get('album_name')
        genre_id = request.form.get('genre_id')


        existing_album = Album.query.filter_by(name=album_name, user_id=current_user.id).first()
        if existing_album:
            flash('Album already exists!')
            return redirect(url_for('upload_song'))
            
        new_album = Album(
            name=album_name,
            genre_id=genre_id,
            user_id=current_user.id,
        )
        db.session.add(new_album)
        db.session.commit()
        flash('Album created successfully!')
        return redirect(url_for('upload_song'))

    genres = Genre.query.all()
    user_albums = Album.query.filter_by(user_id=current_user.id).all()
    return render_template('upload_song.html', genres=genres, user_albums=user_albums)


@app.route('/album/<int:album_id>/add_song', methods=['GET', 'POST'])
@login_required
def add_song(album_id):
    album = Album.query.get_or_404(album_id)
    if album.user_id != current_user.id:
        flash('You are not authorized to add songs to this album.')
        return redirect(url_for('album_songs', album_id=album.id))

    if request.method == 'POST':
        title = request.form['title']
        artist = request.form['artist']
        duration = request.form['duration'] 
        lyrics = request.form['lyrics']
        file = request.files['file']

        if file and allowed_file(file.filename):
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            filename= '/static/audios/'+ file.filename

            new_song = Song(
                title=title,
                artist=artist,
                duration=duration,
                lyrics=lyrics,
                album_id=album.id,
                user_id=current_user.id,
                filename=filename
            )
            db.session.add(new_song)
            db.session.commit()
            
            flash('Song added successfully!')
            return redirect(url_for('album_songs', album_id=album.id))
        else:
            flash('File not allowed. Please upload files with the following extensions: {}'.format(', '.join(ALLOWED_EXTENSIONS)))
    return render_template('add_song.html', album=album)



@app.route('/album/<int:album_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_album(album_id):
    album = Album.query.get_or_404(album_id)
    genres = Genre.query.all() 

    if album.user_id != current_user.id:
        flash('You are not authorized to edit this album.')
        return redirect(url_for('upload_song'))

    if request.method == 'POST':
        album_name = request.form['album_name']
        genre_id = request.form['genre_id']

        album.name = album_name
        album.genre_id = genre_id
        db.session.commit()
        flash('Album updated successfully!')
        return redirect(url_for('upload_song'))
    return render_template('edit_album.html', album=album, genres=genres)



@app.route('/album/<int:album_id>/delete', methods=['POST'])
@login_required
def delete_album(album_id):
    album = Album.query.get_or_404(album_id)
    if album.user_id != current_user.id:
        flash('You are not authorized to delete this album.', 'error')
        return redirect(url_for('upload_song'))

    for song in album.songs:
        db.session.delete(song)

    db.session.delete(album)
    db.session.commit()
    flash('Album deleted successfully.', 'success')
    return redirect(url_for('upload_song'))


@app.route('/album/<int:album_id>/songs')
@login_required
def album_songs(album_id):
    album = Album.query.get_or_404(album_id)
    if album.user_id != current_user.id:
        flash('You are not authorized to view this album.')
        return redirect(url_for('upload_song'))

    songs = Song.query.filter_by(album_id=album.id).all()
    return render_template('album_songs.html', album=album, songs=songs)

@app.route('/song/<int:song_id>/delete', methods=['POST'])
@login_required
def delete_song(song_id):
    song = Song.query.get_or_404(song_id)
    if song.album.user_id != current_user.id:
        flash('You are not authorized to delete this song.')
        return redirect(url_for('album_songs', album_id=song.album_id))

    album_id = song.album_id
    db.session.delete(song)
    db.session.commit()
    flash('Song has been deleted.')
    return redirect(url_for('album_songs', album_id=album_id))

@app.route('/song/<int:song_id>')
@login_required
def song_detail(song_id):
    song = Song.query.get_or_404(song_id)
    if song.album.user_id != current_user.id:
        flash('You are not authorized to view this song.')
        return redirect(url_for('album_songs', album_id=song.album_id))
    return render_template('song_detail.html', song=song)

@app.route('/rate_song/<int:song_id>', methods=['POST'])
@login_required
def rate_song(song_id):
    song = Song.query.get_or_404(song_id)
    try:
        rating_value = float(request.form.get('rating'))
        if 0 < rating_value <= 5:
            existing_rating = Ratings.query.filter_by(song_id=song.id, user_id=current_user.id).first()
            
            if existing_rating:
                existing_rating.rating = rating_value
            else:
                new_rating = Ratings(rating=rating_value, song_id=song.id, user_id=current_user.id)
                db.session.add(new_rating)

            db.session.commit()
            flash('Rating submitted successfully!', 'success')
        else:
            flash('Invalid rating. Please rate between 1 and 5.', 'error')
    except ValueError:
        flash('Invalid input for rating.', 'error')

    return redirect(url_for('song_detail', song_id=song_id))


@app.route('/edit_song/<int:song_id>', methods=['GET', 'POST'])
@login_required
def edit_song(song_id):
    song = Song.query.get_or_404(song_id)
    if song.user_id != current_user.id:
        flash('You do not have permission to edit this song.')
        return redirect(url_for('album_songs', album_id=song.album_id))

    if request.method == 'POST':
        song.title = request.form['title']
        song.artist = request.form['artist']
        song.duration = request.form['duration']
        song.lyrics = request.form['lyrics']
        db.session.commit()
        flash('Song updated successfully.')
        return redirect(url_for('album_songs', album_id=song.album_id))

    return render_template('edit_song.html', song=song)


with app.app_context():
        db.create_all()
if __name__=="__main__":
    app.run(debug=True)
