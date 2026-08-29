from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Deine API-Keys hier eintragen:
GENIUS_ACCESS_TOKEN = "GqdoiVXhVJ_F0PqUn3LDWgpfaaZhx_ssWFmcau2I90ACr3DF9xP2U8EXox-pCjIx"
SPOTIFY_CLIENT_ID = "91c3e6a4cf0e46c394fa9412ef865947"
SPOTIFY_CLIENT_SECRET = "b2faac29494741a589ea872ae345e49b"

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
        return None, None
    
    headers = {'Authorization': f'Bearer {token}'}
    # Bereinige den Titel von Klammern für eine bessere Spotify-Suche
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
            return cover, preview
    except Exception as e:
        print(f"Spotify Search Error: {e}")
        
    return None, None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    lyrics_snippet = request.form.get('query')
    print(f"\n--- Neue Suche gestartet für: '{lyrics_snippet}' ---")
    
    if not lyrics_snippet:
        return jsonify({'results': []})

    headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
    genius_url = "https://api.genius.com/search"
    
    try:
        res = requests.get(genius_url, headers=headers, params={'q': lyrics_snippet}, timeout=5)
        print(f"Genius Status-Code: {res.status_code}")
        
        if res.status_code != 200:
            print(f"Genius Fehler-Antwort: {res.text}")
            return jsonify({'results': []})
            
        data = res.json()
        hits = data.get('response', {}).get('hits', [])
        print(f"Genius Treffer Anzahl: {len(hits)}")
        
    except Exception as e:
        print(f"Genius API Exception: {e}")
        return jsonify({'results': []})

    results = []

    for hit in hits[:5]:
        result_item = hit['result']
        title = result_item['title']
        artist = result_item['primary_artist']['name']
        genius_cover = result_item.get('song_art_image_thumbnail_url')
        
        # Versuche Spotify-Cover zu holen
        spotify_cover, preview = get_spotify_details(title, artist)
        final_cover = spotify_cover if spotify_cover else genius_cover

        results.append({
            'title': title,
            'artist': artist,
            'cover': final_cover,
            'preview': preview,
            'url': result_item['url']
        })

    return jsonify({'results': results})

    results = []

    for hit in hits[:5]:
        result_item = hit['result']
        title = result_item['title']
        artist = result_item['primary_artist']['name']
        genius_cover = result_item.get('song_art_image_thumbnail_url')
        
        # Versuche Spotify-Cover zu holen
        spotify_cover, preview = get_spotify_details(title, artist)
        
        # Fallback auf Genius-Cover, falls Spotify kein Bild liefert
        final_cover = spotify_cover if spotify_cover else genius_cover

        results.append({
            'title': title,
            'artist': artist,
            'cover': final_cover,
            'preview': preview,
            'url': result_item['url']
        })

    return jsonify({'results': results})

@app.route('/impressum')
def impressum():
    return render_template('impressum.html')

@app.route('/datenschutz')
def datenschutz():
    return render_template('datenschutz.html')

if __name__ == '__main__':
    app.run(debug=True)