#!/usr/bin/env python3
"""
Data Validation: Compare OilPriceAPI values with original source sites.
Validate data accuracy against the sources listed in commodities.yml.
"""

import asyncio
import httpx
import random
from datetime import datetime, timedelta
import yaml
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from bs4 import BeautifulSoup
import re
import time

from oilpriceapi import OilPriceAPI

# Configuration
API_KEY = os.getenv("OILPRICEAPI_KEY", "demo_key_for_testing")
BASE_URL = os.getenv("OILPRICEAPI_BASE_URL", "http://localhost:5000")

@dataclass
class DataPoint:
    """A single data point comparison."""
    commodity: str
    api_value: float
    source_value: Optional[float]
    source_url: str
    timestamp: str
    error_pct: Optional[float]
    status: str

class SourceScraper:
    """Scrape prices from original source websites."""

    def __init__(self):
        self.session = httpx.AsyncClient(
            timeout=30,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    async def scrape_investing_com(self, url: str, selectors: List[str]) -> Optional[float]:
        """Scrape price from investing.com."""
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')

            for selector in selectors:
                element = soup.select_one(selector)
                if element:
                    price_text = element.get_text().strip()
                    # Clean price text and extract number
                    price_cleaned = re.sub(r'[^\d.,\-]', '', price_text)
                    price_cleaned = price_cleaned.replace(',', '')

                    try:
                        return float(price_cleaned)
                    except ValueError:
                        continue
            return None
        except Exception as e:
            print(f"    Error scraping {url}: {e}")
            return None

    async def scrape_ft(self, url: str, selector: str) -> Optional[float]:
        """Scrape price from Financial Times."""
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')
            element = soup.select_one(selector)

            if element:
                price_text = element.get_text().strip()
                price_cleaned = re.sub(r'[^\d.,\-]', '', price_text)
                price_cleaned = price_cleaned.replace(',', '')

                try:
                    return float(price_cleaned)
                except ValueError:
                    pass
            return None
        except Exception as e:
            print(f"    Error scraping FT {url}: {e}")
            return None

    async def scrape_business_insider(self, url: str, selector: str) -> Optional[float]:
        """Scrape price from Business Insider."""
        try:
            response = await self.session.get(url)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.content, 'html.parser')
            element = soup.select_one(selector)

            if element:
                price_text = element.get_text().strip()
                price_cleaned = re.sub(r'[^\d.,\-]', '', price_text)
                price_cleaned = price_cleaned.replace(',', '')

                try:
                    return float(price_cleaned)
                except ValueError:
                    pass
            return None
        except Exception as e:
            print(f"    Error scraping Business Insider {url}: {e}")
            return None

    async def close(self):
        """Close the HTTP session."""
        await self.session.aclose()

