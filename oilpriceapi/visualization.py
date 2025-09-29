"""
OilPriceAPI Visualization Module

Data visualization following Edward Tufte's principles:
- Maximize data-ink ratio
- Remove chartjunk
- Show data variation, not design variation
- Clear labeling and context
- Small multiples for comparisons
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import warnings

try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from matplotlib.figure import Figure
    from matplotlib.axes import Axes
    import numpy as np
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class TufteStyle:
    """Tufte-inspired visual style settings."""
    
    # Colors - muted, professional palette
    COLORS = {
        'primary': '#2E3440',      # Dark gray for primary data
        'secondary': '#5E81AC',    # Muted blue
        'accent': '#BF616A',       # Muted red for emphasis
        'grid': '#E5E9F0',         # Very light gray for minimal grid
        'text': '#2E3440',         # Dark gray for text
        'background': '#FFFFFF',   # White background
    }
    
    # Typography
    FONTS = {
        'family': 'sans-serif',
        'title_size': 14,
        'label_size': 10,
        'tick_size': 9,
    }
    
    # Layout
    LAYOUT = {
        'figure_width': 10,
        'figure_height': 6,
        'dpi': 100,
        'line_width': 1.5,
        'marker_size': 4,
    }
    
    @classmethod
    def apply(cls, ax: 'Axes') -> None:
        """Apply Tufte style to an axes object."""
        if not HAS_MATPLOTLIB:
            return
            
        # Remove top and right spines (Tufte box plots)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(0.5)
        ax.spines['bottom'].set_linewidth(0.5)
        
        # Minimize grid
        ax.grid(True, alpha=0.2, linewidth=0.5, color=cls.COLORS['grid'])
        ax.set_axisbelow(True)
        
        # Clean tick marks
        ax.tick_params(colors=cls.COLORS['text'], labelsize=cls.FONTS['tick_size'])
        ax.xaxis.set_tick_params(width=0.5, length=4)
        ax.yaxis.set_tick_params(width=0.5, length=4)


class PriceVisualizer:
    """Visualize oil price data following Tufte principles."""
    
    def __init__(self, client):
        """Initialize visualizer with OilPriceAPI client."""
        self.client = client
        
        if not HAS_MATPLOTLIB:
            warnings.warn(
                "matplotlib is required for visualization. "
                "Install with: pip install matplotlib",
                ImportWarning
            )
    
    def plot_price_series(
        self,
        commodity: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "daily",
        show_range: bool = True,
        annotate_extremes: bool = True
    ) -> Optional['Figure']:
        """Create a clean time series plot.
        
        Args:
            commodity: Commodity code
            start_date: Start date for data
            end_date: End date for data
            interval: Data interval
            show_range: Show min/max range band
            annotate_extremes: Annotate highest and lowest points
            
        Returns:
            matplotlib Figure object
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib required for visualization")
        
        # Fetch data
        history = self.client.historical.get(
            commodity=commodity,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            per_page=1000
        )
        
        if not history.data:
            warnings.warn("No data available for visualization")
            return None
        
        # Extract data
        dates = [p.date for p in history.data]
        prices = [p.value for p in history.data]
        
        # Create figure
        fig, ax = plt.subplots(
            figsize=(TufteStyle.LAYOUT['figure_width'], TufteStyle.LAYOUT['figure_height']),
            dpi=TufteStyle.LAYOUT['dpi']
        )
        
        # Apply Tufte style
        TufteStyle.apply(ax)
        
        # Plot main price line
        ax.plot(
            dates, prices,
            color=TufteStyle.COLORS['primary'],
            linewidth=TufteStyle.LAYOUT['line_width'],
            label=commodity
        )
        
        # Add range band if requested
        if show_range and len(prices) > 20:
            # Calculate rolling min/max
            window = min(20, len(prices) // 5)
            rolling_min = pd.Series(prices).rolling(window, center=True).min()
            rolling_max = pd.Series(prices).rolling(window, center=True).max()
            
            ax.fill_between(
                dates,
                rolling_min,
                rolling_max,
                alpha=0.1,
                color=TufteStyle.COLORS['secondary'],
                label='Range'
            )
        
        # Annotate extremes
        if annotate_extremes and len(prices) > 0:
            max_idx = prices.index(max(prices))
            min_idx = prices.index(min(prices))
            
            # Annotate maximum
            ax.annotate(
                f'${prices[max_idx]:.2f}',
                xy=(dates[max_idx], prices[max_idx]),
                xytext=(10, 10),
                textcoords='offset points',
                fontsize=TufteStyle.FONTS['tick_size'],
                color=TufteStyle.COLORS['accent'],
                ha='left'
            )
            
            # Annotate minimum
            ax.annotate(
                f'${prices[min_idx]:.2f}',
                xy=(dates[min_idx], prices[min_idx]),
                xytext=(10, -15),
                textcoords='offset points',
                fontsize=TufteStyle.FONTS['tick_size'],
                color=TufteStyle.COLORS['secondary'],
                ha='left'
            )
        
        # Labels and title
        ax.set_xlabel('Date', fontsize=TufteStyle.FONTS['label_size'])
        ax.set_ylabel('Price (USD)', fontsize=TufteStyle.FONTS['label_size'])
        ax.set_title(
            f'{commodity} Price History',
            fontsize=TufteStyle.FONTS['title_size'],
            pad=20
        )
        
        # Format dates on x-axis
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate(rotation=45, ha='right')
        
        # Add data source note (Tufte principle)
        fig.text(
            0.99, 0.01,
            f'Source: OilPriceAPI | {datetime.now().strftime("%Y-%m-%d")}',
            fontsize=7,
            color='gray',
            ha='right',
            va='bottom',
            transform=fig.transFigure
        )
        
        plt.tight_layout()
        return fig
    
    def plot_spread(
        self,
        commodity1: str,
        commodity2: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "daily"
    ) -> Optional['Figure']:
        """Plot price spread between two commodities.
        
        Following Tufte's principle of showing data relationships clearly.
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib required for visualization")
        
        # Fetch data for both commodities
        hist1 = self.client.historical.get(
            commodity=commodity1,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            per_page=1000
        )
        
        hist2 = self.client.historical.get(
            commodity=commodity2,
            start_date=start_date,
            end_date=end_date,
            interval=interval,
            per_page=1000
        )
        
        if not hist1.data or not hist2.data:
            warnings.warn("Insufficient data for spread calculation")
            return None
        
        # Align dates
        dates1 = {p.date.date(): p.value for p in hist1.data}
        dates2 = {p.date.date(): p.value for p in hist2.data}
        common_dates = sorted(set(dates1.keys()) & set(dates2.keys()))
        
        if not common_dates:
            warnings.warn("No overlapping dates for spread calculation")
            return None
        
        spreads = [dates1[d] - dates2[d] for d in common_dates]
        
        # Create figure with two subplots
        fig, (ax1, ax2) = plt.subplots(
            2, 1,
            figsize=(TufteStyle.LAYOUT['figure_width'], TufteStyle.LAYOUT['figure_height']),
            dpi=TufteStyle.LAYOUT['dpi'],
            height_ratios=[2, 1]
        )
        
        # Apply Tufte style
        TufteStyle.apply(ax1)
        TufteStyle.apply(ax2)
        
        # Top plot: Individual prices
        ax1.plot(
            common_dates,
            [dates1[d] for d in common_dates],
            color=TufteStyle.COLORS['primary'],
            linewidth=TufteStyle.LAYOUT['line_width'],
            label=commodity1
        )
        ax1.plot(
            common_dates,
            [dates2[d] for d in common_dates],
            color=TufteStyle.COLORS['secondary'],
            linewidth=TufteStyle.LAYOUT['line_width'],
            label=commodity2
        )
        
        ax1.set_ylabel('Price (USD)', fontsize=TufteStyle.FONTS['label_size'])
        ax1.legend(loc='upper left', frameon=False, fontsize=TufteStyle.FONTS['tick_size'])
        ax1.set_title(
            f'{commodity1} vs {commodity2}',
            fontsize=TufteStyle.FONTS['title_size'],
            pad=20
        )
        
        # Bottom plot: Spread
        ax2.fill_between(
            common_dates,
            spreads,
            0,
            where=[s >= 0 for s in spreads],
            color=TufteStyle.COLORS['accent'],
            alpha=0.3,
            label='Positive spread'
        )
        ax2.fill_between(
            common_dates,
            spreads,
            0,
            where=[s < 0 for s in spreads],
            color=TufteStyle.COLORS['secondary'],
            alpha=0.3,
            label='Negative spread'
        )
        ax2.plot(
            common_dates,
            spreads,
            color=TufteStyle.COLORS['primary'],
            linewidth=1
        )
        ax2.axhline(y=0, color='gray', linewidth=0.5, linestyle='-')
        
        ax2.set_xlabel('Date', fontsize=TufteStyle.FONTS['label_size'])
        ax2.set_ylabel('Spread (USD)', fontsize=TufteStyle.FONTS['label_size'])
        
        # Format dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate(rotation=45, ha='right')
        
        # Add statistics annotation
        mean_spread = np.mean(spreads)
        std_spread = np.std(spreads)
        ax2.text(
            0.02, 0.95,
            f'Mean: ${mean_spread:.2f}\nStd: ${std_spread:.2f}',
            transform=ax2.transAxes,
            fontsize=TufteStyle.FONTS['tick_size'],
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='none')
        )
        
        # Data source note
        fig.text(
            0.99, 0.01,
            f'Source: OilPriceAPI | {datetime.now().strftime("%Y-%m-%d")}',
            fontsize=7,
            color='gray',
            ha='right',
            va='bottom',
            transform=fig.transFigure
        )
        
        plt.tight_layout()
        return fig
    
    def create_sparkline(
        self,
        commodity: str,
        days: int = 30,
        width: float = 3,
        height: float = 1
    ) -> Optional['Figure']:
        """Create a Tufte sparkline - data-dense, word-sized graphic.
        
        Perfect for embedding in reports or dashboards.
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib required for visualization")
        
        # Fetch recent data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        history = self.client.historical.get(
            commodity=commodity,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            interval="daily"
        )
        
        if not history.data:
            return None
        
        prices = [p.value for p in history.data]
        
        # Create minimal figure
        fig, ax = plt.subplots(figsize=(width, height), dpi=100)
        
        # Remove all axes and labels
        ax.axis('off')
        
        # Plot line
        x = range(len(prices))
        ax.plot(x, prices, color=TufteStyle.COLORS['primary'], linewidth=1)
        
        # Add start and end points
        ax.plot(0, prices[0], 'o', color=TufteStyle.COLORS['secondary'], markersize=3)
        ax.plot(len(prices)-1, prices[-1], 'o', color=TufteStyle.COLORS['accent'], markersize=3)
        
        # Add min/max markers
        min_idx = prices.index(min(prices))
        max_idx = prices.index(max(prices))
        ax.plot(min_idx, prices[min_idx], 'v', color='gray', markersize=2)
        ax.plot(max_idx, prices[max_idx], '^', color='gray', markersize=2)
        
        # Add end value label
        ax.text(
            len(prices) - 1, prices[-1],
            f'${prices[-1]:.1f}',
            fontsize=8,
            ha='right',
            va='bottom'
        )
        
        plt.tight_layout(pad=0)
        return fig
    
    def create_small_multiples(
        self,
        commodities: List[str],
        days: int = 30,
        cols: int = 3
    ) -> Optional['Figure']:
        """Create Tufte small multiples - multiple similar graphics for comparison.
        
        Allows easy comparison across multiple commodities.
        """
        if not HAS_MATPLOTLIB:
            raise ImportError("matplotlib required for visualization")
        
        n = len(commodities)
        rows = (n + cols - 1) // cols
        
        fig, axes = plt.subplots(
            rows, cols,
            figsize=(12, 3 * rows),
            dpi=100
        )
        
        if rows == 1:
            axes = [axes]
        if cols == 1:
            axes = [[ax] for ax in axes]
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        for idx, commodity in enumerate(commodities):
            row = idx // cols
            col = idx % cols
            ax = axes[row][col] if rows > 1 else axes[col]
            
            # Fetch data
            history = self.client.historical.get(
                commodity=commodity,
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
                interval="daily"
            )
            
            if history.data:
                dates = [p.date for p in history.data]
                prices = [p.value for p in history.data]
                
                # Apply Tufte style
                TufteStyle.apply(ax)
                
                # Plot
                ax.plot(
                    dates, prices,
                    color=TufteStyle.COLORS['primary'],
                    linewidth=1
                )
                
                # Minimal labeling
                ax.set_title(commodity, fontsize=10, pad=10)
                ax.set_xlabel('')
                
                # Only show y-label on leftmost plots
                if col == 0:
                    ax.set_ylabel('Price (USD)', fontsize=9)
                else:
                    ax.set_ylabel('')
                
                # Rotate x labels
                ax.tick_params(axis='x', rotation=45, labelsize=7)
                ax.tick_params(axis='y', labelsize=7)
            
        # Remove empty subplots
        for idx in range(n, rows * cols):
            row = idx // cols
            col = idx % cols
            ax = axes[row][col] if rows > 1 else axes[col]
            ax.axis('off')
        
        # Add overall title and source
        fig.suptitle(
            f'Commodity Price Comparison ({days} days)',
            fontsize=14,
            y=1.02
        )
        
        fig.text(
            0.99, 0.01,
            f'Source: OilPriceAPI | {datetime.now().strftime("%Y-%m-%d")}',
            fontsize=7,
            color='gray',
            ha='right',
            va='bottom',
            transform=fig.transFigure
        )
        
        plt.tight_layout()
        return fig
