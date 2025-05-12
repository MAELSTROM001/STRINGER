import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import math

def plot_bpm_histogram(original_df, optimized_df):
    """
    Create a histogram showing the BPM distribution of the original vs optimized playlist.
    
    Args:
        original_df (DataFrame): DataFrame of original playlist
        optimized_df (DataFrame): DataFrame of optimized playlist
        
    Returns:
        Figure: Plotly figure object
    """
    fig = go.Figure()
    
    # Add original playlist histogram
    fig.add_trace(go.Histogram(
        x=original_df['tempo'],
        name='Original Playlist',
        opacity=0.7,
        nbinsx=20,
        marker=dict(color='#1DB954')  # Spotify green
    ))
    
    # Add optimized playlist histogram
    fig.add_trace(go.Histogram(
        x=optimized_df['tempo'],
        name='Optimized Playlist',
        opacity=0.7,
        nbinsx=20,
        marker=dict(color='#1A0DAB')  # Deep blue
    ))
    
    # Update layout
    fig.update_layout(
        barmode='overlay',
        title='BPM Distribution',
        xaxis_title='Beats Per Minute (BPM)',
        yaxis_title='Number of Tracks',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def plot_energy_valence(original_df, optimized_df):
    """
    Create a scatter plot showing Energy vs Valence progression.
    
    Args:
        original_df (DataFrame): DataFrame of original playlist
        optimized_df (DataFrame): DataFrame of optimized playlist
        
    Returns:
        Figure: Plotly figure object
    """
    # Create dataframes for the plots
    original_plot_df = original_df[['position', 'name', 'artists', 'energy', 'valence']].copy()
    original_plot_df['Type'] = 'Original'
    
    optimized_plot_df = optimized_df[['new_position', 'name', 'artists', 'energy', 'valence']].copy()
    optimized_plot_df.rename(columns={'new_position': 'position'}, inplace=True)
    optimized_plot_df['Type'] = 'Optimized'
    
    # Combine for plotting
    plot_df = pd.concat([original_plot_df, optimized_plot_df])
    
    # Create scatter plot
    fig = px.scatter(
        plot_df, 
        x='valence', 
        y='energy', 
        color='Type',
        symbol='Type',
        size=[10] * len(plot_df),
        hover_name='name',
        hover_data=['artists', 'position'],
        title='Energy vs. Valence (Mood)',
        labels={
            'valence': 'Valence (Positivity/Mood)',
            'energy': 'Energy'
        },
        color_discrete_map={
            'Original': '#1DB954',  # Spotify green
            'Optimized': '#1A0DAB'  # Deep blue
        }
    )
    
    # Add quadrant labels
    fig.add_annotation(x=0.75, y=0.75, text="Happy / Energetic", showarrow=False)
    fig.add_annotation(x=0.25, y=0.75, text="Angry / Intense", showarrow=False)
    fig.add_annotation(x=0.75, y=0.25, text="Chill / Positive", showarrow=False)
    fig.add_annotation(x=0.25, y=0.25, text="Sad / Melancholic", showarrow=False)
    
    # Draw quadrant lines
    fig.add_shape(type="line", x0=0.5, y0=0, x1=0.5, y1=1, line=dict(color="gray", width=1, dash="dash"))
    fig.add_shape(type="line", x0=0, y0=0.5, x1=1, y1=0.5, line=dict(color="gray", width=1, dash="dash"))
    
    # Update layout
    fig.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    return fig

def plot_key_wheel(optimized_df):
    """
    Create a visualization of the Camelot wheel with track distribution.
    
    Args:
        optimized_df (DataFrame): DataFrame of optimized playlist
        
    Returns:
        Figure: Plotly figure object
    """
    # Extract Camelot values and count occurrences
    camelot_counts = optimized_df['camelot'].value_counts().reset_index()
    camelot_counts.columns = ['camelot', 'count']
    
    # Filter out unknown values
    camelot_counts = camelot_counts[camelot_counts['camelot'] != 'Unknown']
    
    # Calculate positions on the Camelot wheel
    wheel_data = []
    
    for _, row in camelot_counts.iterrows():
        camelot = row['camelot']
        count = row['count']
        
        # Parse Camelot notation
        try:
            number = int(camelot[:-1])
            letter = camelot[-1]
            
            # Calculate angle for this position on the wheel
            angle = (number - 1) * 30 * (math.pi / 180)
            
            # Radius differs for A (inner) and B (outer)
            radius = 1 if letter == 'A' else 1.5
            
            # Calculate x, y coordinates
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            
            wheel_data.append({
                'camelot': camelot,
                'count': count,
                'x': x,
                'y': y,
                'number': number,
                'letter': letter
            })
        except:
            # Skip invalid Camelot values
            continue
    
    # Create figure
    fig = go.Figure()
    
    # Add points for each Camelot position
    if wheel_data:
        wheel_df = pd.DataFrame(wheel_data)
        
        # Add scatter plot for track positions
        fig.add_trace(go.Scatter(
            x=wheel_df['x'],
            y=wheel_df['y'],
            mode='markers+text',
            marker=dict(
                size=wheel_df['count'] * 5 + 10,
                color=wheel_df['count'],
                colorscale='Viridis',
                showscale=True,
                colorbar=dict(title='Track Count')
            ),
            text=wheel_df['camelot'],
            textposition="top center",
            hovertemplate='%{text}<br>Tracks: %{marker.size}<extra></extra>'
        ))
        
        # Draw the wheel structure (circles and lines)
        # Inner circle (A keys)
        theta = np.linspace(0, 2*np.pi, 100)
        x_inner = np.cos(theta)
        y_inner = np.sin(theta)
        
        # Outer circle (B keys)
        x_outer = 1.5 * np.cos(theta)
        y_outer = 1.5 * np.sin(theta)
        
        # Add circles
        fig.add_trace(go.Scatter(
            x=x_inner, y=y_inner,
            mode='lines',
            line=dict(color='gray', width=1),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        fig.add_trace(go.Scatter(
            x=x_outer, y=y_outer,
            mode='lines',
            line=dict(color='gray', width=1),
            showlegend=False,
            hoverinfo='skip'
        ))
        
        # Add spokes
        for i in range(12):
            angle = i * 30 * (math.pi / 180)
            x_spoke = [0, 2 * math.cos(angle)]
            y_spoke = [0, 2 * math.sin(angle)]
            
            fig.add_trace(go.Scatter(
                x=x_spoke, y=y_spoke,
                mode='lines',
                line=dict(color='lightgray', width=1),
                showlegend=False,
                hoverinfo='skip'
            ))
    
    # Update layout
    fig.update_layout(
        title='Camelot Wheel Track Distribution',
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-2, 2]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-2, 2],
            scaleanchor="x",
            scaleratio=1
        ),
        showlegend=False,
        hovermode='closest'
    )
    
    # Add annotations for the wheel sections
    for i in range(12):
        # A keys (inner)
        angle_a = i * 30 * (math.pi / 180)
        x_a = 0.7 * math.cos(angle_a)
        y_a = 0.7 * math.sin(angle_a)
        
        # B keys (outer)
        angle_b = i * 30 * (math.pi / 180)
        x_b = 1.8 * math.cos(angle_b)
        y_b = 1.8 * math.sin(angle_b)
        
        # Add number labels
        fig.add_annotation(
            x=x_a,
            y=y_a,
            text=f"{(i+1)}A",
            showarrow=False,
            font=dict(size=8, color="gray")
        )
        
        fig.add_annotation(
            x=x_b,
            y=y_b,
            text=f"{(i+1)}B",
            showarrow=False,
            font=dict(size=8, color="gray")
        )
    
    return fig
