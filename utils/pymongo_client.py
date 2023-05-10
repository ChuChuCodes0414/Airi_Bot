from pymongo import MongoClient
import os

def get_client():
    CONNECTION_STRING  = os.getenv('dbconnection')
    client = MongoClient(CONNECTION_STRING)
    return client

if __name__ == "__main__":   
   dbclient = get_client()