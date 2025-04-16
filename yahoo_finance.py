import yfinance as yf
from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("yahoo_finance")

@mcp.tool()
async def get_stock_price(symbol: str) -> str:
    """
    Get the current stock price for a given stock symbol.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        Current stock price or an error message.
    """
    try:
        if not symbol:
            return "Error: Missing 'symbol' in arguments."

        stock = yf.Ticker(symbol)
        data = stock.history(period="1d")
        if data.empty:
            return f"No data found for stock symbol: {symbol}"
        current_price = data['Close'].iloc[-1]
        return f"The current price of {symbol} is ${current_price:.2f}"
    except Exception as e:
        return f"Error fetching stock price for {symbol}: {str(e)}"

@mcp.tool()
async def get_company_info(symbol: str) -> str:
    """
    Get detailed information about a company.

    Args:
        symbol: Stock symbol (e.g., "AAPL")

    Returns:
        Company information or an error message.
    """
    try:
        if not symbol:
            return "Error: Missing 'symbol' in arguments."

        stock = yf.Ticker(symbol)
        info = stock.info
        if not info:
            return f"No information found for stock symbol: {symbol}"
        details = f"""
                    Company Name: {info.get('longName', 'N/A')}
                    Sector: {info.get('sector', 'N/A')}
                    Industry: {info.get('industry', 'N/A')}
                    Country: {info.get('country', 'N/A')}
                    Market Cap: ${info.get('marketCap', 'N/A'):,}
                    Employees: {info.get('fullTimeEmployees', 'N/A')}
                    Website: {info.get('website', 'N/A')}
                    """
        return details
    except Exception as e:
        return f"Error fetching company info for {symbol}: {str(e)}"

@mcp.tool()
async def get_historical_data(symbol: str, start_date: str, end_date: str) -> str:
    """
    Get historical stock price data for a given date range.

    Args:
        symbol: Stock symbol (e.g., "AAPL")
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format

    Returns:
        Historical stock price data or an error message.
    """
    try:
        # Validate required fields
        if not symbol or not start_date or not end_date:
            return "Error: Missing required fields ('symbol', 'start_date', 'end_date')."

        stock = yf.Ticker(symbol)
        data = stock.history(start=start_date, end=end_date)
        if data.empty:
            return f"No historical data found for {symbol} between {start_date} and {end_date}"

        # Format the historical data into a readable string
        formatted_data = []
        for index, row in data.iterrows():
            formatted_data.append(f"""
Date: {index.date()}
Open: ${row['Open']:.2f}
High: ${row['High']:.2f}
Low: ${row['Low']:.2f}
Close: ${row['Close']:.2f}
Volume: {row['Volume']:,}
""")
        return "\n---\n".join(formatted_data)
    except Exception as e:
        return f"Error fetching historical data for {symbol}: {str(e)}"


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')