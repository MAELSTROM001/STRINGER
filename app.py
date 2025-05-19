import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from PIL import Image
import io
import base64
import re
import os
from dotenv import load_dotenv
from config import load_env_variables

# ===== Spotify Authentication and API Functions =====


def get_spotify_client():
    """Get an authenticated Spotify client using environment variables"""
    # Get credentials from environment
    client_id = os.environ.get('SPOTIFY_CLIENT_ID')
    client_secret = os.environ.get('SPOTIFY_CLIENT_SECRET')
    redirect_uri = "https://example.com/callback"

    # Create auth manager
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scope=
        "playlist-read-private playlist-read-collaborative playlist-modify-private playlist-modify-public",
        cache_path=".cache")

    # Check if we have a valid token in cache
    if 'token_info' in st.session_state:
        token_info = st.session_state.token_info
        # Check if token needs refresh
        if auth_manager.is_token_expired(token_info):
            try:
                token_info = auth_manager.refresh_access_token(
                    token_info['refresh_token'])
                st.session_state.token_info = token_info
            except:
                st.session_state.pop('token_info', None)
                st.sidebar.error("Session expired. Please log in again.")
                token_info = None
    else:
        try:
            token_info = auth_manager.get_cached_token()
            if token_info:
                st.session_state.token_info = token_info
        except:
            token_info = None

    # If no valid token exists, show login button
    if not token_info:
        auth_url = auth_manager.get_authorize_url()
        st.sidebar.markdown(f"### Spotify Authentication")
        st.sidebar.markdown(f"[Login to Spotify]({auth_url})")

        # Hidden input for redirect URL
        redirect_url = st.sidebar.text_input("",
                                             key="redirect_url_input",
                                             label_visibility="collapsed")

        if redirect_url:
            try:
                code = auth_manager.parse_response_code(redirect_url)
                if code != redirect_url:
                    token_info = auth_manager.get_access_token(code)
                    st.session_state.token_info = token_info
                    st.rerun()
            except:
                st.sidebar.error("Authentication failed. Please try again.")
                return None
    else:
        # Show logout button if logged in
        if st.sidebar.button("Logout from Spotify"):
            # Clear cache and session state
            try:
                os.remove(".cache")
            except:
                pass
            st.session_state.pop('token_info', None)
            st.rerun()

    # Return Spotify client if we have a token
    if token_info:
        try:
            return spotipy.Spotify(auth=token_info['access_token'])
        except:
            return None
    return None


def extract_playlist_id(playlist_url):
    """Extract playlist ID from Spotify URL"""
    match = re.search(r'playlist/([a-zA-Z0-9]+)', playlist_url)
    if match:
        return match.group(1)
    return None


def get_playlist_tracks(sp, playlist_id):
    """Get all tracks from a playlist"""
    results = sp.playlist_tracks(playlist_id)
    tracks = results['items']
    while results['next']:
        results = sp.next(results)
        tracks.extend(results['items'])
    return tracks


def get_audio_features(sp, track_ids):
    """Get audio features for a list of track IDs"""
    audio_features = []
    # Process in batches of 100 (API limit)
    for i in range(0, len(track_ids), 100):
        batch = track_ids[i:i + 100]
        audio_features.extend(sp.audio_features(batch))
    return audio_features


# ===== Music Theory and DJ Logic =====


def get_camelot_number(key, mode):
    """Convert Spotify key and mode to Camelot wheel notation"""
    camelot_map = {
        (0, 1): "8B",  # C Major
        (1, 1): "3B",  # C#/Db Major
        (2, 1): "10B",  # D Major
        (3, 1): "5B",  # D#/Eb Major
        (4, 1): "12B",  # E Major
        (5, 1): "7B",  # F Major
        (6, 1): "2B",  # F#/Gb Major
        (7, 1): "9B",  # G Major
        (8, 1): "4B",  # G#/Ab Major
        (9, 1): "11B",  # A Major
        (10, 1): "6B",  # A#/Bb Major
        (11, 1): "1B",  # B Major
        (0, 0): "5A",  # C Minor
        (1, 0): "12A",  # C#/Db Minor
        (2, 0): "7A",  # D Minor
        (3, 0): "2A",  # D#/Eb Minor
        (4, 0): "9A",  # E Minor
        (5, 0): "4A",  # F Minor
        (6, 0): "11A",  # F#/Gb Minor
        (7, 0): "6A",  # G Minor
        (8, 0): "1A",  # G#/Ab Minor
        (9, 0): "8A",  # A Minor
        (10, 0): "3A",  # A#/Bb Minor
        (11, 0): "10A"  # B Minor
    }
    return camelot_map.get((key, mode), "??")


