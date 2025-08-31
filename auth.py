# auth.py
from flask_httpauth import HTTPBasicAuth
from config import USERS

auth = HTTPBasicAuth()

@auth.verify_password
def verify(username, password):
    return USERS.get(username) == password
