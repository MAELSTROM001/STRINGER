# Session timeout in seconds (1 hour)
SESSION_TIMEOUT = 3600

# Maximum number of tracks before cleanup
MAX_TRACKS_BEFORE_CLEANUP = 1000

# Essential track fields to keep after cleanup
ESSENTIAL_TRACK_FIELDS = ['name', 'artists', 'uri']

# Spotify API settings
SPOTIFY_REDIRECT_URI = "http://localhost:8501"

# Theme settings
THEMES = {
    'light': {
        'main_bg': "#FFFFFF",
        'main_text': "#333333",
        'main_container_bg': "rgba(255, 255, 255, 0.8)",
        'pattern_color': "rgba(232, 95, 52, 0.05)",
        'subtitle_color': "#444444",
        'card_bg': "rgba(232, 95, 52, 0.05)",
        'scrollbar_track': "#F1F1F1"
    },
    'dark': {
        'main_bg': "#121212",
        'main_text': "#FFFFFF",
        'main_container_bg': "rgba(30, 30, 30, 0.8)",
        'pattern_color': "rgba(232, 95, 52, 0.1)",
        'subtitle_color': "#BBBBBB",
        'card_bg': "rgba(50, 50, 50, 0.5)",
        'scrollbar_track': "#333333"
    }
}

# Logging settings
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'app.log'
LOG_LEVEL = 'INFO' 