from flask import Flask
from flask_pymongo import PyMongo
from flask_login import LoginManager
from .config import Config
import certifi
import pymongo
from bson.objectid import ObjectId

app = Flask(__name__)
app.config.from_object(Config)

# Configura la connessione a MongoDB usando certifi
MONGO_URI = app.config['MONGO_URI']
client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
mongo = client.get_database()  # Sostituisci con il nome del tuo database

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

from .models import User
from . import routes

@login_manager.user_loader
def load_user(user_id):
    user_data = mongo['users'].find_one({'_id': ObjectId(user_id)})
    if user_data:
        return User(user_data)
    return None
