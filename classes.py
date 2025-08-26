import requests
import os
import json
import pandas as pd
import numpy as np

from consts import PATH
from utils import get_headers, choose_artist_headless


class Song:
    def __init__(self, name, song_id, song_num, album):
        self.name = name
        self.song_id = song_id
        self.song_num = song_num
        self.album = album
        self.artist = self.album.artist
        self.total_album_songs = self.album.num_songs
        self.popularity = None
        # self.preview_url = None  # URL to the song's preview
        self.duration_ms = None  # Song duration in milliseconds
        self.rank_value = None  # Store the song's rank
        # Removed audio_widget and preview_file

    def fetch_song_details(self):
        """Fetches details about the song from Spotify API."""
        song_details_url = f'https://api.spotify.com/v1/tracks/{self.song_id}'
        headers = get_headers()

        response = requests.get(song_details_url, headers=headers)

        if response.status_code == 200:
            song_data = response.json()
            self.popularity = song_data.get('popularity')
            self.duration_ms = song_data.get('duration_ms')
            # self.preview_url = song_data.get('preview_url')
        else:
            print(f"Error fetching song details for {self.name}: {response.status_code}")

    def set_rank(self, rank_value):
        """Set the rank value for the song."""
        self.rank_value = rank_value
        # This will be called by the GUI when the user sets a rank

    def __repr__(self):
        return f"Song(name='{self.name}', rank_value={self.rank_value})"


