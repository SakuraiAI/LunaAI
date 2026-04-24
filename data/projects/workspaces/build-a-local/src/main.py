from __future__ import annotations


def add(left: float, right: float) -> float:
    return left + right


def subtract(left: float, right: float) -> float:
    return left - right


def multiply(left: float, right: float) -> float:
    return left * right


def divide(left: float, right: float) -> float:
    if right == 0:
        raise ValueError("Division by zero is not allowed.")
    return left / right


OPERATIONS = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
}


def read_number(label: str) -> float:
    while True:
        raw_value = input(f"{label}: ").strip().replace(",", ".")
        try:
            return float(raw_value)
        except ValueError:
            print("Please enter a valid number.")


def read_operation() -> str:
    while True:
        operation = input("Operation (+, -, *, /): ").strip()
        if operation in OPERATIONS:
            return operation
        print("Choose one of: +, -, *, /")


def run_calculator() -> None:
    print("LunaAI Calculator")
    print("Type Ctrl+C to exit.\n")

    while True:
        left = read_number("First number")
        operation = read_operation()
        right = read_number("Second number")

        try:
            result = OPERATIONS[operation](left, right)
        except ValueError as error:
            print(f"Error: {error}\n")
            continue

        print(f"Result: {left:g} {operation} {right:g} = {result:g}\n")


if __name__ == "__main__":
    run_calculator()
