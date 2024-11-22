from dataclasses import dataclass
import os
from pathlib import Path
import sys
import requests
import yt_dlp
from tqdm import tqdm
from dotenv import load_dotenv


@dataclass
class Song:
    title: str
    album: str
    artist: str

    def searchable(self) -> str:
        return f'{self.title} - {self.artist}'


def get_access_token(client_id, client_secret):
    url = "https://accounts.spotify.com/api/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {"grant_type": "client_credentials"}
    for _ in tqdm([None], "Getting Access Token"):
        response = requests.post(url, headers=headers, data=data, auth=(client_id, client_secret))

    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        print(f"Failed to get access token: {response.json()}")
        sys.exit(1)


def search_artist(artist_name, token):
    url = "https://api.spotify.com/v1/search"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": artist_name, "type": "artist", "limit": 1}

    for _ in tqdm([None], f"Seraching Artist '{artist_name}'"):
        response = requests.get(url, headers=headers, params=params)
    
    if response.status_code == 200:
        results = response.json()
        if results["artists"]["items"]:
            return results["artists"]["items"][0]["id"]
        else:
            print("Artist not found.")
            sys.exit(1)
    else:
        print(f"Failed to search artist: {response.json()}")
        sys.exit(1)


def get_artist_albums(artist_id, token):
    url = f"https://api.spotify.com/v1/artists/{artist_id}/albums"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"include_groups": "album,single", "limit": 50}
    albums = []

    with tqdm(desc="Fetching Albums") as progress_reporter:
        while url:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                albums.extend(data["items"])
                url = data.get("next")  # Pagination
                progress_reporter.update(1)
            else:
                print(f"Failed to get albums: {response.json()}")
                sys.exit(1)

    return albums


def get_album_tracks(album_id, token):
    url = f"https://api.spotify.com/v1/albums/{album_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json()["items"]
    else:
        print(f"Failed to get album tracks: {response.json()}")
        sys.exit(1)


def get_all_songs(artist_name):
    token = get_access_token(os.getenv("SPOTIFY_CLIENT_ID"), os.getenv("SPOTIFY_CLIENT_SECRET"))
    artist_id = search_artist(artist_name, token)
    albums = get_artist_albums(artist_id, token)

    songs = []
    for album in tqdm(albums, "Fetching Albums Tracks"):
        tracks = get_album_tracks(album["id"], token)
        for track in tracks:
            songs.append(Song(track["name"], album["name"], artist_name))

    return songs


def download_song(song, download_path):
    os.makedirs(download_path, exist_ok=True)
    path = download_path / f'{song.title} - {song.artist}'
    if path.exists():
        return

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': str(path),
        'quiet': True,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            print(f"Searching and downloading: {song}")
            # Use yt-dlp to search and download
            ydl.download([f"ytsearch:{song.searchable()}"])
        except Exception as e:
            print(f"Failed to download {song}: {e}")


if __name__ == "__main__":
    load_dotenv()    
    artists = []
    while True:
        artist_name = input("Enter the artist's name: ").strip()
        if artist_name == "":
            break
        artists.append(artist_name)
    
    for artist_name in tqdm(artists, f"Looping Over {len(artists)} Artists"):
        download_path = Path.home() / "Downloads" / artist_name
        songs = get_all_songs(artist_name)

        for song in tqdm(songs, "Downloading Songs"):
            download_song(song, download_path)
