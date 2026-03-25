from core.database import DatabaseManager


class MilanoRepository:
    def __init__(self):
        self.db = DatabaseManager()
        self.mongo = self.db.get_mongo_db()

    def create_user(self, user_data):
        self.mongo.users.insert_one(user_data)
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MERGE (u:User {user_id: $uid})
                SET u.username = $uname
                """,
                uid=user_data["user_id"],
                uname=user_data["username"],
            )

    def update_user(self, user_id, update_data):
        self.mongo.users.update_one({"user_id": user_id}, {"$set": update_data})
        with self.db.get_neo4j_session() as session:
            params = {"uid": user_id}
            sets = []

            if "username" in update_data:
                sets.append("u.username = $uname")
                params["uname"] = update_data["username"]

            if sets:
                session.run(
                    f"""
                    MATCH (u:User {{user_id: $uid}})
                    SET {", ".join(sets)}
                    """,
                    **params,
                )

    def delete_user(self, user_id):
        self.mongo.users.delete_one({"user_id": user_id})
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MATCH (u:User {user_id: $uid})
                DETACH DELETE u
                """,
                uid=user_id,
            )

    def create_tweet(self, tweet_data):
        self.mongo.tweets.insert_one(tweet_data)
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MERGE (t:Tweet {tweet_id: $tid})
                SET t.user_id = $uid
                """,
                tid=tweet_data["tweet_id"],
                uid=tweet_data["user_id"],
            )
            session.run(
                """
                MATCH (u:User {user_id: $uid}), (t:Tweet {tweet_id: $tid})
                MERGE (u)-[:AUTHORED]->(t)
                """,
                uid=tweet_data["user_id"],
                tid=tweet_data["tweet_id"],
            )

            if tweet_data.get("in_reply_to_tweet_id"):
                session.run(
                    """
                    MATCH (t1:Tweet {tweet_id: $tid}), (t2:Tweet {tweet_id: $rid})
                    MERGE (t1)-[:REPLY_TO]->(t2)
                    """,
                    tid=tweet_data["tweet_id"],
                    rid=tweet_data["in_reply_to_tweet_id"],
                )

    def update_tweet(self, tweet_id, update_data):
        self.mongo.tweets.update_one({"tweet_id": tweet_id}, {"$set": update_data})

    def delete_tweet(self, tweet_id):
        self.mongo.tweets.delete_one({"tweet_id": tweet_id})
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MATCH (t:Tweet {tweet_id: $tid})
                DETACH DELETE t
                """,
                tid=tweet_id,
            )

    def add_follow(self, follower_id, target_id):
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MATCH (a:User {user_id: $aid}), (b:User {user_id: $bid})
                MERGE (a)-[:FOLLOWS]->(b)
                """,
                aid=follower_id,
                bid=target_id,
            )

    def add_retweet(self, user_id, tweet_id):
        with self.db.get_neo4j_session() as session:
            session.run(
                """
                MATCH (u:User {user_id: $uid}), (t:Tweet {tweet_id: $tid})
                MERGE (u)-[:RETWEETS]->(t)
                """,
                uid=user_id,
                tid=tweet_id,
            )

    def get_incident_tweets(self):
        return list(
            self.mongo.tweets.find({"is_incident": True}).sort("created_at", -1)
        )