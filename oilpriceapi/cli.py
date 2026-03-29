"""
OilPriceAPI CLI

Quick command-line access to commodity prices, historical data, and metadata.

Usage:
    oilprice price BRENT_CRUDE_USD
    oilprice price BRENT_CRUDE_USD WTI_USD NATURAL_GAS_USD
    oilprice historical BRENT_CRUDE_USD --days 30
    oilprice commodities
    oilprice commodities --search crude

Requires: pip install oilpriceapi[cli]
"""

import sys
import os

try:
    import click
    from rich.console import Console
    from rich.table import Table
except ImportError:
    def main():
        print("CLI requires extra dependencies. Install with:")
        print("  pip install oilpriceapi[cli]")
        sys.exit(1)
    if __name__ == "__main__":
        main()
    sys.exit(1)

from oilpriceapi.version import __version__

console = Console()


def _get_client():
    """Create an OilPriceAPI client from environment."""
    from oilpriceapi import OilPriceAPI
    api_key = os.environ.get("OILPRICEAPI_KEY")
    if not api_key:
        console.print("[red]Error:[/red] Set OILPRICEAPI_KEY environment variable")
        console.print("  export OILPRICEAPI_KEY=your_api_key")
        sys.exit(1)
    return OilPriceAPI(api_key=api_key)


@click.group()
@click.version_option(version=__version__, prog_name="oilprice")
def main():
    """OilPriceAPI CLI - Commodity price data from your terminal."""
    pass


@main.command()
@click.argument("commodities", nargs=-1, required=True)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def price(commodities, as_json):
    """Get current prices for one or more commodities.

    Examples:
        oilprice price BRENT_CRUDE_USD
        oilprice price BRENT_CRUDE_USD WTI_USD
    """
    import json

    client = _get_client()

    if as_json:
        results = []
        for code in commodities:
            try:
                p = client.prices.get(code)
                results.append({
                    "commodity": code,
                    "price": p.value,
                    "currency": p.currency if hasattr(p, "currency") else "USD",
                    "updated": str(p.last_updated) if hasattr(p, "last_updated") else None,
                })
            except Exception as e:
                results.append({"commodity": code, "error": str(e)})
        click.echo(json.dumps(results, indent=2, default=str))
        return

    table = Table(title="Current Prices")
    table.add_column("Commodity", style="cyan")
    table.add_column("Price", justify="right", style="green")
    table.add_column("Currency", style="dim")
    table.add_column("Updated", style="dim")

    for code in commodities:
        try:
            p = client.prices.get(code)
            price_str = f"${p.value:,.2f}" if p.value else "N/A"
            currency = p.currency if hasattr(p, "currency") else "USD"
            updated = str(p.last_updated) if hasattr(p, "last_updated") else ""
            table.add_row(code, price_str, currency, updated)
        except Exception as e:
            table.add_row(code, f"[red]Error[/red]", "", str(e))

    console.print(table)


@main.command()
@click.argument("commodity")
@click.option("--days", default=7, help="Number of days of history (default: 7)")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def historical(commodity, days, as_json):
    """Get historical prices for a commodity.

    Examples:
        oilprice historical BRENT_CRUDE_USD
        oilprice historical WTI_USD --days 30
    """
    import json
    from datetime import datetime, timedelta

    client = _get_client()

    try:
        end = datetime.now()
        start = end - timedelta(days=days)
        result = client.historical.get(
            commodity,
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    prices = result.data if hasattr(result, "data") else result

    if as_json:
        items = []
        for p in prices:
            items.append({
                "date": str(p.date) if hasattr(p, "date") else str(p.created_at) if hasattr(p, "created_at") else None,
                "price": p.value if hasattr(p, "value") else p.price if hasattr(p, "price") else None,
            })
        click.echo(json.dumps(items, indent=2, default=str))
        return

    table = Table(title=f"{commodity} - Last {days} Days")
    table.add_column("Date", style="cyan")
    table.add_column("Price", justify="right", style="green")

    for p in prices:
        date_str = str(p.date) if hasattr(p, "date") else str(p.created_at) if hasattr(p, "created_at") else "?"
        val = p.value if hasattr(p, "value") else p.price if hasattr(p, "price") else None
        price_str = f"${val:,.2f}" if val else "N/A"
        table.add_row(date_str, price_str)

    console.print(table)
    console.print(f"[dim]{len(prices)} data points[/dim]")


@main.command()
@click.option("--search", "-s", default=None, help="Filter by keyword")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def commodities(search, as_json):
    """List available commodities.

    Examples:
        oilprice commodities
        oilprice commodities --search crude
        oilprice commodities -s diesel
    """
    import json

    client = _get_client()

    try:
        items = client.commodities.list()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)

    # Handle different response formats
    if isinstance(items, dict):
        commodity_list = items.get("commodities", items.get("data", []))
    elif isinstance(items, list):
        commodity_list = items
    else:
        commodity_list = items.data if hasattr(items, "data") else []

    if search:
        search_lower = search.lower()
        commodity_list = [
            c for c in commodity_list
            if search_lower in str(getattr(c, "code", c.get("code", "") if isinstance(c, dict) else "")).lower()
            or search_lower in str(getattr(c, "name", c.get("name", "") if isinstance(c, dict) else "")).lower()
        ]

    if as_json:
        items_out = []
        for c in commodity_list:
            if isinstance(c, dict):
                items_out.append(c)
            else:
                items_out.append({
                    "code": getattr(c, "code", ""),
                    "name": getattr(c, "name", ""),
                    "category": getattr(c, "category", ""),
                })
        click.echo(json.dumps(items_out, indent=2, default=str))
        return

    table = Table(title="Available Commodities")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Category", style="dim")

    for c in commodity_list:
        if isinstance(c, dict):
            code = c.get("code", "")
            name = c.get("name", "")
            category = c.get("category", "")
        else:
            code = getattr(c, "code", "")
            name = getattr(c, "name", "")
            category = getattr(c, "category", "")
        table.add_row(code, name, category)

    console.print(table)
    console.print(f"[dim]{len(commodity_list)} commodities[/dim]")


if __name__ == "__main__":
    main()