class Album:
    def __init__(self, name, album_id, artist, cover_url=None, release_year=None):
        self.name = name
        self.album_id = album_id
        self.cover_url = cover_url  # Album cover image URL
        self.release_year = release_year  # Year the album was released
        self.songs = None  # List of Song objects
        self.ranks = None # numpy array of ranks or nan
        self.e_value = None # Cohesive experience score
        self.r_value = None # Replayability score
        self.s_value = None  # Average song score
        self.final_score = None
        self.artist = artist
        self.num_songs = 0

    def fetch_songs(self):
        """Fetches the songs in this album from the Spotify API."""
        if self.songs is None:
            songs_url = f'https://api.spotify.com/v1/albums/{self.album_id}/tracks'
            headers = get_headers()

            response = requests.get(songs_url, headers=headers)

            if response.status_code == 200:
                tracks_data = response.json()
                self.num_songs = len(tracks_data['items'])
                self.songs = [Song(track['name'], track['id'], i+1, self)
                              for i, track in enumerate(tracks_data['items'])]
                if self.ranks is not None and len(self.ranks) == len(self.songs):
                     # Apply loaded ranks if available and match song count
                     for song, rank in zip(self.songs, self.ranks):
                        song.rank_value = rank if pd.notna(rank) else None
                else:
                    # Initialize ranks with None if no saved data or mismatch
                    self.ranks = np.array([None] * self.num_songs, dtype=object)
            else:
                print(f"Error fetching songs for album {self.name}: {response.status_code}")
                self.songs = []
                self.num_songs = 0
                self.ranks = np.array([], dtype=object)


    # Removed display_cover, get_experience_and_replay, rank methods
    # These will be handled by the GUI

    def calculate_final_score(self):
        """Calculate the final score of the album."""
        self.get_s() # Ensure s_value is updated
        if pd.isna(self.s_value) or self.e_value is None or self.r_value is None:
            self.final_score = None
        else:
            # Formula as previously defined
            self.final_score = max([min([self.s_value + (self.e_value + self.r_value)/10 - 1, 10.]), 0.])

    def get_final_score(self):
        """Return the final score, recalculating if needed."""
        self.calculate_final_score()
        return self.final_score

    def set_ranks(self, ranks_list):
        """Set the ranks from a list (e.g., loaded from JSON)."""
        # Convert list of ranks (including None) to numpy array with nan for missing
        self.ranks = np.array([rank if rank is not None else np.nan for rank in ranks_list], dtype=object)
        if self.songs is not None and len(self.ranks) == len(self.songs):
            for song, rank in zip(self.songs, self.ranks):
                 song.rank_value = rank if pd.notna(rank) else None
        # Recalculate scores after setting ranks
        self.calculate_final_score()

    def get_s(self, weighted=False):
        """Calculate the average song score (s_value), optionally weighted by duration."""
        self.fetch_songs()

        # Update internal ranks array from Song objects
        if self.songs:
            self.ranks = np.array([song.rank_value if song.rank_value is not None else np.nan for song in self.songs])

            if not weighted:
                if np.isnan(self.ranks).all() or len(self.ranks) == 0:
                    self.s_value = np.nan
                else:
                    # Use pandas Series for easier handling of NaN in mean calculation
                    self.s_value = pd.Series(self.ranks).mean()
            else:
                # Fetch song details including duration if needed for weighted average
                if any(song.duration_ms is None and song.rank_value is not None for song in self.songs):
                    for song in self.songs:
                        if song.rank_value is not None and song.duration_ms is None:
                             song.fetch_song_details() # Fetch details only if needed

                valid_ranks_weights = [(song.rank_value, song.duration_ms) for song in self.songs if song.rank_value is not None and song.duration_ms is not None]

                if not valid_ranks_weights:
                    self.s_value = np.nan
                else:
                    ranks = np.array([item[0] for item in valid_ranks_weights])
                    weights = np.array([item[1] for item in valid_ranks_weights])
                    self.s_value = np.average(ranks, weights=weights)

        return self.s_value

    def set_e_r(self, e_value, r_value):
        """Set the album's experience and replayability scores."""
        self.e_value = e_value
        self.r_value = r_value
        self.calculate_final_score() # Recalculate final score

    def load_from_dict(self, data):
        """Load album data from a dictionary (e.g., from JSON)."""
        # Set ranks using the dedicated method which also updates song objects
        ranks_data = data.get('ranks')
        if ranks_data is not None:
             self.fetch_songs()
             self.set_ranks(ranks_data)

        self.e_value = data.get('e', None)
        self.r_value = data.get("r", None)
        # Recalculate s_value and final_score based on loaded data
        self.get_s()
        self.calculate_final_score()

    def dump(self):
        """Dump album data to a dictionary for saving."""
        # Ensure ranks array is updated from Song objects before dumping
        if self.songs:
             self.ranks = np.array([song.rank_value if song.rank_value is not None else np.nan for song in self.songs], dtype=object)

        # Convert numpy array of ranks (including np.nan) to a list (converting nan to None for JSON compatibility)
        ranks_list = [rank if pd.notna(rank) else None for rank in self.ranks]

        # Only dump if there is any ranking data
        if any(rank is not None for rank in ranks_list) or self.e_value is not None or self.r_value is not None:
            return {
                'ranks': ranks_list,
                'e': self.e_value,
                'r': self.r_value,
                's': self.s_value # Include s_value in dump, although it's calculated
            }
        else:
            return None # Don't dump if no ranking data exists

    def show_rank(self):
        """Return a DataFrame representing the album's rankings."""
        # Ensure scores are updated before creating DataFrame
        self.get_s()
        self.calculate_final_score()

        song_ranking_data = [{"name": song.name, "score": song.rank_value} for song in self.songs]

        album_summary_data = [
            {"name": "Song average", "score": self.s_value},
            {"name": "Cohesive experience", "score": self.e_value},
            {"name": "Replayability", "score": self.r_value},
            {"name": "Total score", "score": self.get_final_score()}
        ]

        df = pd.DataFrame(song_ranking_data + album_summary_data)
        return df


