import subprocess
import os
import threading
from features.globals.app_state import AppState
from Api.LocalDB import API as LocalAPI
import time
local_url = "http://127.0.0.1:8090"


# Define the path to the PocketBase binary
POCKETBASE_PATH = r"pocketbase\pocketbase.exe"  # Adjust this path to the location of your PocketBase binary
local_auth = LocalAPI(local_url)

# Define the data directory (optional)
DATA_DIR = "./pocketbase/pb_data"

# Launch PocketBase
def launch_pocketbase():
    if not os.path.exists(POCKETBASE_PATH):
        raise FileNotFoundError(f"PocketBase binary not found at {POCKETBASE_PATH}")
    
    try:
        process = subprocess.Popen(
            [POCKETBASE_PATH, "serve", "--dir", DATA_DIR],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        AppState.local_db = True
        
        # Optional: Read output and errors from the process
        time.sleep(5)
    
        local_user = 'dev@mail.com'
        local_password = '1223334444'
        userdata=local_auth.login_as_admin(local_user,local_password)
        if userdata is None:
            return False
        print("PocketBase is running...")


    except Exception as e:
        print(f"Failed to launch PocketBase: {e}")
       

# Create a thread to launch PocketBase
def start_pocketbase():
    threading.Thread(target=launch_pocketbase(),daemon=True).start()