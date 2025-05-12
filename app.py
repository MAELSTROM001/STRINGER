import streamlit as st
import pandas as pd
import pyperclip
import os
import base64
from dotenv import load_dotenv
from spotify_auth import authenticate_spotify
from playlist_analyzer import fetch_playlist_tracks, get_audio_features
from track_reorderer import reorder_tracks, get_recommendations
from visualizations import plot_bpm_histogram, plot_key_wheel, plot_energy_valence
from utils import (
    validate_env_variables,
    check_session_timeout,
    safe_load_file,
    cleanup_session_data,
    validate_playlist_url,
    safe_copy_to_clipboard,
    log_error,
    cached_plot_bpm_histogram
)
from spotify_utils import fetch_playlist_tracks_with_retry, create_spotify_playlist
import time
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

# Load environment variables from .env file
load_dotenv()

# Validate environment variables
if not validate_env_variables():
    st.stop()

# Initialize session state variables
if 'spotify_client' not in st.session_state:
    st.session_state['spotify_client'] = None
if 'original_tracks' not in st.session_state:
    st.session_state['original_tracks'] = None
if 'optimized_tracks' not in st.session_state:
    st.session_state['optimized_tracks'] = None
if 'recommendations' not in st.session_state:
    st.session_state['recommendations'] = None
if 'theme' not in st.session_state:
    st.session_state['theme'] = 'light'  # Default theme
if 'show_api_alert' not in st.session_state:
    st.session_state['show_api_alert'] = True  # For API credential alert

# Helper function to load local SVG file and convert to base64
def get_svg_base64(svg_file_path):
    return safe_load_file(svg_file_path)

# Helper function to generate custom CSS
def local_css(file_name):
    css_content = safe_load_file(file_name)
    if css_content:
        st.markdown(f'<style>{css_content}</style>', unsafe_allow_html=True)

# Page configuration
st.set_page_config(
    page_title="Strnger - Spotify Playlist Analyzer for DJs",
    page_icon="🎧",
    layout="wide"
)

# Apply custom CSS
try:
    local_css(".streamlit/style.css")
except Exception as e:
    log_error(e, "CSS loading")

# Apply theme-based content styling
if st.session_state['theme'] == 'dark':
    main_bg = "#121212"
    main_text = "#FFFFFF"
    main_container_bg = "rgba(30, 30, 30, 0.8)"
    pattern_color = "rgba(232, 95, 52, 0.1)"
    subtitle_color = "#BBBBBB"
    card_bg = "rgba(50, 50, 50, 0.5)"
    scrollbar_track = "#333333"
else:
    main_bg = "#FFFFFF"
    main_text = "#333333"
    main_container_bg = "rgba(255, 255, 255, 0.8)"
    pattern_color = "rgba(232, 95, 52, 0.05)"
    subtitle_color = "#444444"
    card_bg = "rgba(232, 95, 52, 0.05)"
    scrollbar_track = "#F1F1F1"

