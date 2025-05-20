import os
import time
import logging
import pyperclip
import streamlit as st
from tenacity import retry, stop_after_attempt, wait_exponential

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def validate_env_variables():
    """Validate required environment variables."""
    required_vars = ['SPOTIPY_CLIENT_ID', 'SPOTIPY_CLIENT_SECRET', 'SPOTIPY_REDIRECT_URI']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        st.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        st.info("Please create a .env file with the following variables:")
        st.code("""
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8501
        """)
        return False
    return True

def check_session_timeout():
    """Check if the current session has timed out."""
    if 'last_activity' in st.session_state:
        timeout = 3600  # 1 hour
        if time.time() - st.session_state['last_activity'] > timeout:
            st.session_state.clear()
            st.warning("Session expired. Please reconnect to Spotify.")
            return False
    st.session_state['last_activity'] = time.time()
    return True

def safe_load_file(file_path):
    """Safely load a file with error handling."""
    try:
        with open(file_path, "r", encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"File not found: {file_path}")
        return ""
    except Exception as e:
        st.error(f"Error loading file {file_path}: {str(e)}")
        return ""

def cleanup_session_data():
    """Clean up session data for large playlists."""
    if 'original_tracks' in st.session_state and len(st.session_state['original_tracks']) > 1000:
        st.warning("Large playlist detected. Some data may be cleared to optimize performance.")
        # Keep only essential data
        st.session_state['original_tracks'] = [
            {k: v for k, v in track.items() if k in ['name', 'artists', 'uri']}
            for track in st.session_state['original_tracks']
        ]

def validate_playlist_url(url):
    """Validate Spotify playlist URL format."""
    if not url:
        return False, "Please enter a playlist URL"
    if not url.startswith("https://open.spotify.com/playlist/"):
        return False, "Invalid Spotify playlist URL format"
    return True, ""

def safe_copy_to_clipboard(data):
    """Safely copy data to clipboard with error handling."""
    try:
        # Sanitize data
        sanitized_data = '\n'.join(str(item) for item in data)
        pyperclip.copy(sanitized_data)
        return True
    except Exception as e:
        st.error(f"Error copying to clipboard: {str(e)}")
        return False

def log_error(error, context=None):
    """Log errors with context."""
    logger.error(f"Error: {str(error)}", extra={'context': context})
    st.error(f"An error occurred: {str(error)}")

@st.cache_data(ttl=3600)
def cached_plot_bpm_histogram(original_df, optimized_df):
    """Cached version of BPM histogram plot."""
    from visualizations import plot_bpm_histogram
    return plot_bpm_histogram(original_df, optimized_df)

def create_spotify_playlist(spotify_client, playlist_name, track_uris):
    """
    Create a new Spotify playlist with the given tracks.
    
    Args:
        spotify_client: Authenticated Spotify client
        playlist_name (str): Name for the new playlist
        track_uris (list): List of Spotify track URIs
        
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'link': str or None
        }
    """
    try:
        # Get current user's ID
        user_info = spotify_client.current_user()
        user_id = user_info['id']
        
        # Create a new playlist
        playlist = spotify_client.user_playlist_create(
            user=user_id,
            name=playlist_name,
            public=False,
            description="Created with Strnger - DJ-Style Playlist Organizer"
        )
        
        # Add tracks to the playlist
        # Spotify API can only handle 100 tracks at a time
        for i in range(0, len(track_uris), 100):
            batch = track_uris[i:i+100]
            spotify_client.playlist_add_items(playlist['id'], batch)
        
        return {
            'success': True,
            'message': f"Created playlist '{playlist_name}' with {len(track_uris)} tracks",
            'link': playlist['external_urls']['spotify']
        }
        
    except Exception as e:
        return {
            'success': False,
            'message': str(e),
            'link': None
        }
