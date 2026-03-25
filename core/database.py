import os
from pymongo import MongoClient
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)

            mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
            cls._instance.mongo_client = MongoClient(mongo_uri)
            cls._instance.mongo_db = cls._instance.mongo_client["milano2026"]

            neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
            neo4j_user = os.getenv("NEO4J_USER", "")
            neo4j_password = os.getenv("NEO4J_PASSWORD", "")

            if neo4j_user and neo4j_password:
                cls._instance.neo4j_driver = GraphDatabase.driver(
                    neo4j_uri,
                    auth=(neo4j_user, neo4j_password)
                )
            else:
                cls._instance.neo4j_driver = GraphDatabase.driver(neo4j_uri)

        return cls._instance

    def get_mongo_db(self):
        return self.mongo_db

    def get_neo4j_session(self):
        return self.neo4j_driver.session()

    def close(self):
        self.mongo_client.close()
        self.neo4j_driver.close()