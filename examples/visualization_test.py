#!/usr/bin/env python3
"""
Quick test of visualization with mock data.
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta

# Import our Tufte style
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from oilpriceapi.visualization import TufteStyle

def create_tufte_demo():
    """Create a demo chart following Tufte principles."""
    
    # Generate mock data
    days = 30
    dates = [datetime.now() - timedelta(days=i) for i in range(days, 0, -1)]
    base_price = 70
    prices = base_price + np.cumsum(np.random.randn(days) * 0.5)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6), dpi=100)
    
    # Apply Tufte style
    TufteStyle.apply(ax)
    
    # Plot data
    ax.plot(
        dates, prices,
        color=TufteStyle.COLORS['primary'],
        linewidth=1.5
    )
    
    # Add annotations for max and min
    max_idx = np.argmax(prices)
    min_idx = np.argmin(prices)
    
    ax.scatter([dates[max_idx]], [prices[max_idx]], 
              color=TufteStyle.COLORS['accent'], s=20, zorder=5)
    ax.annotate(
        f'High: ${prices[max_idx]:.2f}',
        xy=(dates[max_idx], prices[max_idx]),
        xytext=(10, 10),
        textcoords='offset points',
        fontsize=9,
        color=TufteStyle.COLORS['accent']
    )
    
    ax.scatter([dates[min_idx]], [prices[min_idx]], 
              color=TufteStyle.COLORS['secondary'], s=20, zorder=5)
    ax.annotate(
        f'Low: ${prices[min_idx]:.2f}',
        xy=(dates[min_idx], prices[min_idx]),
        xytext=(10, -15),
        textcoords='offset points',
        fontsize=9,
        color=TufteStyle.COLORS['secondary']
    )
    
    # Labels
    ax.set_xlabel('Date', fontsize=10)
    ax.set_ylabel('Price (USD)', fontsize=10)
    ax.set_title('Oil Price Visualization (Tufte Style)', fontsize=14, pad=20)
    
    # Format x-axis
    import matplotlib.dates as mdates
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    fig.autofmt_xdate(rotation=45, ha='right')
    
    # Add data source note
    fig.text(
        0.99, 0.01,
        f'Mock Data | Generated {datetime.now().strftime("%Y-%m-%d")}',
        fontsize=7,
        color='gray',
        ha='right',
        va='bottom',
        transform=fig.transFigure
    )
    
    # Add statistics
    mean_price = np.mean(prices)
    std_price = np.std(prices)
    ax.text(
        0.02, 0.98,
        f'Mean: ${mean_price:.2f}\nStd Dev: ${std_price:.2f}',
        transform=ax.transAxes,
        fontsize=9,
        verticalalignment='top',
        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor='none')
    )
    
    plt.tight_layout()
    
    # Save figure
    output_file = 'tufte_style_demo.png'
    fig.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f'Chart saved to: {output_file}')
    
    return fig

def create_sparkline_demo():
    """Create sparklines following Tufte's design."""
    
    # Create multiple sparklines
    fig, axes = plt.subplots(3, 1, figsize=(3, 3), dpi=100)
    
    commodities = ['Brent Crude', 'Natural Gas', 'Gold']
    
    for idx, (ax, commodity) in enumerate(zip(axes, commodities)):
        # Generate mock data
        data = 50 + np.cumsum(np.random.randn(50) * 0.5)
        
        # Remove all axes
        ax.axis('off')
        
        # Plot line
        ax.plot(data, color=TufteStyle.COLORS['primary'], linewidth=1)
        
        # Add end point
        ax.plot(len(data)-1, data[-1], 'o', 
               color=TufteStyle.COLORS['accent'], markersize=3)
        
        # Add label and value
        ax.text(0, data[0], commodity, fontsize=8, va='center')
        ax.text(len(data)-1, data[-1], f'${data[-1]:.1f}', 
               fontsize=7, ha='right', va='center')
    
    plt.tight_layout(pad=0.5)
    
    output_file = 'sparklines_demo.png'
    fig.savefig(output_file, dpi=100, bbox_inches='tight')
    print(f'Sparklines saved to: {output_file}')
    
    return fig

if __name__ == '__main__':
    print('Creating Tufte-style visualizations...')
    print('=' * 50)
    
    # Create main chart
    print('1. Creating main price chart...')
    create_tufte_demo()
    
    # Create sparklines
    print('2. Creating sparklines...')
    create_sparkline_demo()
    
    print('\nDone! Check the generated PNG files.')
