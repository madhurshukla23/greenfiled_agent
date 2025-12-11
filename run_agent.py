"""
Main entry point for Azure Landing Zone Discovery Agent
"""
import sys
import os

# Add parent directory to path for module imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from src.discovery_workshop import main

if __name__ == "__main__":
    asyncio.run(main())
