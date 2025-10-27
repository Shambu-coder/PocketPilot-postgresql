import psycopg2
from psycopg2 import sql

class DatabaseManager:
    def __init__(self, db_name="finance_tracker", user="postgres", password="Root", host="localhost", port="5432"):
        self.conn = psycopg2.connect(
            dbname=db_name,
            user=user,
            password="Root",  # Ensure this is "Root" or the password used in psql
            host=host,
            port=port
        )
        self.conn.set_session(autocommit=False)
        self.cursor = self.conn.cursor()
        self.setup_database()
    # ... rest of the code unchanged ...

    def setup_database(self):
        """Initialize database tables."""
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                full_name VARCHAR(255) NOT NULL,
                password VARCHAR(255) NOT NULL,
                initial_balance NUMERIC DEFAULT 0.0
            )
        """)

        # Expenses table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                name VARCHAR(255),
                category VARCHAR(255),
                amount NUMERIC,
                type VARCHAR(50) CHECK (type IN ('income', 'expense')),
                date VARCHAR(10),
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Portfolio table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                stock_symbol VARCHAR(50) NOT NULL,
                quantity INTEGER NOT NULL,
                avg_buy_price NUMERIC NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Stock transactions table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_transactions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL,
                stock_symbol VARCHAR(50) NOT NULL,
                transaction_type VARCHAR(50) NOT NULL,
                quantity INTEGER NOT NULL,
                price NUMERIC NOT NULL,
                date VARCHAR(10) NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()