#!/usr/bin/env python3
"""
OilPriceAPI Visualization Demo

Demonstrates Tufte-inspired data visualization capabilities.
"""

import os
import sys
from datetime import datetime, timedelta

# For local testing
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oilpriceapi import OilPriceAPI

# Configuration
API_KEY = os.getenv("OILPRICEAPI_KEY")
BASE_URL = os.getenv("OILPRICEAPI_BASE_URL", "https://api.oilpriceapi.com")

if not API_KEY:
    raise ValueError("OILPRICEAPI_KEY environment variable is required")


def demo_price_series():
    """Demonstrate clean time series visualization."""
    print("\n" + "=" * 60)
    print("📊 Creating Price Series Visualization")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    if not client.viz:
        print("⚠️  Matplotlib not installed. Install with: pip install matplotlib")
        return
    
    # Create visualization
    print("\nGenerating Brent Crude price chart...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        fig = client.viz.plot_price_series(
            commodity="BRENT_CRUDE_USD",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            interval="daily",
            show_range=True,
            annotate_extremes=True
        )
        
        if fig:
            # Save to file
            output_file = "brent_price_series.png"
            fig.savefig(output_file, bbox_inches='tight', dpi=150)
            print(f"✅ Chart saved to: {output_file}")
            
            # Show plot (if not in headless environment)
            try:
                import matplotlib.pyplot as plt
                plt.show()
            except:
                pass
    except Exception as e:
        print(f"❌ Error: {e}")
    
    client.close()


def demo_spread_analysis():
    """Demonstrate spread visualization between commodities."""
    print("\n" + "=" * 60)
    print("📈 Creating Spread Analysis")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    if not client.viz:
        print("⚠️  Visualization not available")
        return
    
    print("\nAnalyzing Brent-WTI spread...")
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        fig = client.viz.plot_spread(
            commodity1="BRENT_CRUDE_USD",
            commodity2="WTI_USD",
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            interval="daily"
        )
        
        if fig:
            output_file = "brent_wti_spread.png"
            fig.savefig(output_file, bbox_inches='tight', dpi=150)
            print(f"✅ Spread chart saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    client.close()


def demo_sparklines():
    """Demonstrate Tufte sparklines for compact visualization."""
    print("\n" + "=" * 60)
    print("✨ Creating Sparklines")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    if not client.viz:
        print("⚠️  Visualization not available")
        return
    
    commodities = ["BRENT_CRUDE_USD", "GOLD_USD", "GASOLINE_RBOB_USD"]
    
    for commodity in commodities:
        print(f"\nGenerating sparkline for {commodity}...")
        try:
            fig = client.viz.create_sparkline(
                commodity=commodity,
                days=30,
                width=4,
                height=1
            )
            
            if fig:
                output_file = f"sparkline_{commodity.lower()}.png"
                fig.savefig(output_file, bbox_inches='tight', dpi=100)
                print(f"   ✅ Saved to: {output_file}")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    client.close()


def demo_small_multiples():
    """Demonstrate small multiples for comparison."""
    print("\n" + "=" * 60)
    print("🌐 Creating Small Multiples Grid")
    print("=" * 60)
    
    client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
    
    if not client.viz:
        print("⚠️  Visualization not available")
        return
    
    print("\nGenerating comparison grid...")
    
    commodities = [
        "BRENT_CRUDE_USD",
        "GOLD_USD",
        "GASOLINE_RBOB_USD",
        "HEATING_OIL_USD",
        "COAL_USD",
        "EUR_USD"
    ]
    
    try:
        fig = client.viz.create_small_multiples(
            commodities=commodities,
            days=30,
            cols=3
        )
        
        if fig:
            output_file = "commodity_comparison.png"
            fig.savefig(output_file, bbox_inches='tight', dpi=150)
            print(f"✅ Comparison grid saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    client.close()


def main():
    """Run all visualization demos."""
    print("\n" + "#" * 60)
    print("#" + " " * 10 + "OilPriceAPI Visualization Demo" + " " * 18 + "#")
    print("#" + " " * 10 + "Following Edward Tufte Principles" + " " * 14 + "#")
    print("#" * 60)
    
    # Check for matplotlib
    try:
        import matplotlib
        print(f"\n✅ Matplotlib version: {matplotlib.__version__}")
    except ImportError:
        print("\n⚠️  Matplotlib not installed!")
        print("   Install with: pip install matplotlib")
        return
    
    # Run demos
    demo_price_series()
    demo_sparklines()
    demo_small_multiples()
    
    # Note: Spread analysis commented out as it requires WTI data
    # which may not be available in local test
    # demo_spread_analysis()
    
    print("\n" + "=" * 60)
    print("✅ Visualization demo completed!")
    print("   Check the generated PNG files for results")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
