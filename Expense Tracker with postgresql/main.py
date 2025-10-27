from database import DatabaseManager
from user import UserManager
from expense import ExpenseManager
from stock import StockManager
from utils import confirm_action
from colorama import init, Fore, Style

def main():
    init()  # Initialize colorama
    db = DatabaseManager(db_name="finance_tracker", user="postgres", password="your_password", host="localhost", port="5432")
    try:
        user_manager = UserManager(db.conn)
        expense_manager = ExpenseManager(db.conn)
        stock_manager = StockManager(db.conn)

        while True:
            user_id, full_name = None, None
            while not user_id:
                print("\n--- Welcome to Finance Tracker ---")
                print("1. Register")
                print("2. Login")
                print("3. Exit")
                choice = input("Choose an option: ").strip()
                if choice == '1':
                    user_manager.register()
                elif choice == '2':
                    user_id, full_name = user_manager.login()
                elif choice == '3':
                    if not confirm_action("Are you sure you want to exit?", "Exit cancelled."):
                        continue
                    print(f"{Fore.GREEN}Application closed successfully.{Style.RESET_ALL}")
                    return
                else:
                    print(f"{Fore.RED}Invalid option. Choose 1, 2, or 3.{Style.RESET_ALL}")

            while True:
                print(f"\n--- Welcome, {full_name} ---")
                print("1. Expense Management")
                print("2. Stock Management")
                print("3. Logout")
                choice = input("Choose an option: ").strip()

                if choice == '1':
                    expense_manager.expense_menu(user_id, full_name)
                elif choice == '2':
                    stock_manager.stock_menu(user_id, full_name)
                elif choice == '3':
                    if confirm_action("logout to the main menu?", "Cancelled."):
                        print(f"{Fore.GREEN}Returning to main menu.{Style.RESET_ALL}")
                        break
                else:
                    print(f"{Fore.RED}Invalid option. Choose 1, 2, or 3.{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}An error occurred: {e}{Style.RESET_ALL}")
    finally:
        db.close()  # Cleanly close DB connection

if __name__ == "__main__":
    main()