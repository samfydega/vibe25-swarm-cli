"""
A basic Python script demonstrating fundamental concepts
"""

def calculate_sum(a: int, b: int) -> int:
    """Calculate and return the sum of two numbers"""
    return a + b

def main():
    # Basic print statement
    print("Hello, World!")
    
    # Variables and arithmetic
    x = 10
    y = 5
    sum_result = calculate_sum(x, y)
    print(f"\nBasic arithmetic:")
    print(f"{x} + {y} = {sum_result}")
    
    # String manipulation
    name = "Python"
    print(f"\nString operations:")
    print(f"Original: {name}")
    print(f"Uppercase: {name.upper()}")
    print(f"Length: {len(name)} characters")
    
    # Basic list operations
    numbers = [1, 2, 3, 4, 5]
    print(f"\nList operations:")
    print(f"List: {numbers}")
    print(f"First element: {numbers[0]}")
    print(f"Last element: {numbers[-1]}")
    print(f"Sum of list: {sum(numbers)}")

if __name__ == "__main__":
    main()
