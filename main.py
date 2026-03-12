import sys
from core.database import DatabaseManager
from core.seeder_logic import NarrativeSeeder

def reset_database():
    
    # Clear all data from both databases
    db = DatabaseManager()
    
    # Clean MongoDB collections
    try:
        db.mongo_db.users.drop()
        db.mongo_db.tweets.drop()
        print("   -> MongoDB: Collections 'users' et 'tweets' supprimées.")
    except Exception as e:
        print(f"   -> Erreur Mongo: {e}")

    # Clean Neo4j graph database
    try:
        with db.get_neo4j_session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        print("   -> Neo4j: Tous les nœuds et relations supprimés.")
    except Exception as e:
        print(f"   -> Erreur Neo4j: {e}")

def print_stats():
    
    # Display database statistics
    db = DatabaseManager()
    
    # Count documents in each collection
    nb_users = db.mongo_db.users.count_documents({})
    nb_tweets = db.mongo_db.tweets.count_documents({})
    nb_incidents = db.mongo_db.tweets.count_documents({"is_incident": True})

def main():
    
    # Clean existing data
    reset_database()

    # Generate new test data
    try:
        seeder = NarrativeSeeder()
        seeder.run()
    except Exception as e:
        print(f"Erreur critique pendant le seeding : {e}")
        sys.exit(1)
    
    # Show final statistics    
    print_stats()

    # Close database connections
    DatabaseManager().close()

if __name__ == "__main__":
    main()