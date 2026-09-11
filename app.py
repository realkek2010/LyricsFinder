from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
import re
import os
from langdetect import detect, LangDetectException

app = Flask(__name__)

# API-Keys
GENIUS_ACCESS_TOKEN = "GqdoiVXhVJ_F0PqUn3LDWgpfaaZhx_ssWFmcau2I90ACr3DF9xP2U8EXox-pCjIx"
SPOTIFY_CLIENT_ID = "91c3e6a4cf0e46c394fa9412ef865947"
SPOTIFY_CLIENT_SECRET = "b2faac29494741a589ea872ae345e49b"

def is_original_track(title):
    """
    Prüft, ob der Song ein Original ist.
    Filtert Remixes, Instrumentals, Live-Versionen, Covers etc. heraus.
    """
    forbidden_terms = [
        r'\bremix\b', r'\binstrumental\b', r'\bcover\b', r'\blive\b',
        r'\bedit\b', r'\bspeed up\b', r'\bslowed\b', r'\bkaraoke\b',
        r'\btribute\b', r'\bacoustic\b', r'\bversion\b', r'\bmix\b'
    ]
    title_lower = title.lower()
    for term in forbidden_terms:
        if re.search(term, title_lower):
            return False
    return True

def detect_language_text(text):
    """Erkennt die Sprache eines Textes (z. B. de, en, fr, es, it, etc.)."""
    try:
        if len(text.strip()) < 3:
            return "unknown"
        return detect(text)
    except LangDetectException:
        return "unknown"

def get_spotify_token():
    auth_url = 'https://accounts.spotify.com/api/token'
    try:
        res = requests.post(auth_url, {
            'grant_type': 'client_credentials',
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET,
        }, timeout=5)
        return res.json().get('access_token')
    except Exception as e:
        print(f"Spotify Token Error: {e}")
        return None

def get_spotify_details(title, artist):
    token = get_spotify_token()
    if not token:
        return None, None, None, None
    
    headers = {'Authorization': f'Bearer {token}'}
    clean_title = title.split('(')[0].split('-')[0].strip()
    query = f"{clean_title} {artist}"
    url = f"https://api.spotify.com/v1/search?q={requests.utils.quote(query)}&type=track&limit=1"
    
    try:
        res = requests.get(url, headers=headers, timeout=5).json()
        tracks = res.get('tracks', {}).get('items', [])
        
        if tracks:
            track = tracks[0]
            cover = track['album']['images'][0]['url'] if track['album']['images'] else None
            preview = track.get('preview_url')
            spotify_url = track['external_urls'].get('spotify')
            
            # Release-Jahr extrahieren
            raw_date = track.get('album', {}).get('release_date', '')
            release_date = raw_date[:4] if raw_date else "N/A"
            
            return cover, preview, spotify_url, release_date
    except Exception as e:
        print(f"Spotify Search Error: {e}")
        
    return None, None, None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/download')
def download_page():
    return render_template('download.html')

@app.route('/download/apk')
def download_apk():
    # Sendet die APK-Datei aus dem static-Ordner
    static_folder = os.path.join(app.root_path, 'static')
    return send_from_directory(static_folder, 'LyricsFinder.apk', as_attachment=True)

@app.route('/search', methods=['POST'])
def search():
    lyrics_snippet = request.form.get('query')
    selected_language = request.form.get('language', 'all')
    print(f"\n--- Neue Suche gestartet für: '{lyrics_snippet}' (Sprachfilter: {selected_language}) ---")
    
    if not lyrics_snippet:
        return jsonify({'results': []})

    headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
    genius_url = "https://api.genius.com/search"
    
    try:
        res = requests.get(genius_url, headers=headers, params={'q': lyrics_snippet}, timeout=5)
        
        if res.status_code != 200:
            print(f"Genius Fehler-Antwort: {res.text}")
            return jsonify({'results': []})
            
        data = res.json()
        hits = data.get('response', {}).get('hits', [])
        
    except Exception as e:
        print(f"Genius API Exception: {e}")
        return jsonify({'results': []})

    results = []

    for hit in hits:
        result_item = hit['result']
        title = result_item['title']
        artist = result_item['primary_artist']['name']

        # Filter: Nur Original-Tracks verarbeiten (keine Remixes, Instrumentals etc.)
        if not is_original_track(title):
            continue

        genius_cover = result_item.get('song_art_image_thumbnail_url')
        
        raw_genius_url = result_item.get('url', '')
        if raw_genius_url and not raw_genius_url.startswith('http'):
            genius_song_url = f"https://genius.com{raw_genius_url}"
        else:
            genius_song_url = raw_genius_url

        # Spracherkennung durchführen
        detected_lang = detect_language_text(f"{lyrics_snippet} {title}")

        # Prüfen, ob eine Sprachabweichung vorliegt
        language_mismatch = False
        if selected_language != 'all':
            if detected_lang != selected_language:
                language_mismatch = True

        # Spotify-Details abfragen (inklusive release_date)
        spotify_cover, preview, spotify_url, release_date = get_spotify_details(title, artist)
        
        final_cover = spotify_cover if spotify_cover else genius_cover
        final_spotify_url = spotify_url if spotify_url else genius_song_url

        results.append({
            'title': title,
            'artist': artist,
            'cover': final_cover,
            'preview': preview,
            'release_date': release_date if release_date else "N/A",
            'spotify_url': final_spotify_url,
            'genius_url': genius_song_url,
            'detected_language': detected_lang,
            'language_mismatch': language_mismatch
        })

        if len(results) >= 5:
            break

    return jsonify({'results': results})

@app.route('/impressum')
def impressum():
    return render_template('impressum.html')

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')

if __name__ == '__main__':
    app.run(debug=True)
