# Stringer: Spotify Playlist Optimizer

Stringer is a Streamlit app that helps DJs and music enthusiasts create better flowing playlists by analyzing and reordering tracks based on key music theory concepts and audio characteristics.

## Features

- **Spotify Authentication**: Connect to your Spotify account to access both public and private playlists
- **Playlist Analysis**: Visualize BPM distribution and key distribution on the Camelot wheel
- **DJ-Style Optimization**: Reorder tracks for optimal flow based on:
  - BPM (tempo) compatibility
  - Musical key compatibility using the Camelot wheel system
  - Energy and valence progression
- **Gap Detection**: Identify potentially difficult transitions
- **Bridge Track Recommendations**: Get suggestions for tracks that can smooth out difficult transitions
- **Export Options**: Create a new playlist on Spotify or export track URIs

## Setup

1. Clone this repository
2. Install dependencies:
```
pip install -r requirements.txt
```
3. Create a Spotify Developer account and register an application:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications)
   - Create a new application
   - Set the redirect URI to `http://localhost:8501/callback/`
   - Note your Client ID and Client Secret

## Running the App

```
streamlit run app.py
```

When the app starts:
1. Enter your Spotify Client ID and Client Secret in the sidebar
2. Complete the authentication process
3. Paste a Spotify playlist URL and analyze!

## How It Works

### Camelot Wheel Logic

Stringer uses the Camelot wheel system to determine key compatibility:
- Keys are represented as numbers (1-12) and letters (A for minor, B for major)
- Compatible keys:
  - Same position (e.g., 8A → 8A): Perfect match
  - Adjacent position (e.g., 8A → 9A): Compatible
  - Relative major/minor (e.g., 8A → 8B): Compatible

### Transition Scoring

Transitions are scored based on:
- Key compatibility (using Camelot wheel)
- BPM difference (smaller = better)
- Energy progression
- Valence (mood) progression

### Optimization Algorithm

The app uses a greedy algorithm to:
1. Start with the first track in the playlist
2. Find the best next track based on transition scores
3. Repeat until all tracks are ordered

## Requirements

- Python 3.7+
- streamlit
- spotipy
- pandas
- numpy
- matplotlib
- seaborn
- Spotify Developer account

## License

MIT