class DataValidator:
    """Main data validation orchestrator."""

    def __init__(self):
        self.api_client = OilPriceAPI(api_key=API_KEY, base_url=BASE_URL)
        self.scraper = SourceScraper()
        self.commodities_config = None

    async def load_commodities_config(self) -> Dict:
        """Load commodities configuration."""
        try:
            with open('/home/kwaldman/code/oilpriceapi-api/config/commodities.yml', 'r') as f:
                config = yaml.safe_load(f)
                self.commodities_config = config['commodities']
                return self.commodities_config
        except Exception as e:
            print(f"Error loading commodities config: {e}")
            return {}

    def get_api_value(self, commodity_code: str) -> Optional[float]:
        """Get current value from our API."""
        try:
            price = self.api_client.prices.get(commodity_code)
            return price.value
        except Exception as e:
            print(f"    API error for {commodity_code}: {e}")
            return None

    async def get_source_value(self, commodity_code: str, config: Dict) -> Tuple[Optional[float], str]:
        """Get value from original source."""
        scrapers = config.get('scrapers', {})

        # Try enabled scrapers in priority order
        enabled_scrapers = [(name, scraper) for name, scraper in scrapers.items()
                          if scraper.get('enabled', True)]
        enabled_scrapers.sort(key=lambda x: x[1].get('priority', 999))

        for scraper_name, scraper_config in enabled_scrapers:
            url = scraper_config.get('url', '')
            if not url:
                continue

            print(f"    Trying {scraper_name}: {url}")

            try:
                if scraper_name == 'investing_com':
                    selectors = [scraper_config.get('css_selector', '')]
                    selectors.extend(scraper_config.get('fallback_selectors', []))
                    value = await self.scraper.scrape_investing_com(url, selectors)

                elif scraper_name == 'ft':
                    selector = scraper_config.get('css_selector', '')
                    value = await self.scraper.scrape_ft(url, selector)

                elif scraper_name == 'business_insider':
                    selector = scraper_config.get('css_selector', '')
                    value = await self.scraper.scrape_business_insider(url, selector)

                else:
                    print(f"    Skipping unsupported scraper: {scraper_name}")
                    continue

                if value is not None:
                    print(f"    ✓ Got value from {scraper_name}: {value}")
                    return value, url
                else:
                    print(f"    ✗ No value from {scraper_name}")

            except Exception as e:
                print(f"    Error with {scraper_name}: {e}")
                continue

            # Add delay between scraper attempts
            await asyncio.sleep(2)

        return None, "No working source found"

    async def validate_commodity(self, commodity_code: str, commodity_name: str, config: Dict) -> DataPoint:
        """Validate a single commodity."""
        print(f"\n🔍 Validating {commodity_name} ({commodity_code})")

        # Get API value
        api_value = self.get_api_value(commodity_code)
        print(f"  API Value: {api_value}")

        if api_value is None:
            return DataPoint(
                commodity=commodity_name,
                api_value=0.0,
                source_value=None,
                source_url="N/A",
                timestamp=datetime.now().isoformat(),
                error_pct=None,
                status="API_ERROR"
            )

        # Get source value
        source_value, source_url = await self.get_source_value(commodity_code, config)
        print(f"  Source Value: {source_value}")

        if source_value is None:
            return DataPoint(
                commodity=commodity_name,
                api_value=api_value,
                source_value=None,
                source_url=source_url,
                timestamp=datetime.now().isoformat(),
                error_pct=None,
                status="SOURCE_ERROR"
            )

        # Calculate error
        error_pct = abs(api_value - source_value) / source_value * 100 if source_value != 0 else 0
        status = "OK" if error_pct < 5 else "HIGH_ERROR" if error_pct < 15 else "CRITICAL_ERROR"

        print(f"  Error: {error_pct:.2f}% ({status})")

        return DataPoint(
            commodity=commodity_name,
            api_value=api_value,
            source_value=source_value,
            source_url=source_url,
            timestamp=datetime.now().isoformat(),
            error_pct=error_pct,
            status=status
        )

    async def run_validation(self, num_commodities: int = 6) -> List[DataPoint]:
        """Run validation on random commodities."""
        print("=" * 80)
        print("🔬 DATA VALIDATION: OilPriceAPI vs Original Sources")
        print("=" * 80)

        # Load configuration
        commodities_config = await self.load_commodities_config()
        if not commodities_config:
            print("❌ Failed to load commodities configuration")
            return []

        # Focus on commodities that are in our sparklines and have working scrapers
        target_commodities = {
            'BRENT_CRUDE_USD': 'Brent Crude Oil',
            'GOLD_USD': 'Gold',
            'GASOLINE_RBOB_USD': 'RBOB Gasoline',
            'COAL_USD': 'Coal',
            'EUR_USD': 'EUR/USD',
            'GBP_USD': 'GBP/USD',
            'WTI_USD': 'WTI Crude Oil',
            'NATURAL_GAS_USD': 'US Natural Gas'
        }

        # Validate commodities that exist in config
        results = []
        validated_count = 0

        for code, name in target_commodities.items():
            if validated_count >= num_commodities:
                break

            # Find commodity in config (codes might be slightly different)
            commodity_config = None
            for config_key, config_value in commodities_config.items():
                if config_value.get('code') == code:
                    commodity_config = config_value
                    break

            if commodity_config is None:
                print(f"⚠️  Skipping {name}: not found in config")
                continue

            # Check if it has working scrapers
            scrapers = commodity_config.get('scrapers', {})
            enabled_scrapers = [s for s in scrapers.values() if s.get('enabled', True)]

            if not enabled_scrapers:
                print(f"⚠️  Skipping {name}: no enabled scrapers")
                continue

            result = await self.validate_commodity(code, name, commodity_config)
            results.append(result)
            validated_count += 1

            # Add delay between validations to be respectful
            await asyncio.sleep(3)

        return results

    def generate_report(self, results: List[DataPoint]) -> str:
        """Generate validation report."""
        report = []
        report.append("\n" + "=" * 80)
        report.append("📊 DATA VALIDATION REPORT")
        report.append("=" * 80)

        # Summary statistics
        total = len(results)
        ok_count = len([r for r in results if r.status == "OK"])
        high_error_count = len([r for r in results if r.status == "HIGH_ERROR"])
        critical_error_count = len([r for r in results if r.status == "CRITICAL_ERROR"])
        error_count = len([r for r in results if "ERROR" in r.status and r.status not in ["HIGH_ERROR", "CRITICAL_ERROR"]])

        report.append(f"\nSUMMARY:")
        report.append(f"  Total Commodities Tested: {total}")
        report.append(f"  ✅ OK (< 5% error): {ok_count}")
        report.append(f"  ⚠️  High Error (5-15%): {high_error_count}")
        report.append(f"  ❌ Critical Error (> 15%): {critical_error_count}")
        report.append(f"  🔥 System Errors: {error_count}")

        # Detailed results table
        report.append(f"\nDETAILED RESULTS:")
        report.append("-" * 80)
        report.append(f"{'Commodity':<25} {'API Value':<12} {'Source Value':<12} {'Error %':<10} {'Status':<15}")
        report.append("-" * 80)

        for result in results:
            api_val = f"{result.api_value:.2f}" if result.api_value else "N/A"
            src_val = f"{result.source_value:.2f}" if result.source_value else "N/A"
            err_pct = f"{result.error_pct:.2f}%" if result.error_pct is not None else "N/A"

            report.append(f"{result.commodity:<25} {api_val:<12} {src_val:<12} {err_pct:<10} {result.status:<15}")

        # Error analysis
        if results:
            valid_errors = [r.error_pct for r in results if r.error_pct is not None]
            if valid_errors:
                avg_error = sum(valid_errors) / len(valid_errors)
                max_error = max(valid_errors)
                min_error = min(valid_errors)

                report.append(f"\nERROR STATISTICS:")
                report.append(f"  Average Error: {avg_error:.2f}%")
                report.append(f"  Maximum Error: {max_error:.2f}%")
                report.append(f"  Minimum Error: {min_error:.2f}%")

        # Recommendations
        report.append(f"\nRECOMMENDATIONS:")

        critical_commodities = [r for r in results if r.status == "CRITICAL_ERROR"]
        if critical_commodities:
            report.append("  🚨 URGENT: Review scraping logic for critical errors:")
            for result in critical_commodities:
                report.append(f"    - {result.commodity}: {result.error_pct:.1f}% error")

        high_error_commodities = [r for r in results if r.status == "HIGH_ERROR"]
        if high_error_commodities:
            report.append("  ⚠️  INVESTIGATE: High error commodities:")
            for result in high_error_commodities:
                report.append(f"    - {result.commodity}: {result.error_pct:.1f}% error")

        ok_commodities = [r for r in results if r.status == "OK"]
        if ok_commodities:
            report.append("  ✅ GOOD: These commodities are accurate:")
            for result in ok_commodities:
                report.append(f"    - {result.commodity}: {result.error_pct:.1f}% error")

        report.append(f"\n📝 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)

        return "\n".join(report)

    async def close(self):
        """Clean up resources."""
        self.api_client.close()
        await self.scraper.close()

async def main():
    """Main execution function."""
    validator = DataValidator()

    try:
        # Run validation on 6 commodities (4+ as requested)
        results = await validator.run_validation(num_commodities=6)

        # Generate and display report
        report = validator.generate_report(results)
        print(report)

        # Save results to JSON for further analysis
        results_dict = []
        for result in results:
            results_dict.append({
                'commodity': result.commodity,
                'api_value': result.api_value,
                'source_value': result.source_value,
                'source_url': result.source_url,
                'timestamp': result.timestamp,
                'error_pct': result.error_pct,
                'status': result.status
            })

        with open('data_validation_results.json', 'w') as f:
            json.dump(results_dict, f, indent=2)

        print(f"\n💾 Raw results saved to: data_validation_results.json")

        # Save report to text file
        with open('data_validation_report.txt', 'w') as f:
            f.write(report)

        print(f"📄 Full report saved to: data_validation_report.txt")

    finally:
        await validator.close()

if __name__ == "__main__":
    asyncio.run(main())