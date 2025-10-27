from datetime import datetime
from typing import List, Optional
from tabulate import tabulate
from colorama import Fore, Style

def validate_date(date_str):
    """Validate date format (DD-MM-YYYY)."""
    try:
        datetime.strptime(date_str, '%d-%m-%Y')
        return True
    except ValueError:
        return False

def confirm_action(prompt, cancel_message):
    """Handle yes/no confirmation prompts."""
    confirm = input(f"\n{prompt} (y/n): ").lower()
    if confirm != 'y':
        print(f"{Fore.RED}{cancel_message}{Style.RESET_ALL}")
        return False
    return True

def format_currency(value: float) -> str:
    """Format a number as currency with ₹ symbol."""
    return f"₹{value:.2f}"

def get_valid_number(prompt: str, default: Optional[float] = None, min_value: float = 0.0) -> Optional[float]:
    """Prompt for a numeric input and validate it."""
    try:
        user_input = input(prompt).strip()
        if user_input == '' and default is not None:
            return default
        number = float(user_input)
        if number < min_value:
            print(f"{Fore.RED}Value must be at least {format_currency(min_value)}. Please try again.{Style.RESET_ALL}")
            return None
        return number
    except ValueError:
        print(f"{Fore.RED}Invalid input. Please enter a valid number (e.g., 500.00).{Style.RESET_ALL}")
        return None

def select_category(exp_type: str, default_category: Optional[str] = None) -> Optional[str]:
    """Prompt user to select a category for a transaction."""
    categories = (
        ['Salary', 'Bonus', 'Interest', 'Gift', 'Stock Sale', 'Other Income']
        if exp_type == 'income'
        else ['Food', 'Rent', 'Transport', 'Bills', 'Shopping', 'Stock Purchase', 'Other Expense']
    )
    print(f"\nSelect {'Income' if exp_type == 'income' else 'Expense'} Category:")
    for idx, cat in enumerate(categories, 1):
        print(f"{idx}. {cat}")

    default_idx = categories.index(default_category) + 1 if default_category in categories else 1
    prompt = f"Choose category number [{default_idx}]: "

    try:
        choice = input(prompt).strip()
        choice = default_idx if choice == '' else int(choice)
        if 1 <= choice <= len(categories):
            return categories[choice - 1]
        print(f"{Fore.RED}Please choose a number between 1 and {len(categories)}.{Style.RESET_ALL}")
        return None
    except ValueError:
        print(f"{Fore.RED}Invalid input. Enter a number or press Enter for default.{Style.RESET_ALL}")
        return None

def review_and_confirm(title: str, headers: List[str], data: List, confirm_message: str, cancel_message: str) -> bool:
    """Display a review table and prompt for confirmation."""
    print(f"\n--- {title} ---")
    print(tabulate([headers, data], headers="firstrow", tablefmt="pretty"))
    return confirm_action(confirm_message, cancel_message)

def normalize_stock_symbol(symbol: str) -> str:
    """Normalize stock symbol to uppercase and append .NS if not present."""
    return symbol.upper() + ".NS" if not symbol.endswith(".NS") else symbol.upper()