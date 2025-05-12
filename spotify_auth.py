import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI', 'https://spotify-stringer.streamlit.app/')
SCOPE = 'playlist-modify-public playlist-modify-private user-read-private user-read-email'

def get_spotify_client():
    """
    Creates and returns a Spotify client with the proper authentication.
    Centralizes client creation to prevent duplicate connection issues.
    """
    # Use cache_handler=None to avoid file permission issues in Streamlit cloud
    auth_manager = SpotifyOAuth(
        client_id=SPOTIPY_CLIENT_ID,
        client_secret=SPOTIPY_CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_handler=None,
        open_browser=False
    )
    
    return spotipy.Spotify(auth_manager=auth_manager)

def extract_playlist_tracks(playlist_id):
    """
    Extract tracks from a Spotify playlist.
    
    Args:
        playlist_id: The ID of the Spotify playlist.
        
    Returns:
        A list of tracks from the playlist.
    """
    try:
        # Get a single Spotify client instance
        sp = get_spotify_client()
        
        # Get playlist tracks
        results = sp.playlist_tracks(playlist_id)
        tracks = results['items']
        
        # Continue fetching if there are more tracks
        while results['next']:
            results = sp.next(results)
            tracks.extend(results['items'])
        
        return tracks
    except Exception as e:
        st.error(f"Error fetching playlist: {e}")
        return []

def get_playlist_tracks(playlist_url):
    """
    Get tracks from a Spotify playlist URL.
    
    Args:
        playlist_url: URL of the Spotify playlist.
        
    Returns:
        A list of tracks from the playlist.
    """
    try:
        # Validate playlist URL
        if not playlist_url or "spotify.com/playlist/" not in playlist_url:
            st.error("❌ Invalid playlist URL. Please provide a valid Spotify playlist URL.")
            return []
        
        # Extract playlist ID
        playlist_id = playlist_url.split("playlist/")[1].split("?")[0]
        
        # Fetch the tracks
        tracks = extract_playlist_tracks(playlist_id)
        
        if not tracks:
            st.warning("❌ No tracks found in this playlist or invalid playlist URL.")
            return []
            
        return tracks
    except Exception as e:
        st.error(f"Error processing playlist: {str(e)}")
        return []

def authenticate_spotify():
    """
    Handle Spotify authentication flow.
    Returns a dictionary with authentication status and client if successful.
    """
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        auth_url = None
        try:
            auth_manager = SpotifyOAuth(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_handler=None,
                open_browser=False
            )
            
            # Check if we have a code in the URL
            query_params = st.experimental_get_query_params()
            if "code" in query_params:
                code = query_params["code"][0]
                st.session_state.token_info = auth_manager.get_access_token(code)
                st.session_state.authenticated = True
                # Clear URL parameters by redirecting
                st.experimental_set_query_params()
                st.experimental_rerun()
            else:
                auth_url = auth_manager.get_authorize_url()
        except Exception as e:
            return {
                'success': False,
                'message': f"Authentication error: {str(e)}",
                'spotify_client': None
            }
        
        if auth_url:
            return {
                'success': False,
                'message': "Please authenticate with Spotify",
                'auth_url': auth_url,
                'spotify_client': None
            }
    else:
        # Check if token needs refresh
        try:
            auth_manager = SpotifyOAuth(
                client_id=SPOTIPY_CLIENT_ID,
                client_secret=SPOTIPY_CLIENT_SECRET,
                redirect_uri=REDIRECT_URI,
                scope=SCOPE,
                cache_handler=None,
                open_browser=False
            )
            
            if auth_manager.is_token_expired(st.session_state.token_info):
                st.session_state.token_info = auth_manager.refresh_access_token(
                    st.session_state.token_info['refresh_token']
                )
            
            return {
                'success': True,
                'message': "Successfully authenticated with Spotify",
                'spotify_client': get_spotify_client()
            }
        except Exception as e:
            # If refresh fails, reset authentication
            st.session_state.authenticated = False
            return {
                'success': False,
                'message': f"Error refreshing token: {str(e)}",
                'spotify_client': None
            }
