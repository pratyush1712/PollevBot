#!/usr/bin/env python3
"""
PollEv Bot - Main execution script
Works both locally (with .env file) and in GitHub Actions (with secrets)
"""

from pollevbot import PollBot
import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the PollEv bot."""
    logger.info("Starting PollEv Bot")
    logger.info(f"Current time: {datetime.now()}")
    
    # Try to load .env file (for local development)
    try:
        import dotenv
        dotenv.load_dotenv()
        logger.info("Loaded environment from .env file")
    except ImportError:
        logger.info("python-dotenv not available, using environment variables directly")
    except Exception as e:
        logger.warning(f"Could not load .env file: {e}")

    # Get environment variables
    user = os.getenv('EMAIL')
    password = os.getenv('PASSWORD')
    host = os.getenv('HOST')
    
    # Validate required environment variables
    if not user:
        logger.error("EMAIL environment variable not set")
        return 1
    if not password:
        logger.error("PASSWORD environment variable not set")
        return 1
    if not host:
        logger.error("HOST environment variable not set")
        return 1
    
    logger.info(f"Bot configuration:")
    logger.info(f"  Email: {user}")
    logger.info(f"  Host: {host}")
    logger.info(f"  Login type: pollev")
    logger.info(f"  Lifetime: 4800 seconds (80 minutes)")
    
    try:
        with PollBot(user, password, host, login_type='pollev', lifetime=4800) as bot:
            logger.info("Bot initialized successfully")
            logger.info("Starting bot execution...")
            bot.run()
            logger.info("Bot execution completed normally")
            
    except KeyboardInterrupt:
        logger.info("Bot execution interrupted by user")
        return 0
    except Exception as e:
        logger.error(f"Bot execution failed with error: {e}")
        logger.exception("Full traceback:")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    logger.info(f"Bot script exiting with code: {exit_code}")
    sys.exit(exit_code)