# Enhanced background and styling with HTML and theme support
st.markdown(f"""
<style>
    /* Main container styles with theme awareness */
    .main {{
        background-color: {main_bg};
        background-image: 
            radial-gradient({pattern_color} 1px, transparent 1px),
            radial-gradient({pattern_color} 1px, transparent 1px);
        background-size: 30px 30px;
        background-position: 0 0, 15px 15px;
        color: {main_text};
    }}
    
    .main .block-container {{
        background-color: {main_container_bg};
        backdrop-filter: blur(10px);
        -webkit-backdrop-filter: blur(10px);
        border-radius: 10px;
        padding: 2rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
    }}
    
    /* Header and title styles */
    .container {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        position: relative;
    }}
    
    .logo {{
        width: 80px;
        margin-right: 20px;
    }}
    
    .logo-container {{
        display: flex;
        align-items: center;
    }}
    
    .title-text {{
        color: #E85F34;
        font-weight: 800 !important;
        font-size: 3rem;
        margin: 0;
        letter-spacing: -1px;
        text-shadow: 2px 2px 4px rgba(232, 95, 52, 0.1);
    }}
    
    .subtitle {{
        color: {subtitle_color};
        font-weight: 300;
        font-size: 1.2rem;
        margin-top: 0.5rem;
    }}
    
    /* Text highlight and accents */
    .strnger-highlight {{
        background: linear-gradient(135deg, #E85F34 0%, #F57C52 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }}
    
    /* Input containers */
    .playlist-url-input {{
        border-left: 4px solid #E85F34;
        padding: 1.5rem;
        border-radius: 8px;
        background-color: {card_bg};
        margin-top: 2rem;
        position: relative;
        overflow: hidden;
    }}
    
    .playlist-url-input::after {{
        content: "";
        position: absolute;
        top: -50px;
        right: -50px;
        width: 100px;
        height: 100px;
        background: radial-gradient(circle, rgba(232, 95, 52, 0.15) 0%, rgba(232, 95, 52, 0) 70%);
        border-radius: 50%;
        z-index: 0;
    }}
    
    /* Decorative elements */
    .connector-line {{
        height: 3px;
        background: linear-gradient(90deg, #E85F34, #1DB954);
        margin: 2rem 0;
        border-radius: 3px;
    }}
    
    /* Animations */
    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(10px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    
    .fadeIn {{
        animation: fadeIn 0.5s ease-out forwards;
    }}
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: {scrollbar_track};
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: linear-gradient(180deg, #E85F34, #F57C52);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: linear-gradient(180deg, #D24A26, #E85F34);
    }}
    
    /* Dark mode adjustments for standard Streamlit elements */
    .stTextInput label, .stSelectbox label, .stSlider label {{
        color: {main_text} !important;
    }}
    
    .stDataFrame {{
        background-color: {card_bg};
        border-radius: 8px;
        padding: 0.5rem;
    }}
    
    .stMarkdown {{
        color: {main_text};
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        color: {main_text};
    }}
    
    .main a {{
        color: #E85F34 !important;
    }}
    
    /* Button enhancements */
    .stButton > button {{
        border-radius: 30px !important;
        transition: all 0.3s ease !important;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(232, 95, 52, 0.2) !important;
    }}
</style>
""", unsafe_allow_html=True)

# Select the right logo based on theme
if st.session_state['theme'] == 'dark':
    header_logo_path = "images/strnger_logo_white.svg"
else:
    header_logo_path = "images/strnger_logo_transparent.svg"

# App title with logo in flexbox container
try:
    header_logo_base64 = get_svg_base64(header_logo_path)
    st.markdown(f"""
    <div class="container">
        <div class="logo-container">
            <img src="{header_logo_base64}" class="logo">
            <div>
                <h1 class="title-text">STRNGER</h1>
                <p class="subtitle">DJ-Style Playlist Organizer</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    # Fallback if the SVG loading fails
    st.title("Strnger: DJ-Style Playlist Organizer")
    st.write(f"Logo loading error: {str(e)}")

# App description with styled text
st.markdown("""
    <p style="font-size: 1.1rem; line-height: 1.6; margin-bottom: 2rem;">
    Analyze and reorder your Spotify playlists for <span class="strnger-highlight">optimal DJ-style flow</span> using BPM, 
    musical key (Camelot wheel), energy progression, and other audio features.
    </p>
    <div class="connector-line"></div>
""", unsafe_allow_html=True)

# Function to toggle theme
def toggle_theme():
    if st.session_state['theme'] == 'light':
        st.session_state['theme'] = 'dark'
    else:
        st.session_state['theme'] = 'light'
    st.rerun()

# Function to close API alert
def close_api_alert():
    st.session_state['show_api_alert'] = False

# Apply theme-based styling
if st.session_state['theme'] == 'dark':
    sidebar_bg = "#121212"
    sidebar_text = "#FFFFFF"
    sidebar_card_bg = "rgba(255, 255, 255, 0.1)"
    logo_path = "images/strnger_logo_white.svg"
    theme_icon = "☀️"  # Sun for light mode toggle
    theme_tooltip = "Switch to Light Mode"
else:
    sidebar_bg = "#F8F8F8"
    sidebar_text = "#333333"
    sidebar_card_bg = "rgba(232, 95, 52, 0.05)"
    logo_path = "images/strnger_logo_transparent.svg"
    theme_icon = "🌙"  # Moon for dark mode toggle
    theme_tooltip = "Switch to Dark Mode"

# Enhanced sidebar styling with theme support
st.sidebar.markdown(f"""
<style>
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg};
    }}
    .sidebar-header {{
        font-size: 1.3rem;
        font-weight: 600;
        color: {sidebar_text};
        margin-bottom: 1rem;
    }}
    .sidebar-card {{
        background-color: {sidebar_card_bg};
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }}
    .sidebar-card-header {{
        display: flex;
        align-items: center;
        margin-bottom: 0.5rem;
    }}
    .sidebar-card-header svg {{
        margin-right: 0.5rem;
    }}
    .sidebar-card-title {{
        color: {sidebar_text};
        font-weight: 600;
        margin: 0;
    }}
    .sidebar-card-content {{
        color: {sidebar_text}cc;
        font-size: 0.9rem;
    }}
    .auth-success {{
        background-color: rgba(29, 185, 84, 0.2);
        color: #1DB954;
        padding: 0.5rem;
        border-radius: 4px;
        display: flex;
        align-items: center;
        margin-top: 0.5rem;
    }}
    .auth-error {{
        background-color: rgba(232, 95, 52, 0.2);
        color: #E85F34;
        padding: 0.5rem;
        border-radius: 4px;
        display: flex;
        align-items: center;
        margin-top: 0.5rem;
    }}
    .theme-toggle {{
        display: flex;
        justify-content: center;
        margin-top: 2rem;
    }}
    .theme-toggle button {{
        background-color: {sidebar_card_bg};
        color: {sidebar_text};
        border: none;
        border-radius: 20px;
        padding: 8px 16px;
        font-size: 1rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        transition: all 0.3s ease;
    }}
    .theme-toggle button:hover {{
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }}
    .theme-icon {{
        margin-right: 8px;
        font-size: 1.2rem;
    }}
    .api-alert {{
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        background-color: white;
        border-left: 4px solid #E85F34;
        max-width: 300px;
        animation: slideIn 0.5s forwards;
    }}
    .close-button {{
        position: absolute;
        top: 8px;
        right: 8px;
        background: none;
        border: none;
        color: #888;
        cursor: pointer;
        font-size: 1.2rem;
    }}
    @keyframes slideIn {{
        from {{ transform: translateX(100%); opacity: 0; }}
        to {{ transform: translateX(0); opacity: 1; }}
    }}
