
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

print("Attempting to import main module...")
try:
    import main
    print("Successfully imported main.")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"An error occurred: {e}")
