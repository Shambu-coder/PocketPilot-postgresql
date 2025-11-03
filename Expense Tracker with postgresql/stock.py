from datetime import datetime
import yfinance as yf
from tabulate import tabulate
from utils import normalize_stock_symbol, get_valid_number, review_and_confirm, format_currency, confirm_action
from colorama import Fore, Style
import psycopg2
from decimal import Decimal

class StockManager:
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cursor = db_conn.cursor()
        self.migrate_stock_transactions_dates()

    def get_live_price(self, symbol):
        symbol = normalize_stock_symbol(symbol)
        try:
            stock = yf.Ticker(symbol)
            data = stock.history(period="5d")
            if data.empty:
                print(f"{Fore.RED}No price data for {symbol}. Check the stock symbol.{Style.RESET_ALL}")
                return None
            return round(float(data["Close"].iloc[-1]), 2)
        except Exception as e:
            print(f"{Fore.RED}Unable to fetch price for {symbol}. Error: {e}{Style.RESET_ALL}")
            return None

    def buy_stock(self, user_id, symbol, quantity):
        self.display_suggestions()
        symbol = input("Enter NSE stock symbol (without .NS) [RELIANCE]: ").strip().upper()
        symbol = 'RELIANCE' if not symbol else symbol
        quantity_input = get_valid_number("Enter quantity [1]: ", default=1, min_value=1)
        if quantity_input is None:
            return
        quantity = int(quantity_input)

        price_choice = input("Use market price? (y/n): ").lower()
        price = self.get_live_price(symbol) if price_choice in ['', 'y'] else get_valid_number("Enter manual price (₹): ", min_value=0.01)
        if price is None:
            print(f"{Fore.RED}Unable to fetch price or invalid manual price.{Style.RESET_ALL}")
            return
        price = float(price)

        total_cost = float(quantity * price)
        balance = self.get_balance(user_id)
        if total_cost > balance:
            print(f"{Fore.RED}Insufficient funds. Need {format_currency(total_cost)}, but balance is {format_currency(balance)}.{Style.RESET_ALL}")
            return

        date = datetime.now().strftime("%d-%m-%Y")
        symbol = normalize_stock_symbol(symbol)

        if not review_and_confirm(
            "Review Buy Transaction",
            ["Symbol", "Quantity", "Price", "Total (₹)", "Balance After (₹)", "Date"],
            [symbol, quantity, format_currency(price), format_currency(total_cost), format_currency(balance - total_cost), date],
            "Proceed with this buy?",
            "Buy cancelled."
        ):
            return

        try:
            self.cursor.execute("SELECT id, quantity, avg_buy_price FROM portfolio WHERE user_id=%s AND stock_symbol=%s", (user_id, symbol))
            record = self.cursor.fetchone()

            if record:
                pid, old_qty, old_avg = record
                old_qty = int(old_qty)
                old_avg = float(old_avg)
                new_qty = old_qty + quantity
                new_avg = float(((old_qty * old_avg) + (quantity * price)) / new_qty)
                self.cursor.execute("UPDATE portfolio SET quantity=%s, avg_buy_price=%s WHERE id=%s", (new_qty, new_avg, pid))
            else:
                self.cursor.execute("INSERT INTO portfolio (user_id, stock_symbol, quantity, avg_buy_price) VALUES (%s, %s, %s, %s)",
                                  (user_id, symbol, quantity, price))

            self.cursor.execute("INSERT INTO stock_transactions (user_id, stock_symbol, transaction_type, quantity, price, date) VALUES (%s, %s, %s, %s, %s, %s)",
                              (user_id, symbol, "BUY", quantity, price, date))

            self.cursor.execute(
                "INSERT INTO expenses (user_id, name, category, amount, type, date) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, f"Buy {symbol}", "Stock Purchase", total_cost, "expense", date)
            )

            self.conn.commit()
            print(f"{Fore.GREEN}Bought {quantity} shares of {symbol} at {format_currency(price)}.{Style.RESET_ALL}")
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error processing buy transaction: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def sell_stock(self, user_id, symbol, quantity):
        self.view_portfolio(user_id)
        symbol = input("Enter NSE stock symbol (without .NS) [RELIANCE]: ").strip().upper()
        symbol = 'RELIANCE' if not symbol else symbol
        quantity_input = get_valid_number("Enter quantity [1]: ", default=1, min_value=1)
        if quantity_input is None:
            return
        quantity = int(quantity_input)

        price_choice = input("Use latest market price? (y/n): ").lower()
        price = self.get_live_price(symbol) if price_choice in ['', 'y'] else get_valid_number("Enter manual price (₹): ", min_value=0.01)
        if price is None:
            print(f"{Fore.RED}Unable to fetch price or invalid manual price.{Style.RESET_ALL}")
            return
        price = float(price)

        total_gain = float(quantity * price)
        date = datetime.now().strftime("%d-%m-%Y")
        symbol = normalize_stock_symbol(symbol)

        try:
            self.cursor.execute("SELECT id, quantity, avg_buy_price FROM portfolio WHERE user_id=%s AND stock_symbol=%s", (user_id, symbol))
            record = self.cursor.fetchone()

            if not record:
                print(f"{Fore.RED}You do not own any shares of {symbol}.{Style.RESET_ALL}")
                return

            pid, old_qty, avg_price = record
            old_qty = int(old_qty)
            if quantity > old_qty:
                print(f"{Fore.RED}You only have {old_qty} shares of {symbol}.{Style.RESET_ALL}")
                return

            if not review_and_confirm(
                "Review Sell Transaction",
                ["Symbol", "Quantity", "Price", "Total (₹)", "Date"],
                [symbol, quantity, format_currency(price), format_currency(total_gain), date],
                "Proceed with this sell?",
                "Sell cancelled."
            ):
                return

            new_qty = old_qty - quantity
            if new_qty == 0:
                self.cursor.execute("DELETE FROM portfolio WHERE id=%s", (pid,))
            else:
                self.cursor.execute("UPDATE portfolio SET quantity=%s WHERE id=%s", (new_qty, pid))

            self.cursor.execute("INSERT INTO stock_transactions (user_id, stock_symbol, transaction_type, quantity, price, date) VALUES (%s, %s, %s, %s, %s, %s)",
                              (user_id, symbol, "SELL", quantity, price, date))

            self.cursor.execute(
                "INSERT INTO expenses (user_id, name, category, amount, type, date) VALUES (%s, %s, %s, %s, %s, %s)",
                (user_id, f"Sell {symbol}", "Stock Sale", total_gain, "income", date)
            )

            self.conn.commit()
            print(f"{Fore.GREEN}Sold {quantity} shares of {symbol} at {format_currency(price)}.{Style.RESET_ALL}")
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error processing sell transaction: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def view_portfolio(self, user_id):
        try:
            self.cursor.execute("SELECT stock_symbol, quantity, avg_buy_price FROM portfolio WHERE user_id=%s", (user_id,))
            rows = self.cursor.fetchall()
            if not rows:
                print(f"{Fore.RED}Your portfolio is empty.{Style.RESET_ALL}")
                return

            table = []
            total_invested, total_current = 0, 0

            for symbol, qty, avg_price in rows:
                qty = int(qty)
                avg_price = float(avg_price)
                live_price = self.get_live_price(symbol) or 0
                live_price = float(live_price)
                invested = qty * avg_price
                current = qty * live_price
                profit = current - invested
                profit_pct = (profit / invested * 100) if invested else 0
                live_price_str = f"{Fore.BLUE}{format_currency(live_price)}{Style.RESET_ALL}" if live_price else "0.00"
                profit_str = f"{Fore.GREEN}{format_currency(profit)}{Style.RESET_ALL}" if profit >= 0 else f"{Fore.RED}{format_currency(profit)}{Style.RESET_ALL}"
                profit_pct_str = f"{Fore.GREEN}{profit_pct:.2f}%{Style.RESET_ALL}" if profit_pct >= 0 else f"{Fore.RED}{profit_pct:.2f}%{Style.RESET_ALL}"
                table.append([symbol, qty, format_currency(avg_price), live_price_str, format_currency(invested), format_currency(current), profit_str, profit_pct_str])
                total_invested += invested
                total_current += current

            print("\n--- Portfolio Summary ---")
            print(tabulate(table, headers=["Symbol", "Qty", "Avg Buy", "Live Price", "Invested (₹)", "Current (₹)", "P/L (₹)", "P/L %"], tablefmt="pretty"))
            total_pl = total_current - total_invested
            total_pl_pct = ((total_current - total_invested) / total_invested * 100) if total_invested else 0
            pl_color = Fore.GREEN if total_pl >= 0 else Fore.RED
            print(f"\nTotal Invested: {format_currency(total_invested)} | Current Value: {format_currency(total_current)} | P/L: {pl_color}{format_currency(total_pl)} ({total_pl_pct:.2f}%){Style.RESET_ALL}")
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error fetching portfolio: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def view_stock_transactions(self, user_id):
        try:
            self.cursor.execute("SELECT stock_symbol, transaction_type, quantity, price, date FROM stock_transactions WHERE user_id=%s ORDER BY to_date(date, 'DD-MM-YYYY') DESC", (user_id,))
            rows = self.cursor.fetchall()
            if not rows:
                print(f"{Fore.RED}No stock transactions found.{Style.RESET_ALL}")
                return

            formatted_rows = []
            for row in rows:
                symbol, trans_type, qty, price, date = row
                formatted_rows.append([symbol, trans_type, qty, format_currency(float(price)), date])

            print("\n--- Stock Transaction History ---")
            print(tabulate(formatted_rows, headers=["Symbol", "Type", "Qty", "Price", "Date"], tablefmt="pretty"))
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error fetching transactions: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def display_suggestions(self):
        suggestions = [
            ["RELIANCE.NS", "Reliance Industries", 15.0],
            ["TCS.NS", "Tata Consultancy Services", 12.0],
            ["HDFCBANK.NS", "HDFC Bank", 14.0]
        ]
        print("\n--- Suggested Nifty 50 Stocks to Buy ---")
        print(tabulate(suggestions, headers=["Symbol", "Company Name", "Est. Annual Return (%)"], tablefmt="pretty"))
        print("Note: Estimated returns are based on historical trends and not guaranteed. Use 'Buy Stock' to invest.")

    def migrate_stock_transactions_dates(self):
        try:
            self.cursor.execute("SELECT id, date FROM stock_transactions")
            rows = self.cursor.fetchall()
            for row in rows:
                trans_id, date = row
                try:
                    new_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S").strftime("%d-%m-%Y")
                    self.cursor.execute("UPDATE stock_transactions SET date=%s WHERE id=%s", (new_date, trans_id))
                except ValueError:
                    pass
            self.conn.commit()
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error migrating dates: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def get_balance(self, user_id):
        try:
            self.cursor.execute("SELECT initial_balance FROM users WHERE id=%s", (user_id,))
            initial_balance = self.cursor.fetchone()[0] or Decimal('0.0')
            self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s AND type='income'", (user_id,))
            income = self.cursor.fetchone()[0] or Decimal('0.0')
            self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s AND type='expense'", (user_id,))
            expense = self.cursor.fetchone()[0] or Decimal('0.0')
            return float(initial_balance) + float(income) - float(expense)
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error calculating balance: {e}{Style.RESET_ALL}")
            self.conn.rollback()
            return 0.0

    def stock_menu(self, user_id, full_name):
        while True:
            print(f"\n--- Stock Management for {full_name} ---")
            print("1. Buy Stock")
            print("2. Sell Stock")
            print("3. View Stock Portfolio")
            print("4. View Stock Transactions")
            print("5. View Suggested Stocks")
            print("6. Back")
            sub_choice = input("Choose an option: ").strip()

            if sub_choice == '1':
                self.buy_stock(user_id, None, None)
            elif sub_choice == '2':
                self.sell_stock(user_id, None, None)
            elif sub_choice == '3':
                self.view_portfolio(user_id)
            elif sub_choice == '4':
                self.view_stock_transactions(user_id)
            elif sub_choice == '5':
                self.display_suggestions()
            elif sub_choice == '6':
                if confirm_action("back to the home menu?", "Cancelled. Returning to stock menu."):
                    print(f"{Fore.GREEN}Returning to home menu.{Style.RESET_ALL}")
                    break
            else:
                print(f"{Fore.RED}Invalid option. Choose 1 to 6.{Style.RESET_ALL}")