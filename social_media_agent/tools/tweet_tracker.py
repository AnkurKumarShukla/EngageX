import csv
import os
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

# Define the input schema using Pydantic

    

# Define the function for logging tweets
def log_tweet(tweet_id: str = Field(..., description="The ID of the tweet to be logged.")) -> str:
    """
    Logs a tweet ID along with the current datetime in a CSV file.
    
    If the folder or file does not exist, they will be created automatically.
    """
    folder = "tweet_data"
    filename = "tweet_history.csv"
    

    # Ensure the folder exists
    os.makedirs(folder, exist_ok=True)

    # Full file path
    file_path = os.path.join(folder, filename)

    # Check if the file exists to determine if headers are needed
    file_exists = os.path.isfile(file_path)

    # Open the CSV file in append mode
    with open(file_path, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        
        # Write header if file is newly created
        if not file_exists:
            writer.writerow(["tweet_id", "datetime"])
        
        # Write tweet data
        writer.writerow([tweet_id, datetime.now().isoformat()])

    return f"Logged tweet {tweet_id} added for tracking and analysing . . . "

# Define the tool using StructuredTool with args_schema
log_tweet_tool = StructuredTool.from_function(
    func=log_tweet,
    name="LogTweetTool",
    description="Logs a tweet ID with a timestamp into a CSV file for tracking."   
)

# test the tool
# print(log_tweet("1234567890"))
