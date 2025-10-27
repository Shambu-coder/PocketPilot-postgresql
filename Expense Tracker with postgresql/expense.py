from datetime import datetime
from tabulate import tabulate
from utils import validate_date, get_valid_number, select_category, review_and_confirm, format_currency, confirm_action
from colorama import Fore, Style
import psycopg2

class ExpenseManager:
    def __init__(self, db_conn):
        self.conn = db_conn
        self.cursor = db_conn.cursor()

    def add_expense(self, user_id):
        """Add a new income or expense transaction with type, category, then description."""
        while True:
            print("\nSelect type:")
            print("1. Income")
            print("2. Expense")
            type_choice = input("Choose type number [1]: ").strip()
            exp_type = 'income' if type_choice in ['', '1'] else 'expense' if type_choice == '2' else None
            if exp_type is None:
                print(f"{Fore.RED}Invalid type. Choose 1 for Income or 2 for Expense.{Style.RESET_ALL}")
                return

            category = select_category(exp_type)
            if category is None:
                print(f"{Fore.RED}Category selection cancelled.{Style.RESET_ALL}")
                return

            name = input("Enter transaction name/description: ").strip()
            if not name:
                print(f"{Fore.RED}Transaction name cannot be empty.{Style.RESET_ALL}")
                return

            amount = get_valid_number("Enter amount: ", min_value=0.01)
            if amount is None:
                return

            if exp_type == 'expense':
                try:
                    current_balance = self.get_balance(user_id)
                    if amount > current_balance:
                        print(f"{Fore.RED}Warning: Expense amount {format_currency(amount)} exceeds current balance {format_currency(current_balance)}.{Style.RESET_ALL}")
                        if not confirm_action("Proceed with this expense anyway?", "Transaction cancelled due to insufficient funds."):
                            return
                except psycopg2.Error as e:
                    print(f"{Fore.RED}Error checking balance: {e}{Style.RESET_ALL}")
                    self.conn.rollback()
                    return

            date_input = input("Enter date (DD-MM-YYYY, press Enter for today): ").strip()
            date = date_input if date_input and validate_date(date_input) else datetime.now().strftime('%d-%m-%Y')
            if date_input and not validate_date(date_input):
                print(f"{Fore.RED}Invalid date format. Use DD-MM-YYYY (e.g., 27-08-2025).{Style.RESET_ALL}")
                return

            if not review_and_confirm(
                "Review Transaction",
                ["Type", "Category", "Name", "Amount", "Date"],
                [exp_type.capitalize(), category, name, format_currency(amount), date],
                "Add this transaction?",
                "Transaction cancelled."
            ):
                return

            try:
                self.cursor.execute(
                    "INSERT INTO expenses (user_id, name, category, amount, type, date) VALUES (%s, %s, %s, %s, %s, %s)",
                    (user_id, name, category, amount, exp_type, date)
                )
                self.conn.commit()
                print(f"{Fore.GREEN}Transaction added successfully.{Style.RESET_ALL}")
            except psycopg2.Error as e:
                print(f"{Fore.RED}Error adding transaction: {e}{Style.RESET_ALL}")
                self.conn.rollback()
                return

            if not confirm_action("Continue adding transactions?", "Stopped adding transactions."):
                break

    def edit_expense(self, user_id):
        """Edit an existing expense transaction."""
        rows = self.view_expenses(user_id)
        if not rows:
            print(f"{Fore.RED}No transactions available to edit.{Style.RESET_ALL}")
            return

        try:
            expense_id = int(input("Enter Transaction ID to edit: "))
            self.cursor.execute("SELECT id, user_id, name, category, amount, type, date FROM expenses WHERE id=%s AND user_id=%s", (expense_id, user_id))
            row = self.cursor.fetchone()
            if not row:
                print(f"{Fore.RED}Transaction ID {expense_id} not found.{Style.RESET_ALL}")
                return

            current_name, current_category, current_amount, current_type, current_date = row[2], row[3], row[4], row[5], row[6]

            print("\n--- Press Enter to keep current value ---")
            name = input(f"Enter new name [{current_name}]: ").strip() or current_name
            amount = get_valid_number(f"Enter new amount [{format_currency(current_amount)}]: ", default=current_amount, min_value=0.01)
            if amount is None:
                return
            date_input = input(f"Enter new date (DD-MM-YYYY) [{current_date}]: ").strip()
            date = date_input if date_input and validate_date(date_input) else current_date
            if date_input and not validate_date(date_input):
                print(f"{Fore.RED}Invalid date format. Use DD-MM-YYYY (e.g., 27-08-2025).{Style.RESET_ALL}")
                return

            exp_type = current_type
            category = select_category(exp_type, default_category=current_category)
            if category is None:
                return

            if not review_and_confirm(
                "Review Changes",
                ["Name", "Amount", "Type", "Category", "Date"],
                [name, format_currency(amount), exp_type.capitalize(), category, date],
                "Save these changes?",
                "Changes cancelled."
            ):
                return

            try:
                self.cursor.execute(
                    "UPDATE expenses SET name=%s, category=%s, amount=%s, type=%s, date=%s WHERE id=%s AND user_id=%s",
                    (name, category, amount, exp_type, date, expense_id, user_id)
                )
                self.conn.commit()
                print(f"{Fore.GREEN}Transaction updated successfully.{Style.RESET_ALL}")
            except psycopg2.Error as e:
                print(f"{Fore.RED}Error updating transaction: {e}{Style.RESET_ALL}")
                self.conn.rollback()
                return
        except ValueError:
            print(f"{Fore.RED}Invalid Transaction ID. Enter a number from the list.{Style.RESET_ALL}")

    def delete_expense(self, user_id):
        """Delete an expense transaction."""
        rows = self.view_expenses(user_id)
        if not rows:
            print(f"{Fore.RED}No transactions available to delete.{Style.RESET_ALL}")
            return

        try:
            expense_id = int(input("Enter Transaction ID to delete: "))
            self.cursor.execute("SELECT name, category, amount, type, date FROM expenses WHERE id=%s AND user_id=%s", (expense_id, user_id))
            row = self.cursor.fetchone()
            if not row:
                print(f"{Fore.RED}Transaction ID {expense_id} not found.{Style.RESET_ALL}")
                return

            name, category, amount, trans_type, date = row
            if not review_and_confirm(
                "Review Transaction to Delete",
                ["Name", "Amount", "Type", "Category", "Date"],
                [name, format_currency(amount), trans_type.capitalize(), category, date],
                "Delete this transaction?",
                "Deletion cancelled."
            ):
                return

            try:
                self.cursor.execute("DELETE FROM expenses WHERE id=%s AND user_id=%s", (expense_id, user_id))
                self.conn.commit()
                print(f"{Fore.GREEN}Transaction deleted successfully.{Style.RESET_ALL}")
            except psycopg2.Error as e:
                print(f"{Fore.RED}Error deleting transaction: {e}{Style.RESET_ALL}")
                self.conn.rollback()
                return
        except ValueError:
            print(f"{Fore.RED}Invalid Transaction ID. Enter a number from the list.{Style.RESET_ALL}")

    def view_expenses(self, user_id):
        """Display all transactions for a user."""
        try:
            self.cursor.execute("SELECT initial_balance FROM users WHERE id=%s", (user_id,))
            initial_balance = self.cursor.fetchone()[0] or 0.0

            self.cursor.execute("SELECT id, name, category, amount, type, date FROM expenses WHERE user_id=%s ORDER BY id", (user_id,))
            rows = self.cursor.fetchall()

            print("\n--- Transaction History ---")
            table = [
                ["", "", "Initial Balance", "", "", "", f"{Fore.GREEN if initial_balance >= 0 else Fore.RED}{format_currency(initial_balance)}{Style.RESET_ALL}"]
            ]
            running_balance = initial_balance

            for row in rows:
                trans_id, name, category, amount, trans_type, date = row
                income = format_currency(amount) if trans_type == 'income' else ""
                expense = format_currency(amount) if trans_type == 'expense' else ""
                running_balance += amount if trans_type == 'income' else -amount
                table.append([
                    trans_id,
                    date,
                    name,
                    category,
                    f"{Fore.GREEN}{income}{Style.RESET_ALL}" if income else "",
                    f"{Fore.RED}{expense}{Style.RESET_ALL}" if expense else "",
                    f"{Fore.GREEN if running_balance >= 0 else Fore.RED}{format_currency(running_balance)}{Style.RESET_ALL}"
                ])

            if not rows and initial_balance == 0:
                print(f"{Fore.RED}No transactions or initial balance found.{Style.RESET_ALL}")
            else:
                print(tabulate(table, headers=["ID", "Date", "Description", "Category", "Income", "Expense", "Balance"], tablefmt="pretty"))
            return rows
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error fetching transactions: {e}{Style.RESET_ALL}")
            self.conn.rollback()
            return []

    def view_balance(self, user_id):
        """Display current balance for a user."""
        balance = self.get_balance(user_id)
        print(f"\nBalance: {Fore.GREEN if balance >= 0 else Fore.RED}{format_currency(balance)}{Style.RESET_ALL}")

    def monthly_summary(self, user_id):
        """Display monthly summary of transactions."""
        try:
            self.cursor.execute("SELECT initial_balance FROM users WHERE id=%s", (user_id,))
            initial_balance = self.cursor.fetchone()[0] or 0.0

            self.cursor.execute("""
                SELECT to_char(to_date(date, 'DD-MM-YYYY'), 'MM-YYYY') as month,
                       SUM(CASE WHEN type='income' THEN amount ELSE 0 END) as total_income,
                       SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) as total_expense
                FROM expenses
                WHERE user_id=%s
                GROUP BY to_char(to_date(date, 'DD-MM-YYYY'), 'MM-YYYY')
                ORDER BY to_date(date, 'DD-MM-YYYY')
            """, (user_id,))
            rows = self.cursor.fetchall()

            if not rows:
                print(f"{Fore.RED}No transactions found for monthly summary.{Style.RESET_ALL}")
                return

            print("\n--- Monthly Summary ---")
            table = [["Month", "Total Income", "Total Expense", "Net Balance"]]
            running_balance = initial_balance
            for month, income, expense in rows:
                income = income or 0.0
                expense = expense or 0.0
                running_balance += (income - expense)
                table.append([
                    month,
                    f"{Fore.GREEN}{format_currency(income)}{Style.RESET_ALL}",
                    f"{Fore.RED}{format_currency(expense)}{Style.RESET_ALL}",
                    f"{Fore.GREEN if running_balance >= 0 else Fore.RED}{format_currency(running_balance)}{Style.RESET_ALL}"
                ])
            print(tabulate(table, headers="firstrow", tablefmt="pretty"))
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error fetching monthly summary: {e}{Style.RESET_ALL}")
            self.conn.rollback()

    def get_balance(self, user_id):
        """Calculate current balance for a user."""
        try:
            self.cursor.execute("SELECT initial_balance FROM users WHERE id=%s", (user_id,))
            initial_balance = self.cursor.fetchone()[0] or 0.0
            self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s AND type='income'", (user_id,))
            income = self.cursor.fetchone()[0] or 0.0
            self.cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id=%s AND type='expense'", (user_id,))
            expense = self.cursor.fetchone()[0] or 0.0
            return initial_balance + income - expense
        except psycopg2.Error as e:
            print(f"{Fore.RED}Error calculating balance: {e}{Style.RESET_ALL}")
            self.conn.rollback()
            return 0.0

    def expense_menu(self, user_id, full_name):
        """Display and handle expense management menu."""
        while True:
            print(f"\n--- Expense Management for {full_name} ---")
            print("1. Add Income/Expense Transaction")
            print("2. View Income/Expense Transactions")
            print("3. View Balance")
            print("4. Edit Income/Expense Transaction")
            print("5. Delete Income/Expense Transaction")
            print("6. Monthly Summary")
            print("7. Back")
            sub_choice = input("Choose an option: ").strip()

            if sub_choice == '1':
                self.add_expense(user_id)
            elif sub_choice == '2':
                self.view_expenses(user_id)
            elif sub_choice == '3':
                self.view_balance(user_id)
            elif sub_choice == '4':
                self.edit_expense(user_id)
            elif sub_choice == '5':
                self.delete_expense(user_id)
            elif sub_choice == '6':
                self.monthly_summary(user_id)
            elif sub_choice == '7':
                if confirm_action("back to the home menu?", "Cancelled. Returning to expense menu."):
                    print(f"{Fore.GREEN}Returning to home menu.{Style.RESET_ALL}")
                    break
            else:
                print(f"{Fore.RED}Invalid option. Choose 1 to 7.{Style.RESET_ALL}")