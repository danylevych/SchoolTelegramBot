import scripts.tools.config as config
from pymongo import MongoClient

cluster = MongoClient(config.MONGO_TOKEN)
db = cluster["telegram"]
users = db["users"]
notes = db["notes"]
students = db["students"]
teachers = db["teachers"]
homeworks = db["homeworks"]
