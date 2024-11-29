import argparse
import json
import os
from datetime import datetime, timezone  # Correct timezone import
import pytz
from github import Github
from collections import Counter
from tabulate import tabulate  # For pretty table display

# Constants for default paths and values
HOME_DIR = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME_DIR, ".nhn", "notethisurl")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
DEFAULT_FILENAME = "bookmarks.json"
DEFAULT_TIMEZONE = "UTC"

# Function to initialize the configuration (set up if missing or prompt to override)
def initialize_config(force_setup=False):
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)
        print(f"Created directory: {CONFIG_DIR}")

    # If config.json does not exist or force_setup is True, set up the config
    if not os.path.exists(CONFIG_FILE) or force_setup:
        print("No config file found. Let's set up the configuration.")
        # Prompt user for required info
        github_token = input("Enter your GitHub Personal Access Token: ")
        github_repo = input("Enter the GitHub repository (e.g., username/repo_name): ")
        timezone_choice = input(f"Enter your preferred timezone (default: {DEFAULT_TIMEZONE}): ") or DEFAULT_TIMEZONE
        filename_choice = input(f"Enter the filename to save bookmarks (default: {DEFAULT_FILENAME}): ") or DEFAULT_FILENAME
        
        # Save the configuration to config.json
        config = {
            "GITHUB_TOKEN": github_token,
            "GITHUB_REPO": github_repo,
            "FILENAME": filename_choice,
            "TIMEZONE": timezone_choice
        }
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)
        print(f"Config file created at: {CONFIG_FILE}")
        return True  # Indicate that the config was created
    else:
        # If config.json exists, check for required keys
        with open(CONFIG_FILE, "r") as file:
            config = json.load(file)
        
        # Check if all required keys are present in the config
        required_keys = ["GITHUB_TOKEN", "GITHUB_REPO", "TIMEZONE"]
        if all(key in config for key in required_keys):
            return False  # Configuration exists and is valid, no need to overwrite
        else:
            print("Config file is missing some required keys.")
            overwrite = input("Do you want to overwrite the existing configuration? (yes/no): ").strip().lower()
            if overwrite != "yes":
                print("Keeping the existing configuration.")
                return False  # Don't overwrite, exit here

        # If keys are missing, prompt to reconfigure
        print("Let's reconfigure the setup.")
        # Prompt user for new values (override existing values)
        github_token = input(f"Enter your GitHub Personal Access Token (current: {config.get('GITHUB_TOKEN', 'Not set')}): ")
        github_repo = input(f"Enter the GitHub repository (current: {config.get('GITHUB_REPO', 'Not set')}): ")
        timezone_choice = input(f"Enter your preferred timezone (current: {config.get('TIMEZONE', DEFAULT_TIMEZONE)}): ") or config.get('TIMEZONE', DEFAULT_TIMEZONE)
        filename_choice = input(f"Enter the filename to save bookmarks (current: {config.get('FILENAME', DEFAULT_FILENAME)}): ") or config.get('FILENAME', DEFAULT_FILENAME)
        
        # Save the updated configuration to config.json
        config.update({
            "GITHUB_TOKEN": github_token,
            "GITHUB_REPO": github_repo,
            "TIMEZONE": timezone_choice,
            "FILENAME": filename_choice
        })
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)
        print(f"Config file updated at: {CONFIG_FILE}")
        return True  # Indicate that the config was updated

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
        try:
            with open(file_path, "r") as file:
                return json.load(file)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {file_path}. Initializing with an empty list.")
            return []  # Return an empty list if JSON is invalid
    else:
        print(f"{file_path} not found. Initializing with an empty list.")
        return []  # Return an empty list if the file doesn't exist

# Function to save bookmarks
def save_bookmarks(file_path, bookmarks):
    with open(file_path, "w") as file:
        json.dump(bookmarks, file, indent=4)

# Function to add a new bookmark
def add_bookmark(bookmark_url, tags):
    bookmark = {
        "bookmarkURL": bookmark_url,
        "tags": tags,
        "date": datetime.now(timezone.utc).isoformat()
    }
    return bookmark

# Function to push changes to GitHub
def push_to_github(config, file_path):
    g = Github(config["GITHUB_TOKEN"])  # Authenticate using the GitHub token
    repo = g.get_repo(config["GITHUB_REPO"])  # Get the specified repository
    
    with open(file_path, "r") as file:
        content = file.read()  # Read the contents of the local bookmarks file
    
    try:
        # Try to fetch the existing file from the repository
        contents = repo.get_contents(config["FILENAME"])
        # If file exists, update it
        repo.update_file(contents.path, "Update bookmarks", content, contents.sha)
        print(f"Updated file {config['FILENAME']} in the GitHub repo.")
    except Exception as e:
        # If file doesn't exist, create it
        if "404" in str(e):
            print(f"File {config['FILENAME']} not found, creating a new file.")
            repo.create_file(config["FILENAME"], "Add bookmarks", content)
            print(f"Created file {config['FILENAME']} in the GitHub repo.")
        else:
            print(f"GitHub error occurred: {e}")

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
        tz = pytz.timezone(tz_name)  # Load user-configured timezone
    except pytz.UnknownTimeZoneError:
        print(f"Error: Invalid timezone '{tz_name}'. Falling back to UTC.")
        tz = pytz.utc  # Use UTC as fallback

    table = []
    for bookmark in bookmarks:
        # Convert UTC time to the user-configured timezone
        utc_time = datetime.fromisoformat(bookmark["date"])
        local_time = utc_time.replace(tzinfo=pytz.utc).astimezone(tz)
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
    subparsers.add_parser("urls", help="List saved URLs in a table")

    # Sub-parser for "setup" command
    setup_parser = subparsers.add_parser("setup", help="Set up or reconfigure the GitHub token and repo")

    args = parser.parse_args()

    if args.command == "setup":
        # Handle the setup command separately
        if initialize_config(force_setup=True):
            print("Setup complete. You can now use other commands like 'add', 'tags', or 'urls'.")
            return  # Exit after setup completes

    # Initialize and load configuration (if setup or config file is missing)
    if initialize_config(force_setup=False):  # Ensure config is valid
        print("Configuration already exists and is valid.")
    
    config = load_config()
    file_path = get_bookmarks_file_path(config)
    bookmarks = load_bookmarks(file_path)

    if args.command == "add":
        # Add a new bookmark
        bookmark = add_bookmark(args.url, args.tags)
        bookmarks.append(bookmark)
        save_bookmarks(file_path, bookmarks)
        push_to_github(config, file_path)
        print("Bookmark added and pushed to GitHub.")

    elif args.command == "tags":
        # List tags by frequency
        list_tags(bookmarks)

    elif args.command == "urls":
        # List URLs in a table format
        list_urls(bookmarks, config["TIMEZONE"])

if __name__ == "__main__":
    main()
