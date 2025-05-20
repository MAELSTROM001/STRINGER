import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

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
    key_names = ["C", "C♯/D♭", "D", "D♯/E♭", "E", "F", "F♯/G♭", "G", "G♯/A♭", "A", "A♯/B♭", "B"]
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
    elif letter1 == letter2 and (
            num1 == num2 + 1 or num1 == num2 - 1 or num1 == 12 and num2 == 1 or num1 == 1 and num2 == 12):
        key_score = 1
    # Relative major/minor
    elif (letter1 == 'A' and letter2 == 'B' or letter1 == 'B' and letter2 == 'A') and (
            (num1 == num2 + 3) % 12 or (num2 == num1 + 3) % 12):
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
    """Reorder tracks for optimal DJ flow"""
    # Make a copy of the dataframe to work with
    df = tracks_df.copy()

    # Start with the first track
    optimized_order = [0]  # Start with first track's index
    remaining_indices = set(range(1, len(df)))

    # Greedily select the next best track based on transition score
    while remaining_indices:
        last_track_idx = optimized_order[-1]
        last_track = df.iloc[last_track_idx]

        # Find the best next track
        best_score = float('inf')
        best_idx = -1

        for idx in remaining_indices:
            next_track = df.iloc[idx]
            score = calculate_transition_score(last_track, next_track)

            if score < best_score:
                best_score = score
                best_idx = idx

        # Add the best track to our order and remove from remaining
        optimized_order.append(best_idx)
        remaining_indices.remove(best_idx)

    # Create a new dataframe with optimized order
    optimized_df = df.iloc[optimized_order].copy()
    optimized_df['optimized_position'] = range(1, len(optimized_df) + 1)

    return optimized_df


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


# Visualization Functions
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


def plot_energy_valence_progression(tracks_df):
    """Create a line chart of energy and valence progression"""
    fig, ax = plt.subplots(figsize=(12, 5))

    # Plot energy and valence lines
    ax.plot(tracks_df['optimized_position'], tracks_df['energy'], 'o-', label='Energy', color='#FF9900')
    ax.plot(tracks_df['optimized_position'], tracks_df['valence'], 'o-', label='Valence', color='#3399FF')

    # Add track names at points
    for i, row in tracks_df.iterrows():
        ax.annotate(row['name'][:20] + ('...' if len(row['name']) > 20 else ''),
                   (row['optimized_position'], row['energy']),
                   textcoords="offset points",
                   xytext=(0,10),
                   ha='center',
                   fontsize=8,
                   rotation=45)

    ax.set_xlabel('Track Position')
    ax.set_ylabel('Value (0-1)')
    ax.set_title('Energy and Valence Progression')
    ax.set_ylim(0, 1.1)
    ax.set_xlim(0.8, len(tracks_df) + 0.2)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


def plot_transition_scores(optimized_df):
    """Create a line chart of transition scores between tracks"""
    scores = []
    positions = []
    
    for i in range(len(optimized_df) - 1):
        track1 = optimized_df.iloc[i]
        track2 = optimized_df.iloc[i + 1]
        
        score = calculate_transition_score(track1, track2)
        scores.append(score)
        positions.append(i + 1.5)  # Position between tracks
    
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(positions, scores, 'o-', color='#FF5555')
    
    # Add track pair labels
    for i, pos in enumerate(positions):
        track1 = optimized_df.iloc[i]['name']
        track2 = optimized_df.iloc[i+1]['name']
        label = f"{track1[:10]}...→{track2[:10]}..."
        
        ax.annotate(label,
                   (pos, scores[i]),
                   textcoords="offset points",
                   xytext=(0,10),
                   ha='center',
                   fontsize=8,
                   rotation=45)
    
    ax.set_xlabel('Transition Position')
    ax.set_ylabel('Transition Score (lower is better)')
    ax.set_title('Transition Scores Between Tracks')
    ax.grid(True, alpha=0.3)
    
    # Add threshold line
    ax.axhline(y=7.0, color='r', linestyle='--', alpha=0.5, label='Gap Threshold')
    ax.legend()
    
    plt.tight_layout()
    return fig


def get_table_download_link(df, filename="stringer_playlist.csv", text="Download as CSV"):
    """Generate a link to download the dataframe as a CSV file"""
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">{text}</a>'
    return href
