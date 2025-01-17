from MetaTrader.MT5 import MetaTrader
from features.globals.app_logger import app_logger
from features.globals.app_configs import AppConfigs
from features.globals.app_router import AppRouter

from features.globals.app_state import store
from MetaTrader.MT5 import MetaTrader
from Api.APIHandler import API
from Bots.account import Account

from Orders.orders_manager import orders_manager 
from cycles.cycles_manager import cycles_manager
from pb import local_auth
# Create an MetaTrader of the MetaTraderExpert class
expert = MetaTrader( 135651648, "uPBGz2Mfvv5PnR!", "Exness-MT5Trial")
# Check if the connection was successful
# Initialize the API handler

# Start PocketBase  

# start_pocketbase(local_auth,local_user,local_password)
# Wait until PocketBase is fully launched
    # Adjust the sleep time as needed
# Authenticate with the API
# get accounts


async def login(
    username: str, password: str
) -> tuple[bool, str]:
    """login function, to authenticate the user and set the token in the [AppState.token]

    Returns:
        tuple[bool, str]: return a tuple with the login status as (True in case of successful login ) and (False in case any error)
        and a message, in case of success and failure.
    """
    app_configs = AppConfigs()
    try:
       
        # On successful login, set the token in the AppState
        # ******* Do other stuff Here ********
        auth = API(app_configs.pb_url)
        user_data = auth.login(username, password)
        user_account= Account(auth,expert,local_auth)
        user_account.on_init()
        user_account.run_in_thread()
        OrdersManager= orders_manager(local_auth,expert)
        cyclesManager = cycles_manager(local_auth,expert,auth)
        OrdersManager.run_in_thread()
        cyclesManager.run_in_thread()
        set_app_token(user_data.token)
        # return success status and messge
        return (True, "Login successful")

    except Exception as e:
        # Show snackbar with the error message
        AppRouter.snackbar("Login failed, Worng Credentials!")
        # log the error
        app_logger.error(f"Login failed: {e}")
        return (False, "Login failed")
  

# launch the metatrader
async def launch_metatrader(username: str, password: str, server: str, program_path: str , type: str
) -> tuple[bool, str]:
    """launch_metatrader function, to launch the metatrader

    Returns:
        tuple[bool, str]: return a tuple with the launch status as (True in case of successful launch ) and (False in case any error)
        and a message, in case of success and failure.
    """
    try:
        # ******* Do other stuff Here ********
        expert = MetaTrader( username, password , server)
        logged=expert.initialize(program_path)
        acc=expert.get_account_info()
        print(acc)
        return logged   
    except Exception as e:
        # Show snackbar with the error message
        AppRouter.snackbar("Metatrader launch failed!")
        # log the error
        app_logger.error(f"Metatrader launch failed: {e}")
        return False

def set_app_token(token: str):
    """Set the token in the AppState

    Args:
        token (str): the token to be set in the AppState
    """
    store.token = token
    app_logger.info("Token set in the AppState")
def set_login_data(data: dict[str, str]):
    """Set the login data in the AppState

    Args:
        data (dict[str, str]): the login data to be set in the AppState
    """
    store.login_data = data
    app_logger.info("Login data set in the AppState")