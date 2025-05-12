# 🎧 STRNGER - Spotify Playlist Analyzer for DJs and You

STRNGER is a powerful web application that helps DJs and music enthusiasts analyze and optimize their Spotify playlists for optimal DJ-style flow. It uses audio features like BPM, musical key (Camelot wheel), energy progression, and other metrics to create seamless transitions between tracks.

![STRNGER Demo](images/strnger_demo.gif)

## ✨ Features

- 🔄 **Playlist Analysis**: Analyze your Spotify playlists for BPM, key, energy, and valence
- 🎯 **DJ-Style Optimization**: Reorder tracks for optimal flow and transitions
- 📊 **Interactive Visualizations**: View BPM distribution, key wheel, and energy/valence plots
- 🎵 **Smart Recommendations**: Get track recommendations to bridge gaps in your playlist
- 🌓 **Dark/Light Theme**: Choose your preferred theme
- 📋 **Export Options**: Copy track URIs or create a new optimized playlist directly on Spotify

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- A Spotify account
- Spotify Developer credentials

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/strnger.git
cd strnger
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root with your Spotify API credentials:
```env
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8501
```

### Running the Application

```bash
streamlit run app.py
```

The application will be available at `http://localhost:8501`

## 🎯 How to Use

1. **Authentication**: Connect your Spotify account when prompted
2. **Input Playlist**: Paste a Spotify playlist URL
3. **Analysis**: Wait for the playlist analysis to complete
4. **Optimization**: View the optimized track order and visualizations
5. **Export**: Choose to either:
   - Copy track URIs to clipboard
   - Create a new optimized playlist on Spotify

## 📊 Features in Detail

### Playlist Analysis
- BPM (Tempo) analysis
- Musical key detection (Camelot wheel)
- Energy and valence mapping
- Track transition scoring

### Visualizations
- BPM distribution histogram
- Musical key wheel
- Energy vs. Valence scatter plot
- Track transition visualization

### Optimization
- Smart track reordering based on:
  - BPM progression
  - Key compatibility
  - Energy flow
  - Valence progression

## 🛠️ Technical Details

### Project Structure
```
strnger/
├── app.py              # Main application file
├── utils.py            # Utility functions
├── spotify_utils.py    # Spotify API interactions
├── config.py           # Configuration settings
├── playlist_analyzer.py # Playlist analysis logic
├── track_reorderer.py  # Track reordering logic
├── visualizations.py   # Plotting functions
├── requirements.txt    # Project dependencies
└── .env               # Environment variables (not in repo)
```

### Dependencies
- streamlit==1.32.0
- pandas==2.2.0
- pyperclip==1.8.2
- python-dotenv==1.0.0
- plotly==5.18.0
- spotipy==2.23.0
- tenacity==8.2.3

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Spotify Web API](https://developer.spotify.com/documentation/web-api/)
- [Streamlit](https://streamlit.io/)
- [Plotly](https://plotly.com/)
- [Spotipy](https://spotipy.readthedocs.io/)

## 📧 Contact

MAELSTROM001

Project Link: [https://github.com/MAELSTROM001/strnger](https://github.com/MAELSTROM001/strnger) 