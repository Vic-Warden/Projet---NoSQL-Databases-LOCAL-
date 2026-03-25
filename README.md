# Milano 2026 — Incident Tracker

Real-time tweet analysis platform built for the Milano 2026 Olympics. Combines MongoDB for document storage and Neo4j for graph-based relationship mapping, served through a Streamlit dashboard.

---

## Tech Stack

- **Python 3.10** — Core logic & Streamlit UI
- **MongoDB** — Tweet & user document storage
- **Neo4j** — Social graph (followers, retweets, threads)
- **Docker** — Containerized services
- **Kubernetes / Minikube** — Orchestration & deployment
- **TextBlob** — Sentiment analysis & incident detection

---

## Deployment (Kubernetes)

Requires: `minikube`, `kubectl`, `docker`

```bash

# Start Minikube
minikube start

# Deploy all services
kubectl apply -f k8s/

# Open the app in browser
minikube service milano-app-service
```

The app deployment uses an **Init Container** that runs `main.py` to seed the databases before starting Streamlit. No manual seeding required.

---

## Alternative Launch (Local Docker)

Requires: `docker`, `python 3.10+`

```bash

# Full setup: starts DBs, installs deps, seeds data, launches app
python manage.py run
```

Available commands:

| Command | Description |
|---------|-------------|
| `python manage.py db` | Start MongoDB & Neo4j containers |
| `python manage.py install` | Install Python dependencies |
| `python manage.py seed` | Run data seeder |
| `python manage.py app` | Launch Streamlit |
| `python manage.py stop` | Stop database containers |
| `python manage.py run` | Run everything in sequence |

---

## Database Models

### MongoDB — Document Store

**Users**
```json
{
  "user_id": "u_0",
  "username": "john_doe",
  "role": "fan",
  "country": "France",
  "created_at": "2026-03-12T10:00:00"
}
```

**Tweets**
```json
{
  "tweet_id": "uuid",
  "user_id": "u_0",
  "text": "Metro M1 is blocked!",
  "hashtags": ["metroM1", "disaster"],
  "sentiment_score": -0.9,
  "is_incident": true,
  "favorite_count": 120,
  "in_reply_to_tweet_id": null,
  "created_at": "2026-03-12T11:30:00"
}
```

### Neo4j — Graph Store

| Relationship | Description |
|--------------|-------------|
| `(User)-[:FOLLOWS]->(User)` | Follower network |
| `(User)-[:AUTHORED]->(Tweet)` | Tweet authorship |
| `(Tweet)-[:REPLY_TO]->(Tweet)` | Discussion threads |
| `(User)-[:RETWEETS]->(Tweet)` | Retweet tracking |

---

## Project Structure

```
├── app.py              # Streamlit dashboard
├── main.py             # Database reset & seeding
├── manage.py           # CLI for local Docker setup
├── requirements.txt
├── Dockerfile
├── core/
│   ├── database.py     # MongoDB & Neo4j connections (singleton)
│   ├── models.py       # Data models
│   ├── repositories.py # CRUD operations for both databases
│   ├── services.py     # Sentiment analysis & incident detection
│   └── seeder_logic.py # Test data generation
└── k8s/
    ├── app.yaml        # Streamlit deployment + service
    ├── mongo.yaml      # MongoDB deployment + service
    └── neo4j.yaml      # Neo4j deployment + service
```
