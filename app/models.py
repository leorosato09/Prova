from flask_login import UserMixin
from bson.objectid import ObjectId
from . import mongo

# Definizione delle collezioni
users_collection = mongo.db['users']
bottiglie_collection = mongo.db['bottiglie']

class User(UserMixin):
    def __init__(self, user_data):
        self.id = str(user_data['_id'])
        self.username = user_data['username']
        self.password = user_data['password']

    @staticmethod
    def find_by_username(username):
        user_data = users_collection.find_one({'username': username}, {'_id': 1, 'username': 1, 'password': 1})
        if user_data:
            return User(user_data)
        return None

    def get_id(self):
        return self.id