def get_key_name(key, mode):
    """Convert Spotify key and mode to conventional key names"""
    key_names = [
        "C", "C♯/D♭", "D", "D♯/E♭", "E", "F", "F♯/G♭", "G", "G♯/A♭", "A",
        "A♯/B♭", "B"
    ]
    mode_names = ["minor", "major"]
    return f"{key_names[key]} {mode_names[mode]}"


def calculate_transition_score(track1, track2):
    """Calculate a transition score between two tracks (lower is better)"""
    # Extract camelot numbers
    camelot1 = track1['camelot']
    camelot2 = track2['camelot']

    # Parse camelot notation
    num1 = int(camelot1[:-1])
    letter1 = camelot1[-1]
    num2 = int(camelot2[:-1])
    letter2 = camelot2[-1]

    # Calculate key compatibility score (lower is better)
    key_score = 10  # Default high score

    # Perfect match
    if camelot1 == camelot2:
        key_score = 0
    # Adjacent on camelot wheel (same letter)
    elif letter1 == letter2 and (num1 == num2 + 1 or num1 == num2 - 1
                                 or num1 == 12 and num2 == 1
                                 or num1 == 1 and num2 == 12):
        key_score = 1
    # Relative major/minor
    elif (letter1 == 'A' and letter2 == 'B'
          or letter1 == 'B' and letter2 == 'A') and ((num1 == num2 + 3) % 12 or
                                                     (num2 == num1 + 3) % 12):
        key_score = 2

    # BPM compatibility (target is within 5-10% for smooth transition)
    bpm1 = track1['tempo']
    bpm2 = track2['tempo']

    bpm_ratio = max(bpm1, bpm2) / min(bpm1, bpm2)

    # Perfect BPM match
    if abs(bpm1 - bpm2) < 3:
        bpm_score = 0
    # Within 6% (good for beatmatching)
    elif bpm_ratio <= 1.06:
        bpm_score = 1
    # Within 12% (possible with pitch adjustment)
    elif bpm_ratio <= 1.12:
        bpm_score = 3
    # Bigger difference
    else:
        bpm_score = 5

    # Energy and valence transition (smaller changes preferred)
    energy_score = abs(track1['energy'] - track2['energy']) * 3
    valence_score = abs(track1['valence'] - track2['valence']) * 2

    # Calculate final score (weighted sum)
    total_score = key_score * 3 + bpm_score * 2 + energy_score + valence_score

    return total_score


