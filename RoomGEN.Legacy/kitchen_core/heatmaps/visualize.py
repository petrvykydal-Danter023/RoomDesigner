"""
Heatmap Visualization - Debug PNG export.

Uses matplotlib to generate heatmap images for debugging and client presentation.
"""

from typing import Dict, List, Optional, Any
import numpy as np

# Import matplotlib with error handling
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.colors import LinearSegmentedColormap
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("Warning: matplotlib not installed. Heatmap visualization disabled.")

from .grid import GridMap


def export_heatmap_png(
    grid: GridMap, 
    path: str, 
    title: str = "Heatmap",
    show_colorbar: bool = True
) -> bool:
    """
    Export GridMap as PNG heatmap image.
    
    Colors:
    - Red = negative (bad placement)
    - Yellow = neutral
    - Green = positive (good placement)
    
    Returns:
        True if successful, False if matplotlib not available
    """
    if not HAS_MATPLOTLIB:
        return False
    
    # Create Red-Yellow-Green colormap
    colors = ['#d73027', '#fee08b', '#1a9850']  # Red, Yellow, Green
    cmap = LinearSegmentedColormap.from_list('RdYlGn', colors)
    
    fig, ax = plt.subplots(figsize=(12, 3))
    
    # Reshape 1D data to 2D for imshow (1 row)
    data_2d = grid.data.reshape(1, -1)
    
    # Plot heatmap
    im = ax.imshow(
        data_2d, 
        cmap=cmap, 
        aspect='auto',
        extent=[0, grid.room_width, 0, 60],  # x: room width, y: cabinet depth
        vmin=np.percentile(grid.data, 5),  # Clip outliers
        vmax=np.percentile(grid.data, 95)
    )
    
    # Labels
    ax.set_xlabel('Position (cm)')
    ax.set_ylabel('Depth')
    ax.set_title(title)
    
    # Colorbar
    if show_colorbar:
        cbar = fig.colorbar(im, ax=ax, orientation='vertical', shrink=0.8)
        cbar.set_label('Score')
    
    # Grid lines every 60cm
    for x in range(0, grid.room_width, 60):
        ax.axvline(x, color='white', alpha=0.3, linewidth=0.5)
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return True


def export_combined_debug(
    layers: Dict[str, GridMap],
    placed_items: List[Dict],
    path: str,
    room_width: int
) -> bool:
    """
    Export multi-panel debug image showing all layers and final placement.
    
    Returns:
        True if successful, False if matplotlib not available
    """
    if not HAS_MATPLOTLIB:
        return False
    
    n_layers = len(layers) + 1  # +1 for placement view
    fig, axes = plt.subplots(n_layers, 1, figsize=(14, 3 * n_layers))
    
    if n_layers == 1:
        axes = [axes]
    
    # Red-Yellow-Green colormap
    colors = ['#d73027', '#fee08b', '#1a9850']
    cmap = LinearSegmentedColormap.from_list('RdYlGn', colors)
    
    # Plot each layer
    for i, (name, grid) in enumerate(layers.items()):
        ax = axes[i]
        data_2d = grid.data.reshape(1, -1)
        
        im = ax.imshow(
            data_2d,
            cmap=cmap,
            aspect='auto',
            extent=[0, room_width, 0, 60]
        )
        
        ax.set_title(f"Layer: {name}")
        ax.set_xlabel('Position (cm)')
        fig.colorbar(im, ax=ax, orientation='vertical', shrink=0.6)
    
    # Final panel: Placement view
    ax = axes[-1]
    ax.set_xlim(0, room_width)
    ax.set_ylim(0, 100)
    ax.set_title("Final Placement")
    ax.set_xlabel('Position (cm)')
    
    # Draw placed items as rectangles
    item_colors = {
        'sink_cabinet': '#3498db',  # Blue
        'sink': '#3498db',
        'stove_cabinet': '#e74c3c',  # Red
        'stove': '#e74c3c',
        'fridge': '#2ecc71',  # Green
        'pantry': '#9b59b6',  # Purple
        'dishwasher': '#1abc9c',  # Teal
        'drawer_cabinet': '#95a5a6',  # Gray
        'filler': '#bdc3c7',  # Light gray
    }
    
    for item in placed_items:
        x = item.get('x', 0)
        width = item.get('width', 60)
        height = 60 if item.get('metadata', {}).get('is_monolith') else 40
        color = item_colors.get(item.get('function', ''), '#7f8c8d')
        
        rect = patches.Rectangle(
            (x, 10), width, height,
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.7
        )
        ax.add_patch(rect)
        
        # Label
        label = item.get('function', '')[:8]  # Truncate for space
        ax.text(x + width/2, 10 + height/2, label, 
                ha='center', va='center', fontsize=8, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return True


def export_placement_diagram(
    placed_items: List[Dict],
    room_width: int,
    path: str
) -> bool:
    """
    Export simple placement diagram (items only, no heatmap).
    """
    if not HAS_MATPLOTLIB:
        return False
    
    fig, ax = plt.subplots(figsize=(14, 4))
    
    ax.set_xlim(0, room_width)
    ax.set_ylim(0, 120)
    ax.set_xlabel('Position (cm)')
    ax.set_title('Kitchen Layout')
    
    # Color mapping
    item_colors = {
        'sink_cabinet': '#3498db',
        'sink': '#3498db',
        'stove_cabinet': '#e74c3c',
        'stove': '#e74c3c',
        'fridge': '#2ecc71',
        'pantry': '#9b59b6',
        'oven_tower': '#9b59b6',
        'dishwasher': '#1abc9c',
        'drawer_cabinet': '#95a5a6',
        'base_cabinet': '#95a5a6',
        'filler': '#bdc3c7',
    }
    
    for item in placed_items:
        x = item.get('x', 0)
        width = item.get('width', 60)
        is_monolith = item.get('metadata', {}).get('is_monolith', False)
        height = 90 if is_monolith else 50
        y = 10
        
        func = item.get('function', '')
        color = item_colors.get(func, '#7f8c8d')
        
        rect = patches.Rectangle(
            (x, y), width, height,
            linewidth=2,
            edgecolor='black',
            facecolor=color,
            alpha=0.8
        )
        ax.add_patch(rect)
        
        # Label
        ax.text(x + width/2, y + height/2, func[:10], 
                ha='center', va='center', fontsize=9, fontweight='bold',
                color='white' if color != '#bdc3c7' else 'black')
    
    # Grid lines every 60cm
    for x in range(0, room_width + 1, 60):
        ax.axvline(x, color='gray', alpha=0.3, linewidth=0.5)
        ax.text(x, 5, str(x), ha='center', fontsize=8, color='gray')
    
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    
    return True
