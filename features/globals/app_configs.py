from pydantic_settings import BaseSettings
from dotenv import find_dotenv, load_dotenv


load_dotenv(find_dotenv(".env"))


class AppConfigs(BaseSettings):
    # App configs
    app_name: str = "Patrick App"
    app_version: str = "1.0.0"
    # Pocketbase configs
    pb_url: str  # the pocketbase url
    auth_collection: str  # the collection to authenticate with, ex: 'users'