def optimize_playlist(tracks_df):
    """Reorder tracks for optimal DJ flow with progress tracking for large playlists"""
    # Make a copy of the dataframe to work with
    df = tracks_df.copy()

    # Create a progress bar if there are many tracks
    total_tracks = len(df)
    show_progress = total_tracks > 30

    # Initialize progress tracking elements
    progress_bar = None
    progress_text = None
    calc_progress = None

    if show_progress:
        progress_bar = st.progress(0)
        progress_text = st.empty()
        if progress_text is not None:
            progress_text.text(
                f"Optimizing playlist (0/{total_tracks-1} tracks processed)..."
            )

    # Start with the first track
    optimized_order = [0]  # Start with first track's index
    remaining_indices = set(range(1, total_tracks))

    # Pre-calculate scores for large playlists to improve performance
    score_cache = {}  # Initialize score cache for all playlist sizes

    if total_tracks > 50:
        # For large playlists, calculate and store all pairwise scores once
        # This avoids repeated calculations and significantly speeds up the algorithm

        # Show a progress indicator for score calculation
        if show_progress and progress_text is not None:
            progress_text.text(
                "Pre-calculating transition scores for faster optimization...")
            calc_progress = st.progress(0)
            total_calcs = (total_tracks * (total_tracks - 1)) // 2
            completed_calcs = 0

        for i in range(total_tracks):
            track_i = df.iloc[i]
            for j in range(i + 1, total_tracks):
                track_j = df.iloc[j]
                score = calculate_transition_score(track_i, track_j)
                score_cache[(i, j)] = score
                score_cache[(j, i)] = score

                # Update progress for large playlists
                if show_progress and total_tracks > 100:
                    completed_calcs = completed_calcs + 1
                    if completed_calcs % 100 == 0:  # Update every 100 calculations to avoid slowdown
                        if calc_progress is not None and total_calcs > 0:
                            calc_progress.progress(
                                min(completed_calcs / total_calcs, 1.0))

        if show_progress and total_tracks > 100 and calc_progress is not None:
            calc_progress.empty()

    # Greedily select the next best track based on transition score
    for step in range(len(remaining_indices)):
        last_track_idx = optimized_order[-1]
        last_track = df.iloc[last_track_idx]

        # Find the best next track
        best_score = float('inf')
        best_idx = -1

        for idx in remaining_indices:
            # Use cached score if available (for large playlists)
            if total_tracks > 50 and (last_track_idx, idx) in score_cache:
                score = score_cache[(last_track_idx, idx)]
            else:
                next_track = df.iloc[idx]
                score = calculate_transition_score(last_track, next_track)

            if score < best_score:
                best_score = score
                best_idx = idx

        # Add the best track to our order and remove from remaining
        optimized_order.append(best_idx)
        remaining_indices.remove(best_idx)

        # Update progress bar for large playlists
        if show_progress and (step % max(1, total_tracks // 100) == 0
                              or step == len(remaining_indices) - 1):
            if progress_bar is not None:
                progress_bar.progress((step + 1) / (total_tracks - 1))
            if progress_text is not None:
                progress_text.text(
                    f"Optimizing playlist ({step+1}/{total_tracks-1} tracks processed)..."
                )

    # Create a new dataframe with optimized order
    optimized_df = df.iloc[optimized_order].copy()
    optimized_df['optimized_position'] = range(1, len(optimized_df) + 1)

    # Clear progress indicators when done
    if show_progress:
        if progress_text is not None:
            progress_text.empty()
        if progress_bar is not None:
            progress_bar.empty()
        st.success(
            f"✅ Successfully optimized playlist with {total_tracks} tracks!")

    return optimized_df


def get_recommendations(sp, seed_track_id, target_bpm, target_key,
                        target_energy, target_valence):
    """Get track recommendations to bridge between two tracks"""
    try:
        recommendations = sp.recommendations(seed_tracks=[seed_track_id],
                                             limit=5,
                                             target_tempo=target_bpm,
                                             target_key=target_key,
                                             target_energy=target_energy,
                                             target_valence=target_valence)
        return recommendations['tracks']
    except:
        return []


def find_transition_gaps(optimized_df, threshold=7.0):
    """Find transitions that might need bridge tracks"""
    gaps = []

    for i in range(len(optimized_df) - 1):
        track1 = optimized_df.iloc[i]
        track2 = optimized_df.iloc[i + 1]

        score = calculate_transition_score(track1, track2)

        if score > threshold:
            gaps.append((i, i + 1, score))

    return gaps


# ===== Visualization Functions =====


def plot_bpm_distribution(tracks_df):
    """Create a histogram of track tempos"""
    fig, ax = plt.subplots(figsize=(10, 4))
    sns.histplot(tracks_df['tempo'], bins=15, kde=True, ax=ax)
    ax.set_title('BPM Distribution')
    ax.set_xlabel('Tempo (BPM)')
    ax.set_ylabel('Number of Tracks')
    return fig


def plot_camelot_wheel(tracks_df):
    """Create a visualization of tracks on the Camelot wheel"""
    # Create a blank wheel image
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={'projection': 'polar'})

    # Count tracks in each camelot position
    camelot_counts = tracks_df['camelot'].value_counts().reset_index()
    camelot_counts.columns = ['camelot', 'count']

    # Set up the wheel
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    ax.set_xticks(np.pi / 6 * np.arange(12))
    ax.set_xticklabels([])

    # Add the Camelot numbers
    for i in range(12):
        angle = np.pi / 6 * i
        ax.text(angle, 1.2, f"{i + 1}B", ha='center', va='center', fontsize=12)
        ax.text(angle, 0.8, f"{i + 1}A", ha='center', va='center', fontsize=12)

    # Plot each camelot position
    for _, row in camelot_counts.iterrows():
        camelot = row['camelot']
        count = row['count']

        # Parse camelot notation
        if len(camelot) >= 2:
            try:
                num = int(camelot[:-1]) - 1  # Convert to 0-indexed
                letter = camelot[-1]

                # Calculate position
                angle = np.pi / 6 * num
                radius = 1.0 if letter == 'B' else 0.6

                # Draw a point
                ax.scatter(angle, radius, s=count * 100, alpha=0.7)

                # Add label
                ax.text(angle, radius, str(count), ha='center', va='center')
            except:
                continue

    ax.set_title('Track Distribution on Camelot Wheel')
    ax.grid(True)
    return fig


