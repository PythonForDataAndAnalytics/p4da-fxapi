# Support for usage tracking, logging usage, and limiting usage

import csv
import os
from datetime import datetime
from FileSet import FileSet
from flask import request

# Initialize empty dictionary and list for usage tracking
usage_data = {}      # data tracked for a single user
usage_activity = []  # the list of usage across all users

# Load the whitelist and blacklist
whitelist = FileSet(os.path.join('lists', 'whitelist.txt'))
print('whitelist:', whitelist)
blacklist = FileSet(os.path.join('lists', 'blacklist.txt'))
print('blacklist:', blacklist)

USAGE_TRACKING = True                                      # Set to True to track/limit usage
REQUEST_LIMIT = 100                                        # Max requests per user per day
USAGE_FILE = os.path.join('logs','usage.csv')              # File to save daily usage activity
USAGE_FILE_TODAY = os.path.join('logs', 'usage_today.csv') # File for manually saving today's activity
IS_SAVING_ACTIVITY = True                                  # Toggle to enable or disable saving daily activity

# This function tries to extract a unique the client's IP address
def get_user_id():
    #print('*** entering get_user_id')
    #print(request)
    #print('*** after print(request)')
    # aim for the header's X-Forwarded-For, otherwise use the remote_addr 
    addr = request.headers.get('X-Forwarded-For', request.remote_addr)
    return addr

# Save the usage activity to a specified CSV file with given write mode
def save_daily_activity(filename, mode):
    if IS_SAVING_ACTIVITY and usage_activity:
        with open(filename, mode, newline='') as file:
            writer = csv.writer(file)
            # Write header if file is empty
            if file.tell() == 0:
                writer.writerow(['timestamp', 'user_id', 'url'])
            # Write each activity log
            for record in usage_activity:
                writer.writerow([record['timestamp'], record['user_id'], record['url']])

# Reset usage tracking and save activity at the beginning of each day
def reset_daily_limits():
    global usage_data, usage_activity
    today = datetime.now().date()
    
    # Check if we need to reset (i.e., it's a new day)
    if usage_data and any(data['date'] != today for data in usage_data.values()):
        # Save the current day's activity to the default file
        save_daily_activity(USAGE_FILE, 'a')
        
        # Reset data for the new day
        usage_data = {}  # Reset usage tracking data
        usage_activity = []  # Clear the usage activity log

# Increment the request count for the current user and log the activity
def increment_request_count():
    if not USAGE_TRACKING:
        return True
    reset_daily_limits()
    user_id = get_user_id()
    user_data = usage_data.setdefault(user_id, {'date': datetime.now().date(), 'count': 0})
    
    # Check if the user has exceeded the request limit
    if (user_id not in whitelist) and (user_data['count'] >= REQUEST_LIMIT):
        return False  # Limit exceeded

    # block blacklisted
    if user_id in blacklist:
        return False

    # Increment the user's request count
    user_data['count'] += 1

    # Log the activity
    usage_activity.append({
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'url': request.path
    })
    
    return True  # Request allowed

# Manually write the current usage_activity to USAGE_FILE_TODAY without clearing it
def write_usage_activity_today():
    save_daily_activity(USAGE_FILE_TODAY, 'w')
