#!/bin/bash

# Activate the virtual environment
source .venv/bin/activate
pip install -r requirements.txt

# Run the bot
python3 bot.py

# Keep the terminal open if the bot crashes or stops
read -p "Press [Enter] to exit..."