</style>
""", unsafe_allow_html=True)

# Authenticate with Spotify
try:
    logo_base64 = get_svg_base64(logo_path)
    st.sidebar.markdown(f"""
    <div style="display: flex; align-items: center; margin-bottom: 2rem;">
        <img src="{logo_base64}" style="width: 40px; margin-right: 10px;">
        <span class="sidebar-header">STRNGER</span>
    </div>
    """, unsafe_allow_html=True)
except:
    st.sidebar.header("STRNGER")

# Add theme toggle button
st.sidebar.markdown(f"""
<div class="theme-toggle">
    <button onclick="theme_toggle()">
        <span class="theme-icon">{theme_icon}</span>
        {theme_tooltip}
    </button>
</div>

<script>
function theme_toggle() {{
    const form = window.parent.document.querySelector('form[data-testid="stForm"]');
    const button = form.querySelector('button[data-testid="stFormSubmitButton"]');
    button.click();
}}
</script>
""", unsafe_allow_html=True)

if st.sidebar.button("Toggle Theme", key="theme_toggle", on_click=toggle_theme, help=theme_tooltip):
    pass  # The actual toggling happens in the on_click callback

# Spotify authentication card with improved styling
spotify_icon_color = sidebar_text if st.session_state['theme'] == 'light' else "rgba(255, 255, 255, 0.8)"
st.sidebar.markdown(f"""
<div class="sidebar-card">
    <div class="sidebar-card-header">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
            <path d="M12 0C5.4 0 0 5.4 0 12C0 18.6 5.4 24 12 24C18.6 24 24 18.6 24 12C24 5.4 18.66 0 12 0Z" fill="{spotify_icon_color}"/>
            <path d="M17.521 17.34C17.281 17.699 16.82 17.82 16.46 17.58C13.62 15.84 10.14 15.479 5.939 16.439C5.521 16.56 5.16 16.26 5.04 15.9C4.92 15.48 5.22 15.12 5.58 15C10.14 13.979 13.98 14.4 17.16 16.38C17.58 16.56 17.64 17.04 17.521 17.34Z" fill="#1DB954"/>
            <path d="M18.961 14.04C18.66 14.46 18.12 14.64 17.7 14.34C14.46 12.36 9.54 11.76 5.76 12.96C5.34 13.08 4.74 12.84 4.62 12.42C4.5 12 4.74 11.4 5.16 11.28C9.6 9.9 15 10.56 18.72 12.84C19.081 13.02 19.261 13.62 18.961 14.04Z" fill="#1DB954"/>
            <path d="M19.081 10.68C15.24 8.4 8.82 8.16 5.16 9.301C4.62 9.48 4.08 9.12 3.9 8.64C3.72 8.1 4.08 7.56 4.56 7.38C8.82 6.12 15.84 6.36 20.28 8.94C20.76 9.18 20.94 9.78 20.7 10.26C20.52 10.56 19.92 10.92 19.081 10.68Z" fill="#1DB954"/>
        </svg>
        <h3 class="sidebar-card-title">Spotify Authentication</h3>
    </div>
    <p class="sidebar-card-content">
        Connect to your Spotify account to analyze playlists and create optimized versions
    </p>
    <div id="auth-message"></div>
