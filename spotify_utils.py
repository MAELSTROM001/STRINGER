from tenacity import retry, stop_after_attempt, wait_exponential
import streamlit as st

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_playlist_tracks_with_retry(client, playlist_url):
    """Fetch playlist tracks with retry mechanism."""
    try:
        from playlist_analyzer import fetch_playlist_tracks
        return fetch_playlist_tracks(client, playlist_url)
    except Exception as e:
        if "rate limit" in str(e).lower():
            st.warning("Rate limit reached. Retrying in a few seconds...")
            raise
        st.error(f"Error fetching playlist: {str(e)}")
        return None

def create_spotify_playlist(spotify_client, playlist_name, track_uris):
    """Create a new Spotify playlist with the given tracks."""
    try:
        # Get current user
        user = spotify_client.current_user()
        
        # Create playlist
        playlist = spotify_client.user_playlist_create(
            user=user['id'],
            name=playlist_name,
            public=False
        )
        
        # Add tracks to playlist
        spotify_client.playlist_add_items(playlist['id'], track_uris)
        
        return {
            'success': True,
            'link': playlist['external_urls']['spotify']
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        } 