def get_table_download_link(df,
                            filename="stringer_playlist.csv",
                            text="Download as CSV"):
    """Generate a link to download the dataframe as a CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href


# ===== Main App =====


def main():
    st.set_page_config(page_title="Stringer - Spotify Playlist Optimizer",
                       page_icon="🎧",
                       layout="wide")

    st.title("🎧 Stringer: Spotify Playlist Optimizer")
    st.markdown("""
    Optimize your Spotify playlists for DJ-style flow based on BPM, musical key, energy, and valence.
    Perfect for creating smooth transitions between tracks!
    """)

    # Initialize session state
    if 'optimized_df' not in st.session_state:
        st.session_state.optimized_df = None

    if 'original_df' not in st.session_state:
        st.session_state.original_df = None

    # Attempt to authenticate with Spotify
    sp = get_spotify_client()

    # Only continue if we have a valid Spotify connection
    if not sp:
        st.warning("Please log in to Spotify using the sidebar to continue.")
        return

    # Main content area
    st.markdown("### Enter your Spotify playlist URL")
    playlist_url = st.text_input(
        "Spotify Playlist URL",
        placeholder="https://open.spotify.com/playlist/...")

    if playlist_url:
        playlist_id = extract_playlist_id(playlist_url)

        if not playlist_id:
            st.error(
                "Invalid Spotify playlist URL. Please check the URL and try again."
            )
            return

        with st.spinner("Fetching playlist data..."):
            try:
                # Get playlist information
                playlist_info = sp.playlist(playlist_id)
                playlist_name = playlist_info['name']
                playlist_owner = playlist_info['owner']['display_name']
                total_tracks = playlist_info['tracks']['total']

                st.success(
                    f"Found playlist: **{playlist_name}** by *{playlist_owner}* with {total_tracks} tracks"
                )

                # Get all tracks from the playlist
                tracks = get_playlist_tracks(sp, playlist_id)

                # Extract track IDs and other info
                track_data = []
                track_ids = []

                for i, item in enumerate(tracks):
                    if item['track']:
                        track = item['track']
                        track_ids.append(track['id'])

                        artists = ", ".join(
                            [artist['name'] for artist in track['artists']])

                        track_data.append({
                            'position': i + 1,
                            'name': track['name'],
                            'artist': artists,
                            'spotify_uri': track['uri'],
                            'id': track['id'],
                            'duration_ms': track['duration_ms']
                        })

                # Get audio features for all tracks
                with st.spinner("Analyzing audio features..."):
                    audio_features = get_audio_features(sp, track_ids)

                    # Combine track data with audio features
                    for i, features in enumerate(audio_features):
                        if features:
                            track_data[i]['tempo'] = round(
                                features['tempo'], 1)
                            track_data[i]['key'] = features['key']
                            track_data[i]['mode'] = features['mode']
                            track_data[i]['energy'] = features['energy']
                            track_data[i]['danceability'] = features[
                                'danceability']
                            track_data[i]['valence'] = features['valence']
                            track_data[i]['camelot'] = get_camelot_number(
                                features['key'], features['mode'])
                            track_data[i]['key_name'] = get_key_name(
                                features['key'], features['mode'])

                # Convert to dataframe
                df = pd.DataFrame(track_data)

                # Store original dataframe in session state
                st.session_state.original_df = df

                # Display visualizations
                st.markdown("### Playlist Analysis")
                col1, col2 = st.columns(2)

                with col1:
                    bpm_fig = plot_bpm_distribution(df)
                    st.pyplot(bpm_fig)

                with col2:
                    camelot_fig = plot_camelot_wheel(df)
                    st.pyplot(camelot_fig)

                # Optimize button
                if st.button("Optimize Playlist for DJ Flow"):
                    optimized_df = optimize_playlist(df)
                    st.session_state.optimized_df = optimized_df

                # Display results in tabs
                if st.session_state.optimized_df is not None:
                    tab1, tab2, tab3 = st.tabs([
                        "Original Playlist", "Optimized Playlist",
                        "Transition Issues"
                    ])

                    with tab1:
                        st.markdown("### Original Playlist Order")
                        # Display original tracks
                        display_df = df[[
                            'position', 'name', 'artist', 'tempo', 'key_name',
                            'camelot', 'energy', 'valence'
                        ]].copy()
                        display_df = display_df.rename(
                            columns={
                                'position': 'Position',
                                'name': 'Track Name',
                                'artist': 'Artist',
                                'tempo': 'BPM',
                                'key_name': 'Key',
                                'camelot': 'Camelot',
                                'energy': 'Energy',
                                'valence': 'Valence'
                            })
                        st.dataframe(display_df, use_container_width=True)

                    with tab2:
                        st.markdown("### Optimized Playlist Order")
                        optimized_df = st.session_state.optimized_df

                        # Display optimized tracks
                        display_df = optimized_df[[
                            'optimized_position', 'name', 'artist', 'tempo',
                            'key_name', 'camelot', 'energy', 'valence'
                        ]].copy()
                        display_df = display_df.rename(
                            columns={
                                'optimized_position': 'Position',
                                'name': 'Track Name',
                                'artist': 'Artist',
                                'tempo': 'BPM',
                                'key_name': 'Key',
                                'camelot': 'Camelot',
                                'energy': 'Energy',
                                'valence': 'Valence'
                            })
                        st.dataframe(display_df, use_container_width=True)

                        # Export button
                        st.markdown("#### Export Optimized Playlist")

                        # Create new playlist option
                        if st.button(
                                "Create New Spotify Playlist with Optimized Order"
                        ):
                            try:
                                # Create a new playlist
                                user_id = sp.me()['id']
                                new_playlist = sp.user_playlist_create(
                                    user=user_id,
                                    name=
                                    f"{playlist_name} (Optimized by Stringer)",
                                    public=False,
                                    description=
                                    f"Optimized for DJ flow from {playlist_name}"
                                )

                                # Get all track URIs in the optimized order
                                track_uris = optimized_df[
                                    'spotify_uri'].tolist()

                                # Add tracks to the new playlist
                                sp.playlist_add_items(new_playlist['id'],
                                                      track_uris)

                                st.success(
                                    f"✅ Created new playlist: {new_playlist['name']}"
                                )
                                st.markdown(
                                    f"[Open in Spotify](https://open.spotify.com/playlist/{new_playlist['id']})"
                                )
                            except Exception as e:
                                st.error(f"Error creating playlist: {str(e)}")

                        # Download as CSV
                        st.markdown(get_table_download_link(optimized_df),
                                    unsafe_allow_html=True)

                    with tab3:
                        st.markdown("### Potential Transition Issues")

                        # Find transitions that might need work
                        gaps = find_transition_gaps(optimized_df)

                        if not gaps:
                            st.success(
                                "No significant transition issues found! Your playlist should flow nicely."
                            )
                        else:
                            st.warning(
                                f"Found {len(gaps)} transitions that might need attention."
                            )

                            for i, (idx1, idx2, score) in enumerate(gaps):
                                track1 = optimized_df.iloc[idx1]
                                track2 = optimized_df.iloc[idx2]

                                st.markdown(
                                    f"#### Issue #{i+1}: Score {score:.1f}")
                                st.markdown(
                                    f"**From:** {track1['name']} by {track1['artist']} ({track1['tempo']} BPM, {track1['key_name']})"
                                )
                                st.markdown(
                                    f"**To:** {track2['name']} by {track2['artist']} ({track2['tempo']} BPM, {track2['key_name']})"
                                )

                                # Show recommendation for transition
                                st.markdown("##### Suggested fix:")

                                if abs(track1['tempo'] - track2['tempo']) > 10:
                                    st.markdown(
                                        "- **BPM gap:** Consider adjusting tempo during transition"
                                    )

                                if track1['camelot'] != track2['camelot']:
                                    st.markdown(
                                        "- **Key change:** Mix in key or use an intermediate track"
                                    )

                                if abs(track1['energy'] -
                                       track2['energy']) > 0.3:
                                    st.markdown(
                                        "- **Energy shift:** Use EQ to smooth transition"
                                    )

                                st.markdown("---")
            except Exception as e:
                st.error(f"Error processing playlist: {str(e)}")


if __name__ == "__main__":
    main()
