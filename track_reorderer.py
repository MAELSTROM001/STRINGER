import numpy as np
import pandas as pd

def calculate_transition_score(track1, track2):
    """
    Calculate a transition score between two tracks based on musical compatibility.
    
    Args:
        track1 (dict): First track with audio features
        track2 (dict): Second track with audio features
        
    Returns:
        float: Transition score from 0 to 5 (higher is better)
    """
    score = 0
    
    # BPM compatibility (0-2 points)
    # Closer BPMs are better for mixing
    if 'tempo' in track1 and 'tempo' in track2:
        bpm_diff = abs(track1['tempo'] - track2['tempo'])
        if bpm_diff <= 3:
            score += 2  # Perfect BPM match
        elif bpm_diff <= 6:
            score += 1.5  # Very good match (within 6 BPM)
        elif bpm_diff <= 10:
            score += 1  # Good match (within 10 BPM)
        elif bpm_diff <= 15:
            score += 0.5  # Acceptable match
    
    # Key compatibility (0-2 points)
    # Camelot wheel: perfect match, neighbor, or relative is best
    if 'camelot' in track1 and 'camelot' in track2 and track1['camelot'] != "Unknown" and track2['camelot'] != "Unknown":
        camelot1 = track1['camelot']
        camelot2 = track2['camelot']
        
        if camelot1 == camelot2:
            score += 2  # Perfect key match
        else:
            # Parse Camelot notation (e.g., "8A" -> number=8, letter="A")
            try:
                num1 = int(camelot1[:-1])
                letter1 = camelot1[-1]
                num2 = int(camelot2[:-1])
                letter2 = camelot2[-1]
                
                # Check if same letter and adjacent number (e.g., 8A and 9A)
                if letter1 == letter2 and (num1 == (num2 % 12) + 1 or (num1 % 12) + 1 == num2):
                    score += 1.5  # Adjacent in Camelot wheel (same letter)
                # Check if same number and different letter (e.g., 8A and 8B)
                elif num1 == num2 and letter1 != letter2:
                    score += 1.5  # Relative major/minor
                # Check if diagonal on Camelot wheel (e.g., 8A and 7B or 9B)
                elif (letter1 == 'A' and letter2 == 'B' and (num1 == (num2 % 12) + 1 or (num1 % 12) + 1 == num2)) or \
                     (letter1 == 'B' and letter2 == 'A' and (num1 == (num2 % 12) + 1 or (num1 % 12) + 1 == num2)):
                    score += 1  # Diagonal on Camelot wheel
            except:
                # If parsing fails, don't add any points
                pass
    
    # Energy progression (0-0.5 point)
    # Gradual energy changes are better
    if 'energy' in track1 and 'energy' in track2:
        energy_diff = abs(track1['energy'] - track2['energy'])
        if energy_diff <= 0.2:
            score += 0.5  # Smooth energy transition
        elif energy_diff <= 0.3:
            score += 0.3  # Moderate energy change
    
    # Valence (mood) progression (0-0.5 point)
    # Gradual mood changes are better
    if 'valence' in track1 and 'valence' in track2:
        valence_diff = abs(track1['valence'] - track2['valence'])
        if valence_diff <= 0.2:
            score += 0.5  # Smooth mood transition
        elif valence_diff <= 0.3:
            score += 0.3  # Moderate mood change
    
    return score

def reorder_tracks(tracks_with_features):
    """
    Reorder tracks for optimal DJ flow.
    
    Args:
        tracks_with_features (list): List of track dictionaries with audio features
        
    Returns:
        list: Reordered list of tracks with transition scores added
    """
    # Make a copy to avoid modifying the original
    tracks = tracks_with_features.copy()
    
    # If less than 2 tracks, no need to reorder
    if len(tracks) < 2:
        return tracks
    
    # Initialize with the first track
    ordered_tracks = [tracks[0]]
    remaining_tracks = tracks[1:]
    
    # For each position, find the best next track
    while remaining_tracks:
        current_track = ordered_tracks[-1]
        best_score = -1
        best_next_track = None
        best_index = -1
        
        # Find the track with the best transition score from the current track
        for i, candidate in enumerate(remaining_tracks):
            score = calculate_transition_score(current_track, candidate)
            if score > best_score:
                best_score = score
                best_next_track = candidate
                best_index = i
        
        # Add transition score to the track
        if best_next_track:
            best_next_track = best_next_track.copy()  # Create a copy to avoid modifying original
            best_next_track['transition_score'] = best_score
            
            # Add to ordered tracks and remove from remaining
            ordered_tracks.append(best_next_track)
            remaining_tracks.pop(best_index)
    
    # Update positions
    for i, track in enumerate(ordered_tracks):
        track['new_position'] = i + 1
    
    # First track doesn't have a transition score
    if 'transition_score' not in ordered_tracks[0]:
        ordered_tracks[0]['transition_score'] = None
    
    return ordered_tracks

