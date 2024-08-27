import os
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from slack_bolt.async_app import AsyncApp

load_dotenv()

ALLOWED_CHANNEL_ID = os.getenv("ALLOWED_CHANNEL_ID")
SLACK_USER_TOKEN = os.getenv("SLACK_USER_TOKEN")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")

ES_HOST = os.getenv("ES_HOST")
ES_PORT = int(os.getenv("ES_PORT"))
ES_INDEX = os.getenv("ES_INDEX")
ES_USER = os.getenv("ES_USER")
ES_PASS = os.getenv("ES_PASS")

es = AsyncElasticsearch(
    hosts=[
        {
            "host": ES_HOST,
            "port": ES_PORT,
            "scheme": "https",
        }
    ],
    basic_auth=(ES_USER, ES_PASS),
    verify_certs=False,
    ssl_show_warn=False,
)

app = AsyncApp(token=SLACK_USER_TOKEN)
appBot = AsyncApp(token=SLACK_BOT_TOKEN)