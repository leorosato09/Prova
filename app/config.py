import os

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'Nibefile04ProgettoDB')
    MONGO_URI = "mongodb+srv://leorosato09:Nibefile04@progettodb.vrk4x.mongodb.net/ProgettoDB?retryWrites=true&w=majority&tls=true"
