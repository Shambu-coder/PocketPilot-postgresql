import psycopg2
from getpass import getpass
from utils import get_valid_number, confirm_action
from colorama import Fore, Style

class UserManager:
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cursor = db_conn.cursor()

    def register(self):
        """Register a new user."""
        full_name = input("Enter full name: ").strip()
        username = input("Enter new username: ").strip()
        if not full_name:
            print(f"{Fore.RED}Full name cannot be empty.{Style.RESET_ALL}")
            return
        if not username:
            print(f"{Fore.RED}Username cannot be empty.{Style.RESET_ALL}")
            return
        password = getpass("Enter password: ")
        confirm_password = getpass("Confirm password: ")
        if password != confirm_password:
            print(f"{Fore.RED}Passwords do not match.{Style.RESET_ALL}")
            return

        initial_balance = get_valid_number("Enter initial balance [0]: ", default=0.0, min_value=0.0)
        if initial_balance is None:
            return

        if not confirm_action("Register with these details?", "Registration cancelled."):
            return

        try:
            self.cursor.execute(
                'INSERT INTO users (username, full_name, password, initial_balance) VALUES (%s, %s, %s, %s)',
                (username, full_name, password, initial_balance)
            )
            self.conn.commit()
            print(f"{Fore.GREEN}Registration successful. You can now log in.{Style.RESET_ALL}")
        except psycopg2.IntegrityError as e:
            print(f"{Fore.RED}Username already taken. Choose a different one.{Style.RESET_ALL}")
            self.conn.rollback()

    def login(self):
        """Login and return user ID and full name."""
        username = input("Enter username: ")
        password = getpass("Enter password: ")
        try:
            self.cursor.execute("SELECT id, full_name FROM users WHERE username=%s AND password=%s", (username, password))
            result = self.cursor.fetchone()
            if result:
                print(f"{Fore.GREEN}Login successful. Welcome back!{Style.RESET_ALL}")
                return result[0], result[1]
            else:
                print(f"{Fore.RED}Incorrect username or password.{Style.RESET_ALL}")
                return None, None
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error during login: {e}{Style.RESET_ALL}")
            self.conn.rollback()
            return None, None