class Artist:
    def __init__(self, name=None, path=PATH):
        self.name = name # This will be updated after fetching the artist ID
        self.path = path
        # Use the refactored headless choose_artist
        self.artist_id = choose_artist_headless(name)
        if self.artist_id is None:
             raise ValueError(f"Artist '{name}' not found.")

        self.name = self.fetch_artist_name() # Fetch and set the official artist name
        self.albums = None
        self.fetch_albums() # Fetch albums after getting artist ID and name
        # Removed ipywidgets related attributes like album_dropdown

    def fetch_artist_name(self):
        """Fetches the official artist name from Spotify."""
        artist_url = f'https://api.spotify.com/v1/artists/{self.artist_id}'
        headers = get_headers()

        try:
            response = requests.get(artist_url, headers=headers)
            response.raise_for_status() # Raise an exception for bad status codes
            artist_data = response.json()
            return artist_data['name']
        except requests.exceptions.RequestException as e:
            print(f"Error fetching artist name for ID {self.artist_id}: {e}")
            return "Unknown Artist" # Return a default name or handle error as appropriate

    def fetch_albums(self):
        """Fetches the albums for this artist from the Spotify API."""
        if self.albums is None:
            albums_url = f'https://api.spotify.com/v1/artists/{self.artist_id}/albums'
            headers = get_headers()
            params = {
                'include_groups': 'album',
                'limit': 50
            }

            try:
                response = requests.get(albums_url, headers=headers, params=params)
                response.raise_for_status() # Raise an exception for bad status codes
                albums_data = response.json()
                album_objects = []
                for album_data in albums_data.get('items', []):
                    cover_url = album_data['images'][0]['url'] if album_data.get('images') else None
                    # Extract release year safely, handle potential errors
                    release_year = album_data.get('release_date', 'Unknown').split("-")[0]
                    album_objects.append(Album(album_data.get('name', 'Unknown Album'), album_data.get('id'), self, cover_url, release_year))
                self.albums = album_objects
                self.load_ranking() # Attempt to load ranking data after fetching albums
            except requests.exceptions.RequestException as e:
                print(f"Error fetching albums for artist {self.name}: {e}")
                self.albums = [] # Initialize with an empty list if fetching fails

    def to_dict(self):
        """Convert the artist's ranking data to a dictionary for saving."""
        # Use album.dump() which already handles returning None for unranked albums
        album_rankings = {album.name: album.dump() for album in self.albums if album.dump() is not None}
        return album_rankings

    def save_rankings(self):
        """Save the ranking information of all albums in the artist to a JSON file."""
        ranking_data = self.to_dict()
        # Ensure the directory exists before saving
        os.makedirs(self.path, exist_ok=True)
        file_path = os.path.join(self.path, f"{self.name}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(ranking_data, f, indent=4)
            # print(f"Rankings saved to {file_path}") # Optional: Add confirmation message
        except IOError as e:
            print(f"Error saving rankings to {file_path}: {e}")

    def load_ranking(self):
        """Load the ranking information for the artist from a JSON file."""
        file_path = os.path.join(self.path, f"{self.name}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                # Assuming albums are already fetched before calling load_ranking
                if self.albums is not None:
                    for album in self.albums:
                        if album.name in data:
                            album.load_from_dict(data[album.name])
                # print(f"Rankings loaded from {file_path}") # Optional: Add confirmation message
            except (IOError, json.JSONDecodeError) as e:
                print(f"Error loading rankings from {file_path}: {e}")
        else:
            print(f"No ranking file found at {file_path}") # Optional: Add info message

    def sorted_albums(self):
        """Return a DataFrame of ranked albums sorted by final score."""
        # Filter albums that have a final score and sort them
        ranked_albums = [album for album in self.albums if album.get_final_score() is not None]
        # Sort albums by final score in descending order
        ranked_albums.sort(key=lambda album: album.final_score, reverse=True)

        if not ranked_albums:
            return pd.DataFrame({"name": [], "year": [], "score": []}) # Return empty DataFrame if no albums are ranked

        df = pd.DataFrame({
            "name": [album.name for album in ranked_albums],
            "year": [album.release_year for album in ranked_albums],
            "score": [album.final_score for album in ranked_albums]
        })
        return df


    # show_ranking method will be replaced by GUI display logic


    def __repr__(self):
        return f"Artist(name='{self.name}', id='{self.artist_id}')"

