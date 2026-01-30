"""Quick test of routing"""
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.model_gateway import get_model_gateway, Route

print("Initializing gateway...")
gateway = get_model_gateway()

tests = [
    "hello",
    "severe bleeding", 
    "what is folic acid"
]

print("\nTesting routing decisions:\n")
for query in tests:
    route = gateway.decide_route(query)
    print(f"{query:30} -> {route.value}")

print("\nDone!")