</div>
""", unsafe_allow_html=True)

auth_message = st.sidebar.empty()

if st.session_state['spotify_client'] is None:
    auth_status = authenticate_spotify()
    if auth_status['success']:
        st.session_state['spotify_client'] = auth_status['spotify_client']
        auth_message.markdown("""
        <div class="auth-success">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="margin-right: 8px;">
                <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z" fill="#1DB954"/>
            </svg>
            Successfully connected to Spotify
        </div>
        """, unsafe_allow_html=True)
    else:
        auth_message.markdown(f"""
        <div class="auth-error">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="margin-right: 8px;">
                <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM13 17H11V15H13V17ZM13 13H11V7H13V13Z" fill="#E85F34"/>
            </svg>
            Authentication failed: {auth_status['message']}
        </div>
        """, unsafe_allow_html=True)
        
        # Show API credentials alert as a popup that can be dismissed
        if st.session_state['show_api_alert'] and "Missing Spotify API credentials" in auth_status['message']:
            st.markdown(f"""
            <div class="api-alert">
                <button class="close-button" onclick="close_api_alert()">×</button>
                <h4 style="margin-top: 0; color: #E85F34;">API Credentials Required</h4>
                <p style="font-size: 0.9rem;">
                    To use this app, you'll need to add your Spotify API credentials in the sidebar.
                    <a href="https://developer.spotify.com/dashboard/" target="_blank">Create a Spotify Developer account</a>
                    to get these credentials.
                </p>
            </div>
            
            <script>
            function close_api_alert() {{
                const form = window.parent.document.querySelector('form[data-testid="stForm"]');
                const closeButton = form.querySelector('button[data-testid="stFormSubmitButton"][aria-label="close_alert"]');
                closeButton.click();
                
                // Also hide the alert immediately for better UX
                const alert = window.parent.document.querySelector('.api-alert');
                if (alert) alert.style.display = 'none';
            }}
            </script>
            """, unsafe_allow_html=True)
            
            # Hidden button to handle API alert closing
            if st.button("Close Alert", key="close_alert", on_click=close_api_alert, help="Close the API credentials alert"):
                pass  # The actual closing happens in the on_click callback
else:
    auth_message.markdown("""
    <div class="auth-success">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="margin-right: 8px;">
            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z" fill="#1DB954"/>
        </svg>
        Connected to Spotify
    </div>
    """, unsafe_allow_html=True)

# Playlist URL input with styled container
st.markdown("""
<div class="playlist-url-input">
    <h3 style="margin-top: 0; margin-bottom: 1rem; color: #333;">Enter a Spotify Playlist URL</h3>
    <p style="color: #666; margin-bottom: 1rem; font-size: 0.9rem;">
        Paste the URL of any Spotify playlist you want to analyze and optimize for DJ-style flow
    </p>
