import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def authenticate_spotify():
    """
    Authenticate with Spotify using OAuth
    
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'spotify_client': spotipy.Spotify or None
        }
    """
    
    try:
        # Get credentials from environment variables (loaded from .env)
        client_id = os.getenv("SPOTIPY_CLIENT_ID", "")
        client_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")
        redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8501")
        
        # If credentials not in environment, ask user
        if not client_id or not client_secret:
            with st.sidebar.expander("Spotify API Credentials"):
                st.markdown("""
                    To use this app, you need Spotify API credentials. 
                    [Create a Spotify Developer account](https://developer.spotify.com/dashboard/) 
                    and register an app to get these credentials.
                """)
                client_id = st.text_input("Client ID", value=client_id)
                client_secret = st.text_input("Client Secret", value=client_secret, type="password")
                redirect_uri = st.text_input("Redirect URI", value=redirect_uri)
        
        # Display message about credentials being loaded
        else:
            st.sidebar.info("✅ Spotify API credentials loaded from .env file")
        
        # Check if credentials are provided
        if not client_id or not client_secret:
            return {
                'success': False,
                'message': "Missing Spotify API credentials",
                'spotify_client': None
            }
        
        # Define the scope for Spotify API access
        scope = "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public user-library-read"
        
        # Set up authentication manager
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=".spotify_cache"
        )
        
        # Create Spotify client
        spotify = spotipy.Spotify(auth_manager=auth_manager)
        
        # Test connection by getting current user info
        try:
            user_info = spotify.current_user()
            if user_info and isinstance(user_info, dict):
                display_name = user_info.get('display_name', "Unknown User")
            else:
                display_name = "Unknown User"
        except:
            display_name = "Unknown User"
        
        return {
            'success': True,
            'message': f"Authenticated as {display_name}",
            'spotify_client': spotify
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': str(e),
            'spotify_client': None
        }
