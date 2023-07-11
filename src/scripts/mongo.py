import sys
sys.path.append("src/scripts/tools")
import config
from pymongo import MongoClient

cluster = MongoClient(config.MONGO_TOKEN)
db = cluster["telegram"]
users = db["users"]