</div>
""", unsafe_allow_html=True)

playlist_url = st.text_input(
    "Spotify Playlist URL", 
    placeholder="https://open.spotify.com/playlist/...",
    help="The URL of a Spotify playlist you want to analyze and reorder",
    label_visibility="collapsed"
)

# Display Spotify icon before URL if entered
if playlist_url:
    playlist_display = playlist_url
    if len(playlist_display) > 60:
        playlist_display = playlist_display[:57] + "..."
    
    st.markdown(f"""
    <div style="display: flex; align-items: center; background-color: rgba(29, 185, 84, 0.1); 
                padding: 0.5rem 1rem; border-radius: 4px; margin-bottom: 1rem;">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="margin-right: 10px;">
            <path d="M12 0C5.4 0 0 5.4 0 12C0 18.6 5.4 24 12 24C18.6 24 24 18.6 24 12C24 5.4 18.66 0 12 0ZM17.521 17.34C17.281 17.699 16.82 17.82 16.46 17.58C13.62 15.84 10.14 15.479 5.939 16.439C5.521 16.56 5.16 16.26 5.04 15.9C4.92 15.48 5.22 15.12 5.58 15C10.14 13.979 13.98 14.4 17.16 16.38C17.58 16.56 17.64 17.04 17.521 17.34ZM18.961 14.04C18.66 14.46 18.12 14.64 17.7 14.34C14.46 12.36 9.54 11.76 5.76 12.96C5.34 13.08 4.74 12.84 4.62 12.42C4.5 12 4.74 11.4 5.16 11.28C9.6 9.9 15 10.56 18.72 12.84C19.081 13.02 19.261 13.62 18.961 14.04ZM19.081 10.68C15.24 8.4 8.82 8.16 5.16 9.301C4.62 9.48 4.08 9.12 3.9 8.64C3.72 8.1 4.08 7.56 4.56 7.38C8.82 6.12 15.84 6.36 20.28 8.94C20.76 9.18 20.94 9.78 20.7 10.26C20.52 10.56 19.92 10.92 19.081 10.68Z" 
                  fill="#1DB954"/>
        </svg>
        <span style="color: #1DB954; font-weight: 500;">{playlist_display}</span>
    </div>
    """, unsafe_allow_html=True)

# Process playlist when URL is provided
if playlist_url and st.session_state['spotify_client']:
    try:
        # Validate playlist URL
        is_valid, error_message = validate_playlist_url(playlist_url)
        if not is_valid:
            st.error(error_message)
            st.stop()

        # Check session timeout
        if not check_session_timeout():
            st.stop()

        with st.spinner("Fetching playlist tracks..."):
            # Fetch and analyze playlist
            tracks_info = fetch_playlist_tracks_with_retry(st.session_state['spotify_client'], playlist_url)
            
            if not tracks_info or len(tracks_info) == 0:
                st.error("❌ No tracks found in this playlist or invalid playlist URL.")
            else:
                playlist_name = tracks_info[0].get('playlist_name', 'Playlist')
                st.success(f"✅ Successfully loaded '{playlist_name}' with {len(tracks_info)} tracks")
                
                # Get audio features for the tracks
                with st.spinner("Analyzing audio features..."):
                    tracks_with_features = get_audio_features(st.session_state['spotify_client'], tracks_info)
                    st.session_state['original_tracks'] = tracks_with_features
                    
                    # Clean up session data if needed
                    cleanup_session_data()
                    
                    # Reorder tracks
                    st.session_state['optimized_tracks'] = reorder_tracks(tracks_with_features)
                    
                    # Get recommendations for gaps
                    st.session_state['recommendations'] = get_recommendations(
                        st.session_state['spotify_client'], 
                        st.session_state['optimized_tracks']
                    )
    except Exception as e:
        log_error(e, "Playlist processing")

# Display results if data is available
if st.session_state['original_tracks'] is not None and st.session_state['optimized_tracks'] is not None:
    # Convert to DataFrames for display
    original_df = pd.DataFrame(st.session_state['original_tracks'])
    optimized_df = pd.DataFrame(st.session_state['optimized_tracks'])
    
    # Create tabs for different views with enhanced styling
    st.markdown("""
    <style>
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
            font-weight: 500;
            background-color: #f0f0f0;
            border: none;
        }
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #E85F34 0%, #F57C52 100%) !important;
            color: white !important;
        }
        .stTabs [data-baseweb="tab-panel"] {
            background-color: white;
            border-radius: 0 8px 8px 8px;
            border: 1px solid #f0f0f0;
            padding: 1.5rem;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        }
    </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "Original Playlist", 
        "Optimized Playlist", 
        "Visualizations", 
        "Recommendations"
    ])
    
    with tab1:
        st.header("Original Playlist")
        st.dataframe(
            original_df[['position', 'name', 'artists', 'tempo', 'key_name', 'energy', 'valence']],
            column_config={
                'position': st.column_config.NumberColumn('Position', format="%d"),
                'name': st.column_config.TextColumn('Track'),
                'artists': st.column_config.TextColumn('Artists'),
                'tempo': st.column_config.NumberColumn('BPM', format="%.1f"),
                'key_name': st.column_config.TextColumn('Key'),
                'energy': st.column_config.ProgressColumn('Energy', format="%.2f", min_value=0, max_value=1),
                'valence': st.column_config.ProgressColumn('Positivity', format="%.2f", min_value=0, max_value=1)
            },
            hide_index=True,
            use_container_width=True
        )
    
    with tab2:
        st.header("DJ-Optimized Playlist")
        st.dataframe(
            optimized_df[['new_position', 'name', 'artists', 'tempo', 'key_name', 'energy', 'valence', 'transition_score']],
            column_config={
                'new_position': st.column_config.NumberColumn('Position', format="%d"),
                'name': st.column_config.TextColumn('Track'),
                'artists': st.column_config.TextColumn('Artists'),
                'tempo': st.column_config.NumberColumn('BPM', format="%.1f"),
                'key_name': st.column_config.TextColumn('Key'),
                'energy': st.column_config.ProgressColumn('Energy', format="%.2f", min_value=0, max_value=1),
                'valence': st.column_config.ProgressColumn('Positivity', format="%.2f", min_value=0, max_value=1),
                'transition_score': st.column_config.ProgressColumn('Transition Score', format="%.2f", min_value=0, max_value=5)
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Enhanced action panel with styled buttons
        st.markdown("""
        <style>
            .action-panel {
                background-color: rgba(232, 95, 52, 0.05);
                border-radius: 8px;
                padding: 1.5rem;
                margin-top: 2rem;
                border-left: 4px solid #E85F34;
            }
            .action-panel-title {
                font-size: 1.2rem;
                font-weight: 600;
                color: #333;
                margin-bottom: 1rem;
            }
            .strnger-button {
                background: linear-gradient(135deg, #E85F34 0%, #F57C52 100%);
                color: white;
                padding: 12px 24px;
                border-radius: 30px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(232, 95, 52, 0.2);
                margin-right: 10px;
            }
            .strnger-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(232, 95, 52, 0.3);
            }
            .spotify-button {
                background: linear-gradient(135deg, #1DB954 0%, #1ED760 100%);
                color: white;
                padding: 12px 24px;
                border-radius: 30px;
                border: none;
                font-weight: 600;
                cursor: pointer;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                box-shadow: 0 4px 12px rgba(29, 185, 84, 0.2);
            }
            .spotify-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 16px rgba(29, 185, 84, 0.3);
            }
            .button-icon {
                margin-right: 8px;
            }
            .playlist-name-input {
                margin-bottom: 1rem;
            }
        </style>
        <div class="action-panel">
            <h3 class="action-panel-title">Export Your Optimized Playlist</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Copy to clipboard and create playlist buttons
        col1, col2 = st.columns(2)
        
        with col1:
            playlist_name = st.text_input("New Playlist Name", 
                                         value=f"DJ-Optimized: {original_df['playlist_name'].iloc[0]}" if 'playlist_name' in original_df.columns else "DJ-Optimized Playlist",
                                         help="Enter a name for your new optimized playlist")
        
        with col2:
            st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)  # Vertical spacing
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Copy Track URIs to Clipboard", use_container_width=True):
                track_uris = [track['uri'] for track in st.session_state['optimized_tracks']]
                safe_copy_to_clipboard(track_uris)
                
        with col2:
            if st.button("🎧 Create Spotify Playlist", use_container_width=True, type="primary"):
                with st.spinner("Creating playlist..."):
                    track_uris = [track['uri'] for track in st.session_state['optimized_tracks']]
                    result = create_spotify_playlist(st.session_state['spotify_client'], playlist_name, track_uris)
                    
                    if result['success']:
                        st.markdown(f"""
                        <div style="background-color: rgba(29, 185, 84, 0.1); padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid #1DB954;">
                            <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" style="margin-right: 10px;">
                                    <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM10 17L5 12L6.41 10.59L10 14.17L17.59 6.58L19 8L10 17Z" fill="#1DB954"/>
                                </svg>
                                <span style="font-weight: 600; font-size: 1.1rem; color: #1DB954;">Playlist Created Successfully!</span>
                            </div>
                            <p style="margin: 0 0 0.5rem 0;">Your optimized playlist has been created on your Spotify account.</p>
                            <a href="{result['link']}" target="_blank" style="display: inline-flex; align-items: center; background-color: #1DB954; color: white; padding: 8px 16px; border-radius: 20px; text-decoration: none; font-weight: 500;">
                                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" style="margin-right: 8px;">
                                    <path d="M12 0C5.4 0 0 5.4 0 12C0 18.6 5.4 24 12 24C18.6 24 24 18.6 24 12C24 5.4 18.66 0 12 0Z" fill="white"/>
                                    <path d="M17.521 17.34C17.281 17.699 16.82 17.82 16.46 17.58C13.62 15.84 10.14 15.479 5.939 16.439C5.521 16.56 5.16 16.26 5.04 15.9C4.92 15.48 5.22 15.12 5.58 15C10.14 13.979 13.98 14.4 17.16 16.38C17.58 16.56 17.64 17.04 17.521 17.34Z" fill="#1DB954"/>
                                    <path d="M18.961 14.04C18.66 14.46 18.12 14.64 17.7 14.34C14.46 12.36 9.54 11.76 5.76 12.96C5.34 13.08 4.74 12.84 4.62 12.42C4.5 12 4.74 11.4 5.16 11.28C9.6 9.9 15 10.56 18.72 12.84C19.081 13.02 19.261 13.62 18.961 14.04Z" fill="#1DB954"/>
                                    <path d="M19.081 10.68C15.24 8.4 8.82 8.16 5.16 9.301C4.62 9.48 4.08 9.12 3.9 8.64C3.72 8.1 4.08 7.56 4.56 7.38C8.82 6.12 15.84 6.36 20.28 8.94C20.76 9.18 20.94 9.78 20.7 10.26C20.52 10.56 19.92 10.92 19.081 10.68Z" fill="#1DB954"/>
                                </svg>
                                Open in Spotify
                            </a>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.error(f"❌ Failed to create playlist: {result['message']}")
    
    with tab3:
        st.header("Audio Feature Visualizations")
        
        viz_col1, viz_col2 = st.columns(2)
        
        with viz_col1:
            st.subheader("BPM Distribution")
            bpm_fig = cached_plot_bpm_histogram(original_df, optimized_df)
            st.plotly_chart(bpm_fig, use_container_width=True)
            
            st.subheader("Energy vs. Valence")
            ev_fig = plot_energy_valence(original_df, optimized_df)
            st.plotly_chart(ev_fig, use_container_width=True)
            
        with viz_col2:
            st.subheader("Musical Key Distribution")
            key_fig = plot_key_wheel(optimized_df)
            st.plotly_chart(key_fig, use_container_width=True)
            
    with tab4:
        st.header("Recommended Tracks to Bridge Gaps")
        
        if st.session_state['recommendations'] and len(st.session_state['recommendations']) > 0:
            rec_df = pd.DataFrame(st.session_state['recommendations'])
            
            st.dataframe(
                rec_df[['position_to_insert', 'name', 'artists', 'tempo', 'key_name', 'energy', 'valence']],
                column_config={
                    'position_to_insert': st.column_config.NumberColumn('Insert After Position', format="%d"),
                    'name': st.column_config.TextColumn('Track'),
                    'artists': st.column_config.TextColumn('Artists'),
                    'tempo': st.column_config.NumberColumn('BPM', format="%.1f"),
                    'key_name': st.column_config.TextColumn('Key'),
                    'energy': st.column_config.ProgressColumn('Energy', format="%.2f", min_value=0, max_value=1),
                    'valence': st.column_config.ProgressColumn('Positivity', format="%.2f", min_value=0, max_value=1)
                },
                hide_index=True,
                use_container_width=True
            )
            
            if st.button("Add Recommendations to Optimized Playlist"):
                # Merge recommendations into the optimized playlist
                with st.spinner("Adding recommendations to playlist..."):
                    new_optimized_tracks = st.session_state['optimized_tracks'].copy()
                    
                    # Sort recommendations by position to insert
                    sorted_recs = sorted(st.session_state['recommendations'], key=lambda x: x['position_to_insert'])
                    
                    # Add each recommendation at the specified position
                    offset = 0
                    for rec in sorted_recs:
                        insert_pos = rec['position_to_insert'] + offset
                        rec['new_position'] = insert_pos + 1
                        new_optimized_tracks.insert(insert_pos + 1, rec)
                        offset += 1
                    
                    # Update positions
                    for i, track in enumerate(new_optimized_tracks):
                        track['new_position'] = i + 1
                    
                    st.session_state['optimized_tracks'] = new_optimized_tracks
                    st.success("✅ Recommendations added to optimized playlist!")
                    st.rerun()
        else:
            st.info("No recommendations are available for this playlist. Try a playlist with more varied tracks.")

# Select footer logo and colors based on theme
if st.session_state['theme'] == 'dark':
    footer_logo_path = "images/strnger_logo_white.svg"
    footer_text_color = "#BBBBBB"
    footer_subtext_color = "#888888" 
    footer_border_color = "rgba(232, 95, 52, 0.2)"
else:
    footer_logo_path = "images/strnger_logo_transparent.svg"
    footer_text_color = "#555555"
    footer_subtext_color = "#888888"
    footer_border_color = "rgba(232, 95, 52, 0.2)"

# Enhanced footer with branding and theme support
try:
    footer_logo_base64 = get_svg_base64(footer_logo_path)
    
    st.markdown(f"""
    <style>
        .footer-container {{
            border-top: 1px solid {footer_border_color};
            margin-top: 3rem;
            padding-top: 1.5rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }}
        .footer-row {{
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 1rem;
        }}
        .footer-logo {{
            width: 40px;
            margin-right: 16px;
        }}
        .footer-text {{
            color: {footer_text_color};
            font-size: 1rem;
            font-weight: 500;
        }}
        .footer-highlight {{
            background: linear-gradient(135deg, #E85F34 0%, #F57C52 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-weight: bold;
        }}
        .spotify-credit {{
            display: flex;
            align-items: center;
            font-size: 0.9rem;
            color: {footer_subtext_color};
            margin-top: 0.5rem;
        }}
        .spotify-logo {{
            height: 20px;
            margin-left: 6px;
            margin-right: 6px;
        }}
    </style>
    
    <div class="footer-container">
        <div class="footer-row">
            <img src="{footer_logo_base64}" class="footer-logo">
            <span class="footer-text">Made with <span style="color: #E85F34;">♥</span> by <span class="footer-highlight">STRNGER</span></span>
        </div>
        <div class="spotify-credit">
            Powered by
            <svg class="spotify-logo" viewBox="0 0 24 24" fill="none">
                <path d="M12 0C5.4 0 0 5.4 0 12C0 18.6 5.4 24 12 24C18.6 24 24 18.6 24 12C24 5.4 18.66 0 12 0Z" fill="#1DB954"/>
                <path d="M17.521 17.34C17.281 17.699 16.82 17.82 16.46 17.58C13.62 15.84 10.14 15.479 5.939 16.439C5.521 16.56 5.16 16.26 5.04 15.9C4.92 15.48 5.22 15.12 5.58 15C10.14 13.979 13.98 14.4 17.16 16.38C17.58 16.56 17.64 17.04 17.521 17.34Z" fill="white"/>
                <path d="M18.961 14.04C18.66 14.46 18.12 14.64 17.7 14.34C14.46 12.36 9.54 11.76 5.76 12.96C5.34 13.08 4.74 12.84 4.62 12.42C4.5 12 4.74 11.4 5.16 11.28C9.6 9.9 15 10.56 18.72 12.84C19.081 13.02 19.261 13.62 18.961 14.04Z" fill="white"/>
                <path d="M19.081 10.68C15.24 8.4 8.82 8.16 5.16 9.301C4.62 9.48 4.08 9.12 3.9 8.64C3.72 8.1 4.08 7.56 4.56 7.38C8.82 6.12 15.84 6.36 20.28 8.94C20.76 9.18 20.94 9.78 20.7 10.26C20.52 10.56 19.92 10.92 19.081 10.68Z" fill="white"/>
            </svg>
            Spotify Web API
        </div>
    </div>
    """, unsafe_allow_html=True)
except Exception as e:
    # Fallback footer
    st.markdown("---")
    st.markdown("Made with ♥ by J.Wanjohi | Powered by Spotify Web API")

def validate_env_variables():
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
    if 'last_activity' in st.session_state:
        timeout = 3600  # 1 hour
        if time.time() - st.session_state['last_activity'] > timeout:
            st.session_state.clear()
            st.warning("Session expired. Please reconnect to Spotify.")
            return False
    st.session_state['last_activity'] = time.time()
    return True

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_playlist_tracks_with_retry(client, playlist_url):
    try:
        return fetch_playlist_tracks(client, playlist_url)
    except Exception as e:
        if "rate limit" in str(e).lower():
            st.warning("Rate limit reached. Retrying in a few seconds...")
            raise
        st.error(f"Error fetching playlist: {str(e)}")
        return None

def safe_load_file(file_path):
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
    if 'original_tracks' in st.session_state and len(st.session_state['original_tracks']) > 1000:
        st.warning("Large playlist detected. Some data may be cleared to optimize performance.")
        # Keep only essential data
        st.session_state['original_tracks'] = [
            {k: v for k, v in track.items() if k in ['name', 'artists', 'uri']}
            for track in st.session_state['original_tracks']
        ]

def validate_playlist_url(url):
    if not url:
        return False, "Please enter a playlist URL"
    if not url.startswith("https://open.spotify.com/playlist/"):
        return False, "Invalid Spotify playlist URL format"
    return True, ""

# Usage
is_valid, error_message = validate_playlist_url(playlist_url)
if not is_valid:
    st.error(error_message)
    

@st.cache_data(ttl=3600)
def cached_plot_bpm_histogram(original_df, optimized_df):
    return plot_bpm_histogram(original_df, optimized_df)

def safe_copy_to_clipboard(data):
    try:
        # Sanitize data
        sanitized_data = '\n'.join(str(item) for item in data)
        pyperclip.copy(sanitized_data)
        return True
    except Exception as e:
        st.error(f"Error copying to clipboard: {str(e)}")
        return False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def log_error(error, context=None):
    logger.error(f"Error: {str(error)}", extra={'context': context})
    st.error(f"An error occurred: {str(error)}")
