
from Views.globals.app_logger import app_logger
from Views.globals.app_configs import AppConfigs
from Views.globals.app_router import AppRouter
from helpers.store import store
from helpers.actions_creators import add_user, add_mt5, GetUser
from Api.APIHandler import API
# from Views.globals.app_state import store

from Bots.account import Account

from Orders.orders_manager import orders_manager
from cycles.cycles_manager import cycles_manager
from helpers.store import store

import multiprocessing
from multiprocessing import Queue

# Create a Manager object

# Create an MetaTrader of the MetaTraderExpert class
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

    try:

        # On successful login, set the token in the AppState
        # ******* Do other stuff Here ********
        app_configs = AppConfigs()
        auth = API(app_configs.pb_url)
        user_data = auth.login(username, password)
        if user_data is None:
            return (False, "Login failed")
        store.dispatch(add_user(user_data, auth, username, password))

        # return success status and messge
        return (True, "Login successful")

    except Exception as e:
        # Show snackbar with the error message
        AppRouter.snackbar("Login failed, Worng Credentials!")
        # log the error
        app_logger.error(f"Login failed: {e}")
        return (False, "Login failed")


# launch the metatrader
def launch_metatrader(data, authorized):
    from MetaTrader.MT5 import MetaTrader
    username = data.get('username')
    password = data.get('password')
    server = data.get('server')
    program_path = data.get('program_path')
    server_username = data.get('server_username')
    server_password = data.get('server_password')
    try:
        # ******* Do other stuff Here ********
        expert = MetaTrader(username, password, server)
        logged = expert.initialize(program_path)
        acc = expert.get_account_info()
        # shared['mt5'] = expert
        app_configs = AppConfigs()
        auth = API(app_configs.pb_url)
        auth.login(server_username, server_password)

        user_account = Account(auth, expert)
        user_account.on_init()
        user_account.run_in_thread()
        OrdersManager = orders_manager(expert)
        cyclesManager = cycles_manager(expert, auth, user_account)
        OrdersManager.run_in_thread()
        cyclesManager.run_in_thread()
        print(acc)
        authorized.put(True)
    except Exception as e:
        # Show snackbar with the error message
        # log the error
        app_logger.error(f"Metatrader launch failed: {e}")
        return False


def launch_metatrader_in_process(data):
    # ns=multiprocessing.Manager().Namespace()
    authorized = Queue()
    p = multiprocessing.Process(
        target=launch_metatrader, args=(data, authorized))
    p.daemon = True
    p.start()
    return p.is_alive

    # store.dispatch(add_mt5(user, account, expert))
    # user_data = GetUser(user)
    # auth = user_data.get('auth_api')


def set_app_token(token: str):
    """Set the token in the AppState

    Args:
        token (str): the token to be set in the AppState
    """

    app_logger.info("Token set in the AppState")


def set_login_data(data: dict[str, str]):
    """Set the login data in the AppState

    Args:
        data (dict[str, str]): the login data to be set in the AppState
    """
    # store.login_data = data
    app_logger.info("Login data set in the AppState")
