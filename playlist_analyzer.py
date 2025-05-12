import streamlit as st
import re
import pandas as pd

# Define musical key mappings (Camelot wheel)
KEY_NAMES = {
    0: "C",
    1: "C♯/D♭",
    2: "D",
    3: "D♯/E♭",
    4: "E",
    5: "F",
    6: "F♯/G♭",
    7: "G",
    8: "G♯/A♭",
    9: "A",
    10: "A♯/B♭",
    11: "B"
}

CAMELOT_WHEEL = {
    (0, 1): "8B",   # C Major
    (0, 0): "5A",   # C Minor
    (1, 1): "3B",   # C#/Db Major
    (1, 0): "12A",  # C#/Db Minor
    (2, 1): "10B",  # D Major
    (2, 0): "7A",   # D Minor
    (3, 1): "5B",   # D#/Eb Major
    (3, 0): "2A",   # D#/Eb Minor
    (4, 1): "12B",  # E Major
    (4, 0): "9A",   # E Minor
    (5, 1): "7B",   # F Major
    (5, 0): "4A",   # F Minor
    (6, 1): "2B",   # F#/Gb Major
    (6, 0): "11A",  # F#/Gb Minor
    (7, 1): "9B",   # G Major
    (7, 0): "6A",   # G Minor
    (8, 1): "4B",   # G#/Ab Major
    (8, 0): "1A",   # G#/Ab Minor
    (9, 1): "11B",  # A Major
    (9, 0): "8A",   # A Minor
    (10, 1): "6B",  # A#/Bb Major
    (10, 0): "3A",  # A#/Bb Minor
    (11, 1): "1B",  # B Major
    (11, 0): "10A"  # B Minor
}

def extract_playlist_id(playlist_url):
    """
    Extract playlist ID from Spotify playlist URL.
    
    Args:
        playlist_url (str): Spotify playlist URL
        
    Returns:
        str: Playlist ID or None if not found
    """
    patterns = [
        r'playlist/([a-zA-Z0-9]+)',  # Standard format
        r'playlist:([a-zA-Z0-9]+)',  # URI format
        r'playlist/([a-zA-Z0-9]+)\?',  # URL with query params
    ]
    
    for pattern in patterns:
        match = re.search(pattern, playlist_url)
        if match:
            return match.group(1)
    
    return None

def fetch_playlist_tracks(spotify_client, playlist_url):
    """
    Fetch tracks from a Spotify playlist URL.
    
    Args:
        spotify_client: Authenticated Spotify client
        playlist_url (str): Spotify playlist URL
        
    Returns:
        list: List of track information dictionaries
    """
    # Extract playlist ID from the URL
    playlist_id = extract_playlist_id(playlist_url)
    
    if not playlist_id:
        raise ValueError("Invalid Spotify playlist URL format")
    
    # Get playlist information
    playlist_info = spotify_client.playlist(playlist_id)
    playlist_name = playlist_info['name']
    
    # Fetch all tracks from the playlist
    results = spotify_client.playlist_items(playlist_id)
    tracks = results['items']
    
    while results['next']:
        results = spotify_client.next(results)
        tracks.extend(results['items'])
    
    # Extract relevant track information
    tracks_info = []
    
    for i, item in enumerate(tracks):
        track = item['track']
        
        # Skip if track is None (e.g., unavailable in region)
        if track is None:
            continue
            
        track_info = {
            'position': i + 1,
            'id': track['id'],
            'name': track['name'],
            'artists': ', '.join([artist['name'] for artist in track['artists']]),
            'uri': track['uri'],
            'duration_ms': track['duration_ms'],
            'playlist_name': playlist_name
        }
        
        tracks_info.append(track_info)
    
    return tracks_info

def get_audio_features(spotify_client, tracks_info):
    """
    Get audio features for a list of tracks.
    
    Args:
        spotify_client: Authenticated Spotify client
        tracks_info (list): List of track information dictionaries
        
    Returns:
        list: List of track dictionaries with audio features added
    """
    # Get track IDs
    track_ids = [track['id'] for track in tracks_info]
    
    # Spotify API can only handle 100 tracks at a time
    tracks_with_features = tracks_info.copy()
    
    # Process in batches of 100
    for i in range(0, len(track_ids), 100):
        batch_ids = track_ids[i:i+100]
        
        # Get audio features for this batch
        audio_features = spotify_client.audio_features(batch_ids)
        
        # Add features to the corresponding tracks
        for j, features in enumerate(audio_features):
            if features:
                # Add audio features to track info
                idx = i + j
                if idx < len(tracks_with_features):
                    tracks_with_features[idx]['tempo'] = features['tempo']
                    tracks_with_features[idx]['key'] = features['key']
                    tracks_with_features[idx]['mode'] = features['mode']
                    tracks_with_features[idx]['energy'] = features['energy']
                    tracks_with_features[idx]['valence'] = features['valence']
                    tracks_with_features[idx]['danceability'] = features['danceability']
                    tracks_with_features[idx]['acousticness'] = features['acousticness']
                    tracks_with_features[idx]['instrumentalness'] = features['instrumentalness']
                    tracks_with_features[idx]['liveness'] = features['liveness']
                    tracks_with_features[idx]['loudness'] = features['loudness']
                    tracks_with_features[idx]['speechiness'] = features['speechiness']
                    
                    # Add key name and Camelot wheel position
                    key = features['key']
                    mode = features['mode']
                    
                    if key >= 0:  # If key is valid
                        tracks_with_features[idx]['key_name'] = f"{KEY_NAMES[key]} {'Major' if mode == 1 else 'Minor'}"
                        tracks_with_features[idx]['camelot'] = CAMELOT_WHEEL.get((key, mode), "Unknown")
                    else:
                        tracks_with_features[idx]['key_name'] = "Unknown"
                        tracks_with_features[idx]['camelot'] = "Unknown"
    
    return tracks_with_features
