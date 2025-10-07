# Real-World Examples for OilPriceAPI Python SDK

This guide showcases practical applications of the [OilPriceAPI Python SDK](https://oilpriceapi.com) for energy trading, financial analysis, research, and application development.

**[Get your free API key →](https://oilpriceapi.com/auth/signup)** to run these examples.

## 📊 Table of Contents

- [Trading & Finance](#trading--finance)
- [Data Analysis & Research](#data-analysis--research)
- [Web & Mobile Applications](#web--mobile-applications)
- [Monitoring & Alerts](#monitoring--alerts)
- [Data Export & Integration](#data-export--integration)

---

## 🔥 Trading & Finance

### Example 1: Simple Moving Average Crossover Strategy

A classic trading strategy that signals BUY when short-term MA crosses above long-term MA.

```python
from oilpriceapi import OilPriceAPI
import pandas as pd

# Initialize client - get your API key at https://oilpriceapi.com/auth/signup
client = OilPriceAPI()

# Get 6 months of Brent Crude historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-06-01",
    end="2024-12-31",
    interval="daily"
)

# Calculate moving averages
df['SMA_20'] = df['close'].rolling(window=20).mean()
df['SMA_50'] = df['close'].rolling(window=50).mean()

# Generate trading signals
df['signal'] = 'HOLD'
df.loc[df['SMA_20'] > df['SMA_50'], 'signal'] = 'BUY'
df.loc[df['SMA_20'] < df['SMA_50'], 'signal'] = 'SELL'

# Show recent signals
print(df[['date', 'close', 'SMA_20', 'SMA_50', 'signal']].tail(10))
```

**Learn more about trading strategies:** [OilPriceAPI Trading Use Cases](https://oilpriceapi.com/use-cases/trading)

### Example 2: Brent-WTI Spread Analysis

Monitor the price differential between Brent Crude and WTI for arbitrage opportunities.

```python
from oilpriceapi import OilPriceAPI
import matplotlib.pyplot as plt

client = OilPriceAPI()

# Calculate spread over time
spread = client.analysis.spread(
    "BRENT_CRUDE_USD",
    "WTI_USD",
    start="2024-01-01",
    end="2024-12-31"
)

# Find arbitrage opportunities (spread > $5)
opportunities = spread[spread['spread'] > 5.0]

print(f"Found {len(opportunities)} arbitrage opportunities")
print(f"Average spread: ${spread['spread'].mean():.2f}")
print(f"Max spread: ${spread['spread'].max():.2f}")

# Plot the spread
plt.figure(figsize=(12, 6))
plt.plot(spread['date'], spread['spread'])
plt.axhline(y=5.0, color='r', linestyle='--', label='Arbitrage Threshold')
plt.title('Brent-WTI Spread Analysis')
plt.xlabel('Date')
plt.ylabel('Spread (USD)')
plt.legend()
plt.grid(True)
plt.savefig('brent_wti_spread.png')
```

**Pricing for professional traders:** [View Plans](https://oilpriceapi.com/pricing)

### Example 3: Risk Management - Value at Risk (VaR)

Calculate portfolio risk exposure based on oil price volatility.

```python
from oilpriceapi import OilPriceAPI
import numpy as np

client = OilPriceAPI()

# Get 1 year of historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2023-01-01",
    end="2023-12-31",
    interval="daily"
)

# Calculate daily returns
df['returns'] = df['close'].pct_change()

# Calculate VaR (95% confidence)
var_95 = np.percentile(df['returns'].dropna(), 5)

# Portfolio exposure
portfolio_value = 1_000_000  # $1M exposure to Brent
var_dollar = portfolio_value * var_95

print(f"95% Value at Risk: ${abs(var_dollar):,.2f}")
print(f"Maximum expected daily loss (95% confidence): {var_95*100:.2f}%")

# Volatility metrics
volatility = df['returns'].std() * np.sqrt(252)  # Annualized
print(f"Annualized Volatility: {volatility*100:.2f}%")
```

**Need more data for risk modeling?** [Upgrade to higher limits](https://oilpriceapi.com/pricing)

---

## 📈 Data Analysis & Research

### Example 4: Seasonal Price Pattern Analysis

Identify seasonal trends in natural gas prices.

```python
from oilpriceapi import OilPriceAPI
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

client = OilPriceAPI()

# Get 3 years of natural gas data
df = client.prices.to_dataframe(
    commodity="NATURAL_GAS_USD",
    start="2021-01-01",
    end="2024-12-31",
    interval="daily"
)

# Extract month and calculate average by month
df['month'] = pd.to_datetime(df['date']).dt.month
monthly_avg = df.groupby('month')['close'].mean()

# Plot seasonal pattern
plt.figure(figsize=(10, 6))
monthly_avg.plot(kind='bar', color='skyblue')
plt.title('Natural Gas - Seasonal Price Pattern')
plt.xlabel('Month')
plt.ylabel('Average Price (USD/MMBtu)')
plt.xticks(range(12), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'], rotation=45)
plt.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig('natural_gas_seasonal.png')

print("Highest prices in:", monthly_avg.idxmax())
print("Lowest prices in:", monthly_avg.idxmin())
```

**Access historical data for research:** [Sign up free](https://oilpriceapi.com/auth/signup)

### Example 5: Correlation Analysis Between Commodities

Understand relationships between different energy commodities.

```python
from oilpriceapi import OilPriceAPI
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

client = OilPriceAPI()

# Get multiple commodities
commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD", "DIESEL_USD"]
data = {}

for commodity in commodities:
    df = client.prices.to_dataframe(
        commodity=commodity,
        start="2024-01-01",
        end="2024-12-31",
        interval="daily"
    )
    data[commodity] = df.set_index('date')['close']

# Create correlation matrix
df_combined = pd.DataFrame(data)
correlation_matrix = df_combined.corr()

# Visualize correlation heatmap
plt.figure(figsize=(10, 8))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0,
            square=True, linewidths=1, cbar_kws={"shrink": 0.8})
plt.title('Energy Commodity Correlation Matrix')
plt.tight_layout()
plt.savefig('commodity_correlation.png')

print(correlation_matrix)
```

**Research applications:** [Learn more](https://oilpriceapi.com/use-cases/research)

### Example 6: Price Forecast Using Machine Learning

Simple time series forecasting with scikit-learn.

```python
from oilpriceapi import OilPriceAPI
from sklearn.linear_model import LinearRegression
import numpy as np
import pandas as pd

client = OilPriceAPI()

# Get historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2023-01-01",
    end="2024-12-31",
    interval="daily"
)

# Prepare features
df['day_num'] = np.arange(len(df))
X = df[['day_num']].values
y = df['close'].values

# Train simple linear model
model = LinearRegression()
model.fit(X, y)

# Forecast next 30 days
future_days = np.arange(len(df), len(df) + 30).reshape(-1, 1)
predictions = model.predict(future_days)

print(f"Current Price: ${y[-1]:.2f}")
print(f"30-day forecast: ${predictions[-1]:.2f}")
print(f"Predicted change: {((predictions[-1] - y[-1]) / y[-1] * 100):.2f}%")

# Note: This is a simple example. For production forecasting,
# use more sophisticated models and validation techniques.
```

**Build advanced models with our API:** [View documentation](https://docs.oilpriceapi.com)

---

## 💻 Web & Mobile Applications

### Example 7: Real-Time Price Dashboard (Streamlit)

Create an interactive web dashboard for monitoring oil prices.

```python
import streamlit as st
from oilpriceapi import OilPriceAPI
import plotly.graph_objects as go
from datetime import datetime, timedelta

# Initialize API client
client = OilPriceAPI()

st.title("🛢️ Live Oil Price Dashboard")
st.markdown("Powered by [OilPriceAPI](https://oilpriceapi.com)")

# Commodity selector
commodity = st.selectbox(
    "Select Commodity",
    ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD", "DIESEL_USD"]
)

# Fetch current price
try:
    price = client.prices.get(commodity)

    col1, col2, col3 = st.columns(3)
    col1.metric("Current Price", f"${price.value:.2f}")
    col2.metric("24h Change", f"${price.change_24h:.2f}", f"{price.change_24h_pct:.2f}%")
    col3.metric("Update Time", price.updated_at.strftime("%H:%M:%S"))

    # Historical chart (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    df = client.prices.to_dataframe(
        commodity=commodity,
        start=start_date.strftime("%Y-%m-%d"),
        end=end_date.strftime("%Y-%m-%d"),
        interval="daily"
    )

    # Create interactive chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['close'],
        mode='lines',
        name=commodity,
        line=dict(color='#FF6B35', width=2)
    ))
    fig.update_layout(
        title=f"{commodity} - Last 30 Days",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        hovermode='x unified'
    )
    st.plotly_chart(fig, use_container_width=True)

    st.success(f"✅ Data updates every 5 minutes • [View all commodities](https://docs.oilpriceapi.com/commodities)")

except Exception as e:
    st.error(f"Error: {e}")
    st.info("Get your API key at [oilpriceapi.com/auth/signup](https://oilpriceapi.com/auth/signup)")

# Run with: streamlit run dashboard.py
```

**Deploy production dashboards:** [See pricing](https://oilpriceapi.com/pricing)

### Example 8: REST API Wrapper for Your App

Build a simple Flask API that wraps OilPriceAPI for your frontend.

```python
from flask import Flask, jsonify, request
from oilpriceapi import OilPriceAPI
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Initialize OilPriceAPI client
# Get your key at https://oilpriceapi.com/auth/signup
client = OilPriceAPI()

@app.route('/api/price/<commodity>', methods=['GET'])
def get_price(commodity):
    """Get current price for a commodity"""
    try:
        price = client.prices.get(commodity)
        return jsonify({
            'commodity': commodity,
            'price': price.value,
            'currency': 'USD',
            'change_24h': price.change_24h,
            'change_24h_pct': price.change_24h_pct,
            'updated_at': price.updated_at.isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/historical/<commodity>', methods=['GET'])
def get_historical(commodity):
    """Get historical data for a commodity"""
    start = request.args.get('start', '2024-01-01')
    end = request.args.get('end', '2024-12-31')

    try:
        df = client.prices.to_dataframe(
            commodity=commodity,
            start=start,
            end=end,
            interval='daily'
        )
        return jsonify(df.to_dict('records'))
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/commodities', methods=['GET'])
def list_commodities():
    """List available commodities"""
    return jsonify({
        'commodities': [
            'BRENT_CRUDE_USD',
            'WTI_USD',
            'NATURAL_GAS_USD',
            'DIESEL_USD',
            'GASOLINE_USD',
            'HEATING_OIL_USD'
        ],
        'docs': 'https://docs.oilpriceapi.com/commodities'
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)

# Run with: python app.py
```

**Integrate into your app:** [View integration guides](https://docs.oilpriceapi.com/integrations)

---

## 🔔 Monitoring & Alerts

### Example 9: Email Alerts for Price Thresholds

Send email notifications when prices cross specific thresholds.

```python
from oilpriceapi import OilPriceAPI
import smtplib
from email.mime.text import MIMEText
import time

client = OilPriceAPI()

def send_alert(commodity, price, threshold, direction):
    """Send email alert"""
    msg = MIMEText(f"""
    PRICE ALERT: {commodity}

    Current Price: ${price:.2f}
    Threshold: ${threshold:.2f}
    Direction: {direction}

    View live prices: https://oilpriceapi.com
    """)
    msg['Subject'] = f'🚨 Price Alert: {commodity} {direction} ${threshold}'
    msg['From'] = 'alerts@yourdomain.com'
    msg['To'] = 'your-email@example.com'

    # Configure your SMTP settings
    with smtplib.SMTP('smtp.gmail.com', 587) as server:
        server.starttls()
        server.login('your-email@gmail.com', 'your-password')
        server.send_message(msg)

def monitor_prices():
    """Monitor prices and send alerts"""
    thresholds = {
        'BRENT_CRUDE_USD': {'high': 80.0, 'low': 70.0},
        'WTI_USD': {'high': 75.0, 'low': 65.0}
    }

    while True:
        for commodity, limits in thresholds.items():
            price = client.prices.get(commodity)

            if price.value > limits['high']:
                send_alert(commodity, price.value, limits['high'], 'ABOVE')
            elif price.value < limits['low']:
                send_alert(commodity, price.value, limits['low'], 'BELOW')

        # Check every 5 minutes (aligned with API update frequency)
        time.sleep(300)

if __name__ == '__main__':
    print("Starting price monitor...")
    print("Get your API key at https://oilpriceapi.com/auth/signup")
    monitor_prices()
```

**Set up production alerts:** [Choose a plan](https://oilpriceapi.com/pricing)

### Example 10: Slack Bot for Team Notifications

Post daily price summaries to Slack.

```python
from oilpriceapi import OilPriceAPI
from slack_sdk import WebClient
from datetime import datetime

# Initialize clients
oil_client = OilPriceAPI()
slack_client = WebClient(token='your-slack-token')

def post_daily_summary():
    """Post daily oil price summary to Slack"""
    commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]

    message = "📊 *Daily Oil Price Summary*\n\n"

    for commodity in commodities:
        price = oil_client.prices.get(commodity)

        # Format with emoji based on change
        emoji = "📈" if price.change_24h > 0 else "📉"

        message += f"{emoji} *{commodity}*: ${price.value:.2f} "
        message += f"({price.change_24h_pct:+.2f}% 24h)\n"

    message += f"\n_Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n"
    message += "_Powered by <https://oilpriceapi.com|OilPriceAPI>_"

    slack_client.chat_postMessage(
        channel='#trading',
        text=message
    )

if __name__ == '__main__':
    post_daily_summary()
```

---

## 📤 Data Export & Integration

### Example 11: Export to Excel with Charts

Create formatted Excel reports with price data and charts.

```python
from oilpriceapi import OilPriceAPI
import pandas as pd
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

client = OilPriceAPI()

# Get historical data
df = client.prices.to_dataframe(
    commodity="BRENT_CRUDE_USD",
    start="2024-01-01",
    end="2024-12-31",
    interval="daily"
)

# Export to Excel
with pd.ExcelWriter('oil_prices_report.xlsx', engine='openpyxl') as writer:
    df.to_excel(writer, sheet_name='Data', index=False)

    # Add summary statistics
    summary = pd.DataFrame({
        'Metric': ['Average', 'Min', 'Max', 'Std Dev'],
        'Value': [
            df['close'].mean(),
            df['close'].min(),
            df['close'].max(),
            df['close'].std()
        ]
    })
    summary.to_excel(writer, sheet_name='Summary', index=False)

    workbook = writer.book
    worksheet = writer.sheets['Data']

    # Create chart
    chart = LineChart()
    chart.title = "Brent Crude Price Trend"
    chart.y_axis.title = "Price (USD)"
    chart.x_axis.title = "Date"

    data = Reference(worksheet, min_col=2, min_row=1, max_row=len(df)+1)
    chart.add_data(data, titles_from_data=True)

    worksheet.add_chart(chart, "E5")

print("✅ Report exported to oil_prices_report.xlsx")
print("📊 Get more data at https://oilpriceapi.com")
```

### Example 12: PostgreSQL Integration

Store price data in a PostgreSQL database for analysis.

```python
from oilpriceapi import OilPriceAPI
import psycopg2
from datetime import datetime

client = OilPriceAPI()

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="oil_prices",
    user="your_user",
    password="your_password"
)
cur = conn.cursor()

# Create table
cur.execute("""
    CREATE TABLE IF NOT EXISTS price_history (
        id SERIAL PRIMARY KEY,
        commodity VARCHAR(50),
        price DECIMAL(10, 2),
        date DATE,
        created_at TIMESTAMP DEFAULT NOW()
    )
""")

# Fetch and insert data
commodities = ["BRENT_CRUDE_USD", "WTI_USD", "NATURAL_GAS_USD"]

for commodity in commodities:
    price = client.prices.get(commodity)

    cur.execute("""
        INSERT INTO price_history (commodity, price, date)
        VALUES (%s, %s, %s)
    """, (commodity, price.value, datetime.now().date()))

conn.commit()
cur.close()
conn.close()

print("✅ Data saved to PostgreSQL")
print("📊 Powered by https://oilpriceapi.com")
```

---

## 🚀 Getting Started

Ready to build with these examples?

1. **[Sign up for free](https://oilpriceapi.com/auth/signup)** - Get 1,000 free requests/month
2. **[Install the SDK](https://pypi.org/project/oilpriceapi/)** - `pip install oilpriceapi`
3. **[Read the docs](https://docs.oilpriceapi.com/sdk/python)** - Complete API reference
4. **[Choose a plan](https://oilpriceapi.com/pricing)** - Upgrade for more requests

## 📖 More Resources

- **[Complete API Documentation](https://docs.oilpriceapi.com)** - Full REST API reference
- **[Available Commodities](https://docs.oilpriceapi.com/commodities)** - List of all supported commodities
- **[GitHub Repository](https://github.com/oilpriceapi/python-sdk)** - Source code and issues
- **[Support](mailto:support@oilpriceapi.com)** - Get help from our team

## 💡 Need Help?

- **Questions about the API?** [Read the FAQ](https://oilpriceapi.com/faq)
- **Feature requests?** [Open an issue](https://github.com/oilpriceapi/python-sdk/issues)
- **Custom enterprise needs?** [Contact sales](mailto:sales@oilpriceapi.com)

---

**Built something cool?** Share it with us at support@oilpriceapi.com!

**Want more examples?** Visit [OilPriceAPI.com](https://oilpriceapi.com) for tutorials and use cases.