def identify_transition_gaps(optimized_tracks, threshold=2.0):
    """
    Identify gaps in transitions that could benefit from bridge tracks.
    
    Args:
        optimized_tracks (list): List of tracks with transition scores
        threshold (float): Minimum transition score threshold
        
    Returns:
        list: List of indices where a bridge track would be helpful
    """
    gap_indices = []
    
    for i in range(len(optimized_tracks) - 1):
        track = optimized_tracks[i]
        next_track = optimized_tracks[i + 1]
        
        if 'transition_score' in next_track and next_track['transition_score'] < threshold:
            gap_indices.append(i)
    
    return gap_indices

def get_recommendations(spotify_client, optimized_tracks, max_recommendations=5):
    """
    Get track recommendations to bridge gaps in transitions.
    
    Args:
        spotify_client: Authenticated Spotify client
        optimized_tracks (list): List of tracks with transition scores
        max_recommendations (int): Maximum number of recommendations to return
        
    Returns:
        list: List of recommended tracks with insertion positions
    """
    # Find gaps in transitions
    gap_indices = identify_transition_gaps(optimized_tracks, threshold=2.5)
    
    # Limit to the specified maximum number of recommendations
    gap_indices = gap_indices[:max_recommendations]
    
    recommendations = []
    
    for idx in gap_indices:
        current_track = optimized_tracks[idx]
        next_track = optimized_tracks[idx + 1]
        
        # Calculate target audio features (halfway between current and next track)
        seed_tracks = [current_track['id'], next_track['id']]
        
        target_features = {}
        for feature in ['tempo', 'energy', 'valence', 'danceability', 'acousticness']:
            if feature in current_track and feature in next_track:
                # Average the feature values
                target_features[f'target_{feature}'] = (current_track[feature] + next_track[feature]) / 2
        
        # Get recommendations from Spotify
        try:
            recs = spotify_client.recommendations(
                seed_tracks=seed_tracks,
                limit=1,
                **target_features
            )
            
            # Process recommendations
            for track in recs['tracks']:
                # Get audio features for this track
                features = spotify_client.audio_features([track['id']])[0]
                
                if features:
                    # Create recommendation object
                    rec = {
                        'id': track['id'],
                        'name': track['name'],
                        'artists': ', '.join([artist['name'] for artist in track['artists']]),
                        'uri': track['uri'],
                        'position_to_insert': idx + 1,  # Insert after the current track
                        'tempo': features['tempo'],
                        'key': features['key'],
                        'mode': features['mode'],
                        'energy': features['energy'],
                        'valence': features['valence'],
                        'danceability': features['danceability'],
                        'acousticness': features['acousticness']
                    }
                    
                    # Add key name and Camelot wheel position
                    key = features['key']
                    mode = features['mode']
                    
                    if key >= 0:  # If key is valid
                        rec['key_name'] = f"{KEY_NAMES[key]} {'Major' if mode == 1 else 'Minor'}"
                        rec['camelot'] = CAMELOT_WHEEL.get((key, mode), "Unknown")
                    else:
                        rec['key_name'] = "Unknown"
                        rec['camelot'] = "Unknown"
                    
                    # Calculate transition scores
                    rec['transition_score_from_prev'] = calculate_transition_score(current_track, rec)
                    rec['transition_score_to_next'] = calculate_transition_score(rec, next_track)
                    
                    recommendations.append(rec)
        except Exception as e:
            # If recommendation fails, just continue
            continue
    
    return recommendations

# Import the KEY_NAMES and CAMELOT_WHEEL from playlist_analyzer
from playlist_analyzer import KEY_NAMES, CAMELOT_WHEEL
