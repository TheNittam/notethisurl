import argparse
import json
import os
from datetime import datetime
from pytz import timezone, utc
from collections import Counter
from github import Github
from tabulate import tabulate  # For pretty table display

# Constants for default paths and values
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".nhn", "notethisurl")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_FILENAME = "bookmarks.json"
DEFAULT_TIMEZONE = "UTC"

# Function to initialize the configuration
def initialize_config():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
        print(f"Created directory: {CONFIG_DIR}")
    
    if not os.path.exists(CONFIG_FILE):
        # Create default configuration
        config = {
            "GITHUB_TOKEN": "your_github_personal_access_token",  # Replace later
            "GITHUB_REPO": "username/repo_name",  # Replace later
            "FILENAME": DEFAULT_FILENAME,
            "TIMEZONE": DEFAULT_TIMEZONE
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)
        print(f"Created default config file at: {CONFIG_FILE}")
    else:
        print(f"Config file already exists at: {CONFIG_FILE}")

# Function to load the configuration
def load_config():
    with open(CONFIG_FILE, "r") as file:
        return json.load(file)

# Function to get the full path for the bookmarks file
def get_bookmarks_file_path(config):
    return os.path.join(CONFIG_DIR, config.get("FILENAME", DEFAULT_FILENAME))

# Function to load existing bookmarks
def load_bookmarks(file_path):
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return []

# Function to save bookmarks
def save_bookmarks(file_path, bookmarks):
    with open(file_path, "w") as file:
        json.dump(bookmarks, file, indent=4)

# Function to add a new bookmark
def add_bookmark(bookmark_url, tags):
    bookmark = {
        "bookmarkURL": bookmark_url,
        "tags": tags,
        "date": datetime.utcnow().isoformat()
    }
    return bookmark

# Function to push changes to GitHub
def push_to_github(config, file_path):
    g = Github(config["GITHUB_TOKEN"])
    repo = g.get_repo(config["GITHUB_REPO"])
    with open(file_path, "r") as file:
        content = file.read()
    try:
        # Check if file exists in the repo
        contents = repo.get_contents(config["FILENAME"])
        repo.update_file(contents.path, "Update bookmarks", content, contents.sha)
    except:
        # Create file if it doesn't exist
        repo.create_file(config["FILENAME"], "Add bookmarks", content)

# Function to list tags sorted by frequency
def list_tags(bookmarks):
    tags_counter = Counter(tag for bookmark in bookmarks for tag in bookmark["tags"].split(",") if tag)
    sorted_tags = tags_counter.most_common()
    print("Tags sorted by count:")
    for tag, count in sorted_tags:
        print(f"{tag}: {count}")

# Function to list URLs in a table
def list_urls(bookmarks, tz_name):
    try:
        tz = timezone(tz_name)  # Load user-configured timezone
    except Exception as e:
        print(f"Error: Invalid timezone '{tz_name}'. Falling back to UTC.")
        tz = utc

    table = []
    for bookmark in bookmarks:
        # Convert UTC time to user-configured timezone
        utc_time = datetime.fromisoformat(bookmark["date"])
        local_time = utc_time.replace(tzinfo=utc).astimezone(tz)
        table.append([
            local_time.strftime("%Y-%m-%d %H:%M:%S"),
            bookmark["bookmarkURL"],
            bookmark["tags"]
        ])
    print(tabulate(table, headers=["DateTime", "URL", "Tags"], tablefmt="grid"))

# Main function
def main():
    parser = argparse.ArgumentParser(description="Manage bookmarks saved to a GitHub-hosted JSON file.")
    subparsers = parser.add_subparsers(dest="command", required=True, help="Sub-command to run")

    # Sub-parser for "add" command
    add_parser = subparsers.add_parser("add", help="Add a new bookmark")
    add_parser.add_argument("url", help="URL to save")
    add_parser.add_argument("--tags", default="", help="Comma-separated tags for the URL")

    # Sub-parser for "tags" command
    subparsers.add_parser("tags", help="List tags sorted by frequency")

    # Sub-parser for "urls" command
    subparsers.add_parser("urls", help="List URLs in a table")

    args = parser.parse_args()

    # Initialize and load configuration
    initialize_config()
    config = load_config()
    file_path = get_bookmarks_file_path(config)
    timezone_name = config.get("TIMEZONE", DEFAULT_TIMEZONE)

    # Load bookmarks
    bookmarks = load_bookmarks(file_path)

    if args.command == "add":
        # Add a new bookmark
        new_bookmark = add_bookmark(args.url, args.tags)
        bookmarks.append(new_bookmark)
        save_bookmarks(file_path, bookmarks)
        push_to_github(config, file_path)
        print(f"Bookmark added: {args.url}")
    elif args.command == "tags":
        # List tags
        list_tags(bookmarks)
    elif args.command == "urls":
        # List URLs
        list_urls(bookmarks, timezone_name)
    else:
        print("Error: Invalid command.")

if __name__ == "__main__":
    main()
