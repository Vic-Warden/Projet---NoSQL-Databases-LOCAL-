import os
import tempfile

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from pyvis.network import Network

from core.database import DatabaseManager
from core.repositories import MilanoRepository


st.set_page_config(
    page_title="Milano 2026 — Ops Center",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.block-container {
    padding-top: 1.2rem;
    padding-bottom: 1rem;
}
.section-title {
    font-size: 1rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8b949e;
    border-bottom: 2px solid #30363d;
    padding-bottom: 8px;
    margin-bottom: 14px;
    margin-top: 8px;
}
.kpi-card {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 18px 20px;
    text-align: center;
}
.kpi-value {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: 4px;
}
.kpi-label {
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #8b949e;
}
.kpi-blue .kpi-value { color: #58a6ff; }
.kpi-green .kpi-value { color: #3fb950; }
.kpi-purple .kpi-value { color: #bc8cff; }
.kpi-orange .kpi-value { color: #d29922; }
.kpi-red .kpi-value { color: #f85149; }
.kpi-teal .kpi-value { color: #39d2c0; }
.badge {
    padding: 4px 10px;
    border-radius: 6px;
    font-size: 0.8rem;
    font-weight: 700;
    display: inline-block;
    margin-bottom: 8px;
}
.query-box {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 10px 12px;
}
.left-panel {
    background: #11161d;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 14px;
}
.graph-panel {
    background: #11161d;
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 10px;
}
</style>
""", unsafe_allow_html=True)

repo = MilanoRepository()
db = repo.mongo


def get_neo4j():
    return DatabaseManager().get_neo4j_session()


def render_pyvis_graph(net, height=560):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp_file:
        net.save_graph(tmp_file.name)
        with open(tmp_file.name, "r", encoding="utf-8") as f:
            html = f.read()
    components.html(html, height=height, scrolling=True)
    try:
        os.unlink(tmp_file.name)
    except OSError:
        pass


def build_milano_ops_graph():
    net = Network(
        height="560px",
        width="100%",
        bgcolor="#0d1117",
        font_color="#e6edf3",
        directed=True
    )

    with get_neo4j() as session:
        record = session.run(
            """
            MATCH (m:User {username: 'MilanoOps'})
            OPTIONAL MATCH (f:User)-[:FOLLOWS]->(m)
            OPTIONAL MATCH (m)-[:FOLLOWS]->(g:User)
            RETURN m.username AS ops,
                   collect(DISTINCT f.username) AS followers,
                   collect(DISTINCT g.username) AS following
            """
        ).single()

    if not record or not record["ops"]:
        return None

    ops = record["ops"]
    followers = [x for x in record["followers"] if x]
    following = [x for x in record["following"] if x]

    net.add_node(
        ops,
        label=ops,
        title="Compte officiel MilanoOps",
        color="#f85149",
        size=38
    )

    for username in followers:
        net.add_node(
            username,
            label=username,
            title=f"{username} suit MilanoOps",
            color="#58a6ff",
            size=22
        )
        net.add_edge(username, ops, color="#58a6ff", title="FOLLOWS")

    for username in following:
        if username != ops:
            if username not in followers:
                net.add_node(
                    username,
                    label=username,
                    title=f"MilanoOps suit {username}",
                    color="#3fb950",
                    size=22
                )
            net.add_edge(ops, username, color="#3fb950", title="FOLLOWS")

    net.repulsion(
        node_distance=180,
        central_gravity=0.15,
        spring_length=180,
        spring_strength=0.05
    )
    return net


def build_mutual_graph():
    net = Network(
        height="560px",
        width="100%",
        bgcolor="#0d1117",
        font_color="#e6edf3",
        directed=True
    )

    with get_neo4j() as session:
        records = list(session.run(
            """
            MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User)-[:FOLLOWS]->(m)
            RETURN m.username AS ops, u.username AS mutual
            """
        ))

    if not records:
        return None

    ops = "MilanoOps"
    net.add_node(
        ops,
        label=ops,
        color="#f85149",
        size=38,
        title="Compte officiel MilanoOps"
    )

    for row in records:
        mutual = row["mutual"]
        net.add_node(
            mutual,
            label=mutual,
            color="#bc8cff",
            size=22,
            title="Relation réciproque"
        )
        net.add_edge(ops, mutual, color="#3fb950", title="FOLLOWS")
        net.add_edge(mutual, ops, color="#58a6ff", title="FOLLOWS")

    net.repulsion(
        node_distance=180,
        central_gravity=0.15,
        spring_length=180,
        spring_strength=0.05
    )
    return net


def build_reply_thread_graph():
    net = Network(
        height="560px",
        width="100%",
        bgcolor="#0d1117",
        font_color="#e6edf3",
        directed=True
    )

    with get_neo4j() as session:
        record = session.run(
            """
            MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet)
            WHERE NOT (start)-[:REPLY_TO]->()
            RETURN length(path) AS depth,
                   [n IN nodes(path) | n.tweet_id] AS thread
            ORDER BY depth DESC
            LIMIT 1
            """
        ).single()

    if not record:
        return None, None

    thread = record["thread"]
    depth = record["depth"]

    tweet_docs = list(
        db.tweets.find(
            {"tweet_id": {"$in": thread}},
            {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1}
        )
    )
    tweet_map = {t["tweet_id"]: t for t in tweet_docs}

    for i, tweet_id in enumerate(thread):
        tweet = tweet_map.get(tweet_id, {})
        text = tweet.get("text", "")
        short_text = text[:80] + "..." if len(text) > 80 else text
        color = "#f85149" if i == len(thread) - 1 else "#58a6ff" if i == 0 else "#d29922"

        net.add_node(
            tweet_id,
            label=tweet_id[:8] + "...",
            title=short_text if short_text else tweet_id,
            color=color,
            size=25 if i in (0, len(thread) - 1) else 18
        )

    for i in range(len(thread) - 1):
        net.add_edge(thread[i], thread[i + 1], color="#bc8cff", title="REPLY_TO")

    net.repulsion(
        node_distance=220,
        central_gravity=0.08,
        spring_length=220,
        spring_strength=0.04
    )
    return net, depth


def build_conversation_overview_graph(limit=10):
    net = Network(
        height="600px",
        width="100%",
        bgcolor="#0d1117",
        font_color="#e6edf3",
        directed=True
    )

    with get_neo4j() as session:
        records = list(session.run(
            """
            MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet)
            WHERE NOT (start)-[:REPLY_TO]->()
              AND NOT ()-[:REPLY_TO]->(end)
            RETURN start.tweet_id AS debut, end.tweet_id AS fin, length(path) AS longueur
            ORDER BY longueur DESC
            LIMIT $limit
            """,
            limit=limit
        ))

    if not records:
        return None

    seen = set()

    for idx, row in enumerate(records, start=1):
        start_id = row["debut"]
        end_id = row["fin"]
        depth = row["longueur"]

        start_label = f"Start {idx}"
        end_label = f"End {idx}"

        if start_id not in seen:
            net.add_node(
                start_id,
                label=start_label,
                title=f"Début conversation\n{start_id}",
                color="#58a6ff",
                size=22
            )
            seen.add(start_id)

        if end_id not in seen:
            net.add_node(
                end_id,
                label=end_label,
                title=f"Fin conversation\n{end_id}",
                color="#f85149",
                size=22
            )
            seen.add(end_id)

        net.add_edge(
            start_id,
            end_id,
            title=f"Longueur: {depth}",
            color="#bc8cff",
            label=str(depth)
        )

    net.repulsion(
        node_distance=220,
        central_gravity=0.08,
        spring_length=220,
        spring_strength=0.04
    )
    return net


def render_chart(data, col_label, col_value, chart_kind="bar", height=None):
    if data is None or data.empty:
        return

    fig_height = height if height else max(2.8, len(data) * 0.45)
    fig, ax = plt.subplots(figsize=(8, fig_height))
    fig.patch.set_facecolor("#0d1117")
    ax.set_facecolor("#0d1117")

    palette = [
        "#58a6ff", "#3fb950", "#bc8cff", "#d29922", "#f85149",
        "#39d2c0", "#f778ba", "#ffa657", "#a5d6ff", "#7ee787"
    ]

    if chart_kind == "bar":
        bars = ax.barh(
            data[col_label].astype(str),
            data[col_value],
            color=palette[:len(data)],
            height=0.6,
            edgecolor="none"
        )
        max_value = max(data[col_value]) if len(data[col_value]) else 1
        ax.set_xlim(0, max_value * 1.25 if max_value > 0 else 1)

        for bar, val in zip(bars, data[col_value]):
            ax.text(
                bar.get_width() + max(max_value * 0.02, 0.2),
                bar.get_y() + bar.get_height() / 2,
                str(int(val)) if float(val).is_integer() else f"{val:.1f}",
                va="center",
                fontsize=10,
                color="#e6edf3",
                fontweight="bold"
            )

        ax.invert_yaxis()
        ax.xaxis.set_visible(False)

    elif chart_kind == "pie":
        ax.pie(
            data[col_value],
            labels=data[col_label],
            colors=palette[:len(data)],
            autopct="%1.0f%%",
            textprops={"color": "#e6edf3", "fontsize": 10}
        )

    ax.tick_params(colors="#8b949e", labelsize=9)
    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def render_tweet_card(tweet):
    sentiment = tweet.get("sentiment_score", 0)
    is_incident = tweet.get("is_incident", False)
    border = "#f85149" if sentiment < -0.3 else "#3fb950" if sentiment > 0.3 else "#d29922"
    badge = '<span style="background:#f8514922;color:#f85149;padding:2px 6px;border-radius:4px;font-size:0.7rem;font-weight:600;margin-left:6px;">INCIDENT</span>' if is_incident else ""
    tags_html = " ".join(f'<span style="color:#58a6ff;font-size:0.75rem;">#{tag}</span>' for tag in tweet.get("hashtags", []))
    user = db.users.find_one({"user_id": tweet.get("user_id")}, {"_id": 0, "username": 1})
    username = user["username"] if user else tweet.get("user_id", "?")
    text = tweet.get("text", "").replace("<", "&lt;").replace(">", "&gt;")
    html = f'<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin-bottom:8px;border-left:3px solid {border};"><div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;flex-wrap:wrap;"><span style="font-weight:600;color:#e6edf3;font-size:0.9rem;">@{username}</span><span style="color:#8b949e;font-size:0.75rem;">{tweet.get("favorite_count", 0)} likes | sentiment: {sentiment:.2f}</span>{badge}</div><div style="color:#e6edf3;font-size:0.92rem;line-height:1.5;margin-bottom:6px;">{text}</div><div>{tags_html}</div></div>'
    st.markdown(html, unsafe_allow_html=True)

def get_summary_data():
    nb_users = db.users.count_documents({})
    nb_tweets = db.tweets.count_documents({})
    nb_hashtags = len(db.tweets.distinct("hashtags"))
    nb_replies = db.tweets.count_documents({"in_reply_to_tweet_id": {"$ne": None}})
    nb_incidents = db.tweets.count_documents({"is_incident": True})

    avg_likes_data = list(
        db.tweets.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$favorite_count"}}}])
    )
    avg_likes = round(avg_likes_data[0]["avg"], 1) if avg_likes_data else 0

    roles_data = list(
        db.users.aggregate([
            {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ])
    )

    top_tags = list(
        db.tweets.aggregate([
            {"$unwind": "$hashtags"},
            {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 5}
        ])
    )

    summary_mix = pd.DataFrame({
        "Type": ["Tweets", "Réponses", "Incidents"],
        "Count": [nb_tweets, nb_replies, nb_incidents]
    })

    return {
        "nb_users": nb_users,
        "nb_tweets": nb_tweets,
        "nb_hashtags": nb_hashtags,
        "nb_replies": nb_replies,
        "nb_incidents": nb_incidents,
        "avg_likes": avg_likes,
        "roles_data": roles_data,
        "top_tags": top_tags,
        "summary_mix": summary_mix
    }


QUERY_DEFS = {
    "Q1 — Nombre d'utilisateurs": {
        "engine": "mongo",
        "query_text": "db.users.countDocuments({})"
    },
    "Q2 — Nombre de tweets": {
        "engine": "mongo",
        "query_text": "db.tweets.countDocuments({})"
    },
    "Q3 — Hashtags distincts": {
        "engine": "mongo",
        "query_text": "db.tweets.distinct('hashtags')"
    },
    "Q4 — Tweets par hashtag (filtre)": {
        "engine": "mongo",
        "query_text": "db.tweets.countDocuments({ hashtags: '<hashtag>' })"
    },
    "Q5 — Users distincts avec #milano2026": {
        "engine": "mongo",
        "query_text": "db.tweets.distinct('user_id', { hashtags: 'milano2026' })"
    },
    "Q6 — Tweets qui sont des réponses": {
        "engine": "mongo",
        "query_text": "db.tweets.find({ in_reply_to_tweet_id: { $ne: null } })"
    },
    "Q7 — Followers de MilanoOps": {
        "engine": "neo4j",
        "query_text": "MATCH (f:User)-[:FOLLOWS]->(m:User {username: 'MilanoOps'}) RETURN f.username AS follower, f.user_id AS uid"
    },
    "Q8 — Suivis par MilanoOps": {
        "engine": "neo4j",
        "query_text": "MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User) RETURN u.username AS following"
    },
    "Q9 — Relations réciproques MilanoOps": {
        "engine": "neo4j",
        "query_text": "MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User)-[:FOLLOWS]->(m) RETURN u.username AS mutual"
    },
    "Q10 — Users avec +10 followers": {
        "engine": "neo4j",
        "query_text": "MATCH (f:User)-[:FOLLOWS]->(u:User) WITH u, COUNT(f) AS followers WHERE followers > 10 RETURN u.username AS username, followers ORDER BY followers DESC"
    },
    "Q11 — Users suivant +5 personnes": {
        "engine": "neo4j",
        "query_text": "MATCH (u:User)-[:FOLLOWS]->(f:User) WITH u, COUNT(f) AS following WHERE following > 5 RETURN u.username AS username, following ORDER BY following DESC"
    },
    "Q12 — Top 10 tweets populaires": {
        "engine": "mongo",
        "query_text": "db.tweets.find().sort({ favorite_count: -1 }).limit(10)"
    },
    "Q13 — Top 10 hashtags populaires": {
        "engine": "mongo",
        "query_text": "db.tweets.aggregate([{ $unwind: '$hashtags' }, { $group: { _id: '$hashtags', count: { $sum: 1 } } }, { $sort: { count: -1 } }, { $limit: 10 }])"
    },
    "Q14 — Tweets initiateurs de discussion": {
        "engine": "neo4j",
        "query_text": "MATCH (reply:Tweet)-[:REPLY_TO]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() RETURN DISTINCT start.tweet_id AS thread_start"
    },
    "Q15 — Discussion la plus longue": {
        "engine": "neo4j",
        "query_text": "MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() RETURN length(path) AS depth, [n IN nodes(path) | n.tweet_id] AS thread ORDER BY depth DESC LIMIT 1"
    },
    "Q16 — Début et fin de chaque conversation": {
        "engine": "neo4j",
        "query_text": "MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() AND NOT ()-[:REPLY_TO]->(end) RETURN start.tweet_id AS debut, end.tweet_id AS fin, length(path) AS longueur ORDER BY longueur DESC"
    }
}


def run_selected_query(selected_query, hashtag_param=None):
    result_data = None
    result_text = ""
    chart_data = None
    chart_type = None

    if selected_query == "Q1 — Nombre d'utilisateurs":
        count = db.users.count_documents({})
        result_text = f"Nombre total d'utilisateurs : **{count}**"
        chart_data = pd.DataFrame(list(
            db.users.aggregate([
                {"$group": {"_id": "$role", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ])
        ))
        if not chart_data.empty:
            chart_data.columns = ["Rôle", "Count"]
            chart_type = "bar"

    elif selected_query == "Q2 — Nombre de tweets":
        count = db.tweets.count_documents({})
        result_text = f"Nombre total de tweets : **{count}**"
        time_data = list(db.tweets.aggregate([
            {"$group": {"_id": {"$hour": "$created_at"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]))
        if time_data:
            chart_data = pd.DataFrame(time_data)
            chart_data.columns = ["Heure", "Count"]
            chart_type = "bar"

    elif selected_query == "Q3 — Hashtags distincts":
        tags = db.tweets.distinct("hashtags")
        result_text = f"Nombre de hashtags distincts : **{len(tags)}**"
        if tags:
            result_data = pd.DataFrame({"Hashtag": [f"#{t}" for t in sorted(tags)]})

    elif selected_query == "Q4 — Tweets par hashtag (filtre)":
        if hashtag_param:
            count = db.tweets.count_documents({"hashtags": hashtag_param})
            result_text = f"Tweets contenant **#{hashtag_param}** : **{count}**"

            tweets = list(db.tweets.find(
                {"hashtags": hashtag_param},
                {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1, "favorite_count": 1, "sentiment_score": 1}
            ))
            if tweets:
                result_data = pd.DataFrame(tweets)

            sent_data = list(db.tweets.aggregate([
                {"$match": {"hashtags": hashtag_param}},
                {"$bucket": {
                    "groupBy": "$sentiment_score",
                    "boundaries": [-1, -0.5, -0.1, 0.1, 0.5, 1.01],
                    "default": "other",
                    "output": {"count": {"$sum": 1}}
                }}
            ]))
            if sent_data:
                labels = ["Très négatif", "Négatif", "Neutre", "Positif", "Très positif"]
                chart_data = pd.DataFrame(sent_data)
                chart_data["Label"] = labels[:len(chart_data)]
                chart_data = chart_data[["Label", "count"]]
                chart_data.columns = ["Sentiment", "Count"]
                chart_type = "bar"

    elif selected_query == "Q5 — Users distincts avec #milano2026":
        user_ids = db.tweets.distinct("user_id", {"hashtags": "milano2026"})
        result_text = f"Utilisateurs distincts ayant utilisé #milano2026 : **{len(user_ids)}**"
        users = list(db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "username": 1, "role": 1, "country": 1}))
        if users:
            result_data = pd.DataFrame(users)
        role_data = list(db.users.aggregate([
            {"$match": {"user_id": {"$in": user_ids}}},
            {"$group": {"_id": "$role", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]))
        if role_data:
            chart_data = pd.DataFrame(role_data)
            chart_data.columns = ["Rôle", "Count"]
            chart_type = "pie"

    elif selected_query == "Q6 — Tweets qui sont des réponses":
        replies = list(db.tweets.find(
            {"in_reply_to_tweet_id": {"$ne": None}},
            {"_id": 0, "tweet_id": 1, "user_id": 1, "text": 1, "in_reply_to_tweet_id": 1, "sentiment_score": 1}
        ))
        result_text = f"Nombre de tweets-réponses : **{len(replies)}**"
        if replies:
            result_data = pd.DataFrame(replies)

    elif selected_query == "Q7 — Followers de MilanoOps":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (f:User)-[:FOLLOWS]->(m:User {username: 'MilanoOps'}) RETURN f.username AS follower, f.user_id AS uid"
            )
            records = [dict(r) for r in res]
        result_text = f"Followers de MilanoOps : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)

    elif selected_query == "Q8 — Suivis par MilanoOps":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User) RETURN u.username AS following"
            )
            records = [dict(r) for r in res]
        result_text = f"MilanoOps suit **{len(records)}** utilisateurs."
        if records:
            result_data = pd.DataFrame(records)

    elif selected_query == "Q9 — Relations réciproques MilanoOps":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User)-[:FOLLOWS]->(m) RETURN u.username AS mutual"
            )
            records = [dict(r) for r in res]
        result_text = f"Relations réciproques : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)

    elif selected_query == "Q10 — Users avec +10 followers":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (f:User)-[:FOLLOWS]->(u:User) WITH u, COUNT(f) AS followers WHERE followers > 10 RETURN u.username AS username, followers ORDER BY followers DESC"
            )
            records = [dict(r) for r in res]
        result_text = f"Utilisateurs avec +10 followers : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
            chart_data = result_data.copy()
            chart_data.columns = ["Username", "Count"]
            chart_type = "bar"

    elif selected_query == "Q11 — Users suivant +5 personnes":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (u:User)-[:FOLLOWS]->(f:User) WITH u, COUNT(f) AS following WHERE following > 5 RETURN u.username AS username, following ORDER BY following DESC"
            )
            records = [dict(r) for r in res]
        result_text = f"Utilisateurs suivant +5 personnes : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
            chart_data = result_data.copy()
            chart_data.columns = ["Username", "Count"]
            chart_type = "bar"

    elif selected_query == "Q12 — Top 10 tweets populaires":
        top_tweets = list(db.tweets.find(
            {},
            {"_id": 0, "tweet_id": 1, "text": 1, "favorite_count": 1, "user_id": 1, "hashtags": 1}
        ).sort("favorite_count", -1).limit(10))
        result_text = "Top 10 tweets par likes"
        if top_tweets:
            result_data = pd.DataFrame(top_tweets)
            chart_data = pd.DataFrame({
                "Tweet": [t["tweet_id"][:8] + "..." for t in top_tweets],
                "Count": [t["favorite_count"] for t in top_tweets]
            })
            chart_type = "bar"

    elif selected_query == "Q13 — Top 10 hashtags populaires":
        tags_result = list(db.tweets.aggregate([
            {"$unwind": "$hashtags"},
            {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]))
        result_text = "Top 10 hashtags par fréquence"
        if tags_result:
            chart_data = pd.DataFrame(tags_result)
            chart_data.columns = ["Hashtag", "Count"]
            chart_data["Hashtag"] = chart_data["Hashtag"].apply(lambda x: f"#{x}")
            result_data = chart_data.copy()
            chart_type = "bar"

    elif selected_query == "Q14 — Tweets initiateurs de discussion":
        with get_neo4j() as session:
            res = session.run(
                "MATCH (reply:Tweet)-[:REPLY_TO]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() RETURN DISTINCT start.tweet_id AS thread_start"
            )
            records = [dict(r) for r in res]
        result_text = f"Tweets initiant une discussion : **{len(records)}**"
        if records:
            start_ids = [r["thread_start"] for r in records]
            tweets_info = list(db.tweets.find(
                {"tweet_id": {"$in": start_ids}},
                {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1, "favorite_count": 1}
            ))
            if tweets_info:
                result_data = pd.DataFrame(tweets_info)

    elif selected_query == "Q15 — Discussion la plus longue":
        with get_neo4j() as session:
            res = session.run(
                "MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() RETURN length(path) AS depth, [n IN nodes(path) | n.tweet_id] AS thread ORDER BY depth DESC LIMIT 1"
            )
            record = res.single()
        if record:
            depth = record["depth"]
            thread = record["thread"]
            result_text = f"Discussion la plus longue : **{depth}** niveaux, soit **{depth + 1}** tweets"
            tweets_info = list(db.tweets.find(
                {"tweet_id": {"$in": thread}},
                {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1}
            ))
            if tweets_info:
                result_data = pd.DataFrame(tweets_info)
                chart_data = pd.DataFrame({
                    "Mesure": ["Profondeur", "Tweets dans le thread"],
                    "Count": [depth, depth + 1]
                })
                chart_type = "bar"
        else:
            result_text = "Aucune discussion trouvée."

    elif selected_query == "Q16 — Début et fin de chaque conversation":
        with get_neo4j() as session:
            res = session.run(
                "MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet) WHERE NOT (start)-[:REPLY_TO]->() AND NOT ()-[:REPLY_TO]->(end) RETURN start.tweet_id AS debut, end.tweet_id AS fin, length(path) AS longueur ORDER BY longueur DESC"
            )
            records = [dict(r) for r in res]
        result_text = f"Conversations identifiées : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
            if len(result_data) > 0:
                chart_data = result_data[["debut", "longueur"]].copy()
                chart_data.columns = ["Conversation", "Count"]
                chart_type = "bar"

    return result_text, result_data, chart_data, chart_type


summary = get_summary_data()

st.markdown("## Milano 2026 — Ops Center")
st.caption("Plateforme de monitoring et d'analyse des tweets JO Milano-Cortina 2026")

k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(f'<div class="kpi-card kpi-blue"><div class="kpi-value">{summary["nb_users"]}</div><div class="kpi-label">Utilisateurs</div></div>', unsafe_allow_html=True)
with k2:
    st.markdown(f'<div class="kpi-card kpi-green"><div class="kpi-value">{summary["nb_tweets"]}</div><div class="kpi-label">Tweets</div></div>', unsafe_allow_html=True)
with k3:
    st.markdown(f'<div class="kpi-card kpi-purple"><div class="kpi-value">{summary["nb_hashtags"]}</div><div class="kpi-label">Hashtags</div></div>', unsafe_allow_html=True)
with k4:
    st.markdown(f'<div class="kpi-card kpi-orange"><div class="kpi-value">{summary["nb_replies"]}</div><div class="kpi-label">Réponses</div></div>', unsafe_allow_html=True)
with k5:
    st.markdown(f'<div class="kpi-card kpi-red"><div class="kpi-value">{summary["nb_incidents"]}</div><div class="kpi-label">Incidents IA</div></div>', unsafe_allow_html=True)
with k6:
    st.markdown(f'<div class="kpi-card kpi-teal"><div class="kpi-value">{summary["avg_likes"]}</div><div class="kpi-label">Likes moyen</div></div>', unsafe_allow_html=True)

st.markdown("")
top1, top2, top3 = st.columns(3)

with top1:
    st.markdown('<div class="section-title">Répartition par rôle</div>', unsafe_allow_html=True)
    if summary["roles_data"]:
        df_roles = pd.DataFrame(summary["roles_data"])
        df_roles.columns = ["Rôle", "Count"]
        render_chart(df_roles, "Rôle", "Count", "bar", height=2.8)

with top2:
    st.markdown('<div class="section-title">Top 5 hashtags</div>', unsafe_allow_html=True)
    if summary["top_tags"]:
        df_tags = pd.DataFrame(summary["top_tags"])
        df_tags.columns = ["Hashtag", "Count"]
        df_tags["Hashtag"] = df_tags["Hashtag"].apply(lambda x: f"#{x}")
        render_chart(df_tags, "Hashtag", "Count", "bar", height=2.8)

with top3:
    st.markdown('<div class="section-title">Vue d’ensemble</div>', unsafe_allow_html=True)
    render_chart(summary["summary_mix"], "Type", "Count", "pie", height=2.8)

st.divider()

tab_dashboard, tab_queries, tab_neo4j, tab_tweets, tab_users, tab_crud, tab_crisis = st.tabs([
    "Dashboard",
    "Requêtes",
    "Graphes Neo4j",
    "Tweets",
    "Utilisateurs",
    "Gestion",
    "Crisis Mode"
])

with tab_dashboard:
    st.markdown('<div class="section-title">Résumé opérationnel</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1.2, 1])
    with c1:
        latest_incidents = list(
            db.tweets.find({"is_incident": True}, {"_id": 0}).sort("created_at", -1).limit(5)
        )
        st.markdown("**Derniers incidents détectés**")
        if latest_incidents:
            for tweet in latest_incidents:
                render_tweet_card(tweet)
        else:
            st.success("Aucun incident détecté.")

    with c2:
        st.markdown("**Top utilisateurs par volume de tweets**")
        top_users = list(db.tweets.aggregate([
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 8}
        ]))
        if top_users:
            df_u = pd.DataFrame(top_users)
            usernames = []
            for uid in df_u["_id"]:
                user = db.users.find_one({"user_id": uid}, {"_id": 0, "username": 1})
                usernames.append(user["username"] if user else uid)
            df_u["Username"] = usernames
            df_u = df_u[["Username", "count"]]
            df_u.columns = ["Utilisateur", "Count"]
            render_chart(df_u, "Utilisateur", "Count", "bar")

with tab_queries:
    left, right = st.columns([1, 2])

    with left:
        st.markdown('<div class="section-title">Piloter les requêtes</div>', unsafe_allow_html=True)
        st.markdown('<div class="left-panel">', unsafe_allow_html=True)

        selected_query = st.selectbox("Choisir une requête", list(QUERY_DEFS.keys()))
        meta = QUERY_DEFS[selected_query]
        badge_color = "#3fb950" if meta["engine"] == "mongo" else "#bc8cff"
        badge_label = "MongoDB" if meta["engine"] == "mongo" else "Neo4j"
        st.markdown(
            f'<span class="badge" style="background:{badge_color}22;color:{badge_color};">{badge_label}</span>',
            unsafe_allow_html=True
        )

        hashtag_param = None
        if selected_query == "Q4 — Tweets par hashtag (filtre)":
            tags = sorted(db.tweets.distinct("hashtags"))
            hashtag_param = st.selectbox("Hashtag", tags)

        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-title">Requête exécutée</div>', unsafe_allow_html=True)
        lang = "javascript" if meta["engine"] == "mongo" else "cypher"
        st.code(meta["query_text"], language=lang)

        result_text, result_data, chart_data, chart_type = run_selected_query(selected_query, hashtag_param)

        st.markdown('<div class="section-title">Résultat</div>', unsafe_allow_html=True)
        st.markdown(result_text)

        if result_data is not None and not result_data.empty:
            st.dataframe(result_data, use_container_width=True, hide_index=True)

        if chart_data is not None and not chart_data.empty and chart_type:
            st.markdown('<div class="section-title">Visualisation</div>', unsafe_allow_html=True)
            render_chart(chart_data, chart_data.columns[0], chart_data.columns[1], chart_type)

with tab_neo4j:
    st.markdown('<div class="section-title">Visualisations Neo4j</div>', unsafe_allow_html=True)

    g1, g2 = st.columns(2)

    with g1:
        st.markdown("**Réseau autour de MilanoOps**")
        st.caption("Followers entrants et comptes suivis par MilanoOps.")
        ops_graph = build_milano_ops_graph()
        if ops_graph:
            render_pyvis_graph(ops_graph, height=580)
        else:
            st.info("Impossible de générer le graphe autour de MilanoOps.")

    with g2:
        st.markdown("**Relations réciproques avec MilanoOps**")
        st.caption("Utilisateurs ayant une relation bidirectionnelle avec MilanoOps.")
        mutual_graph = build_mutual_graph()
        if mutual_graph:
            render_pyvis_graph(mutual_graph, height=580)
        else:
            st.info("Aucune relation réciproque trouvée dans le dataset.")

    st.markdown("")
    st.markdown("**Discussion la plus longue**")
    st.caption("Chaîne REPLY_TO la plus longue détectée dans Neo4j.")
    thread_graph, depth = build_reply_thread_graph()
    if thread_graph:
        st.markdown(f"Profondeur détectée : **{depth}**")
        render_pyvis_graph(thread_graph, height=600)
    else:
        st.info("Aucune discussion trouvée.")

    st.markdown("")
    st.markdown("**Vue globale des conversations**")
    st.caption("Aperçu synthétique des conversations les plus longues.")
    overview_graph = build_conversation_overview_graph(limit=10)
    if overview_graph:
        render_pyvis_graph(overview_graph, height=620)
    else:
        st.info("Impossible de générer la vue globale des conversations.")

with tab_tweets:
    st.markdown('<div class="section-title">Explorer les tweets</div>', unsafe_allow_html=True)

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        all_hashtags = ["Tous"] + sorted(db.tweets.distinct("hashtags"))
        filter_hashtag = st.selectbox("Filtrer par hashtag", all_hashtags, key="explore_hashtag")
    with fc2:
        all_usernames = ["Tous"] + sorted(db.users.distinct("username"))
        filter_user = st.selectbox("Filtrer par utilisateur", all_usernames, key="explore_user")
    with fc3:
        filter_sentiment = st.selectbox(
            "Filtrer par sentiment",
            ["Tous", "Positif (> 0.3)", "Neutre", "Négatif (< -0.3)"],
            key="explore_sentiment"
        )
    with fc4:
        filter_incident = st.selectbox(
            "Type",
            ["Tous", "Incidents uniquement", "Sans incidents"],
            key="explore_incident"
        )

    sc1, sc2, _ = st.columns([1, 1, 2])
    with sc1:
        sort_by = st.selectbox(
            "Trier par",
            ["Date (récent)", "Date (ancien)", "Likes (desc)", "Likes (asc)", "Sentiment (desc)", "Sentiment (asc)"],
            key="explore_sort"
        )
    with sc2:
        page_size = st.selectbox("Par page", [10, 25, 50, 100], key="explore_page_size")

    mongo_filter = {}
    if filter_hashtag != "Tous":
        mongo_filter["hashtags"] = filter_hashtag

    if filter_user != "Tous":
        user_doc = db.users.find_one({"username": filter_user}, {"_id": 0, "user_id": 1})
        if user_doc:
            mongo_filter["user_id"] = user_doc["user_id"]

    if filter_sentiment == "Positif (> 0.3)":
        mongo_filter["sentiment_score"] = {"$gt": 0.3}
    elif filter_sentiment == "Négatif (< -0.3)":
        mongo_filter["sentiment_score"] = {"$lt": -0.3}
    elif filter_sentiment == "Neutre":
        mongo_filter["sentiment_score"] = {"$gte": -0.3, "$lte": 0.3}

    if filter_incident == "Incidents uniquement":
        mongo_filter["is_incident"] = True
    elif filter_incident == "Sans incidents":
        mongo_filter["is_incident"] = {"$ne": True}

    sort_map = {
        "Date (récent)": ("created_at", -1),
        "Date (ancien)": ("created_at", 1),
        "Likes (desc)": ("favorite_count", -1),
        "Likes (asc)": ("favorite_count", 1),
        "Sentiment (desc)": ("sentiment_score", -1),
        "Sentiment (asc)": ("sentiment_score", 1),
    }
    sort_field, sort_dir = sort_map[sort_by]

    total_matching = db.tweets.count_documents(mongo_filter)
    total_pages = max(1, (total_matching + page_size - 1) // page_size)
    page_num = st.number_input("Page", min_value=1, max_value=total_pages, value=1)

    st.markdown(f"**{total_matching}** tweets trouvés — page {page_num}/{total_pages}")

    skip = (page_num - 1) * page_size
    tweets_page = list(
        db.tweets.find(mongo_filter, {"_id": 0}).sort(sort_field, sort_dir).skip(skip).limit(page_size)
    )

    if tweets_page:
        for tweet in tweets_page:
            render_tweet_card(tweet)
    else:
        st.info("Aucun tweet ne correspond aux filtres.")

    if total_matching > 0:
        st.markdown('<div class="section-title">Analyse des résultats filtrés</div>', unsafe_allow_html=True)
        g1, g2 = st.columns(2)

        with g1:
            sent_data = list(db.tweets.aggregate([
                {"$match": mongo_filter},
                {"$bucket": {
                    "groupBy": "$sentiment_score",
                    "boundaries": [-1, -0.5, -0.1, 0.1, 0.5, 1.01],
                    "default": "other",
                    "output": {"count": {"$sum": 1}}
                }}
            ]))
            if sent_data:
                labels = ["Très négatif", "Négatif", "Neutre", "Positif", "Très positif"]
                df_sent = pd.DataFrame(sent_data)
                df_sent["Label"] = labels[:len(df_sent)]
                df_sent = df_sent[["Label", "count"]]
                df_sent.columns = ["Sentiment", "Count"]
                render_chart(df_sent, "Sentiment", "Count")

        with g2:
            tag_data = list(db.tweets.aggregate([
                {"$match": mongo_filter},
                {"$unwind": "$hashtags"},
                {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 8}
            ]))
            if tag_data:
                df_tags = pd.DataFrame(tag_data)
                df_tags.columns = ["Hashtag", "Count"]
                df_tags["Hashtag"] = df_tags["Hashtag"].apply(lambda x: f"#{x}")
                render_chart(df_tags, "Hashtag", "Count")

with tab_users:
    st.markdown('<div class="section-title">Explorer les utilisateurs</div>', unsafe_allow_html=True)

    uf1, uf2 = st.columns(2)
    with uf1:
        filter_role = st.selectbox("Filtrer par rôle", ["Tous", "fan", "volunteer", "journalist", "staff"])
    with uf2:
        user_search = st.text_input("Rechercher un username", placeholder="Tapez un nom...")

    user_filter = {}
    if filter_role != "Tous":
        user_filter["role"] = filter_role
    if user_search:
        user_filter["username"] = {"$regex": user_search, "$options": "i"}

    users_found = list(db.users.find(user_filter, {"_id": 0}).sort("username", 1))
    st.markdown(f"**{len(users_found)}** utilisateurs trouvés")

    if users_found:
        df_users = pd.DataFrame(users_found)
        cols_order = [c for c in ["user_id", "username", "role", "country", "created_at"] if c in df_users.columns]
        st.dataframe(df_users[cols_order], use_container_width=True, hide_index=True)

        selected_profile = st.selectbox(
            "Sélectionner un utilisateur",
            [u["username"] for u in users_found]
        )

        if selected_profile:
            profile = db.users.find_one({"username": selected_profile}, {"_id": 0})
            if profile:
                uid = profile["user_id"]
                pc1, pc2, pc3, pc4 = st.columns(4)

                tweet_count = db.tweets.count_documents({"user_id": uid})

                avg_sent = list(db.tweets.aggregate([
                    {"$match": {"user_id": uid}},
                    {"$group": {"_id": None, "avg": {"$avg": "$sentiment_score"}}}
                ]))
                avg_s = round(avg_sent[0]["avg"], 2) if avg_sent else 0

                total_likes = list(db.tweets.aggregate([
                    {"$match": {"user_id": uid}},
                    {"$group": {"_id": None, "total": {"$sum": "$favorite_count"}}}
                ]))
                total_l = total_likes[0]["total"] if total_likes else 0

                pc1.metric("Tweets", tweet_count)
                pc2.metric("Likes total", total_l)
                pc3.metric("Sentiment moyen", avg_s)
                pc4.metric("Rôle", profile.get("role", "?"))

                st.markdown(f"**Derniers tweets de @{selected_profile}**")
                user_tweets = list(db.tweets.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).limit(5))
                for tweet in user_tweets:
                    render_tweet_card(tweet)

with tab_crud:
    st.markdown('<div class="section-title">Gestion des données</div>', unsafe_allow_html=True)

    left_crud, right_crud = st.columns([1, 2])

    with left_crud:
        crud_entity = st.radio("Entité", ["Users", "Tweets"], horizontal=True)

    with right_crud:
        if crud_entity == "Users":
            operation = st.selectbox(
                "Opération",
                ["Ajouter un utilisateur", "Modifier un utilisateur", "Supprimer un utilisateur"]
            )

            if operation == "Ajouter un utilisateur":
                with st.form("add_user", clear_on_submit=True):
                    uid = st.text_input("User ID", placeholder="ex: u_100")
                    uname = st.text_input("Username", placeholder="ex: jean_dupont")
                    role = st.selectbox("Rôle", ["fan", "volunteer", "journalist", "staff"])
                    country = st.text_input("Pays", placeholder="ex: France")
                    submitted = st.form_submit_button("Ajouter", type="primary", use_container_width=True)
                    if submitted and uid and uname:
                        from datetime import datetime
                        try:
                            repo.create_user({
                                "user_id": uid,
                                "username": uname,
                                "role": role,
                                "country": country,
                                "created_at": datetime.now()
                            })
                            st.success(f"Utilisateur '{uname}' créé.")
                            st.rerun()
                        except Exception as error:
                            st.error(f"Erreur : {error}")

            elif operation == "Modifier un utilisateur":
                users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
                user_opts = {f"{u['username']} ({u['user_id']})": u["user_id"] for u in users_list}
                selected = st.selectbox("Sélectionner", list(user_opts.keys()))
                if selected:
                    uid = user_opts[selected]
                    current = db.users.find_one({"user_id": uid}, {"_id": 0})
                    with st.form("edit_user"):
                        new_name = st.text_input("Nouveau username", value=current.get("username", ""))
                        roles = ["fan", "volunteer", "journalist", "staff"]
                        new_role = st.selectbox("Nouveau rôle", roles, index=roles.index(current.get("role", "fan")))
                        new_country = st.text_input("Nouveau pays", value=current.get("country", ""))
                        submitted = st.form_submit_button("Modifier", type="primary", use_container_width=True)
                        if submitted:
                            repo.update_user(uid, {
                                "username": new_name,
                                "role": new_role,
                                "country": new_country
                            })
                            st.success(f"Utilisateur '{uid}' mis à jour.")
                            st.rerun()

            elif operation == "Supprimer un utilisateur":
                users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
                user_opts = {f"{u['username']} ({u['user_id']})": u["user_id"] for u in users_list}
                selected = st.selectbox("Sélectionner", list(user_opts.keys()))
                if selected:
                    uid = user_opts[selected]
                    if st.button(f"Supprimer {selected}", type="primary", use_container_width=True):
                        repo.delete_user(uid)
                        st.success(f"Utilisateur '{uid}' supprimé.")
                        st.rerun()

        else:
            operation = st.selectbox(
                "Opération",
                ["Ajouter un tweet", "Modifier un tweet", "Supprimer un tweet"]
            )

            if operation == "Ajouter un tweet":
                with st.form("add_tweet", clear_on_submit=True):
                    from datetime import datetime
                    from faker import Faker
                    from core.services import SentimentService

                    users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
                    user_opts = {u["username"]: u["user_id"] for u in users_list}

                    author = st.selectbox("Auteur", list(user_opts.keys()))
                    text = st.text_area("Texte du tweet", placeholder="Votre tweet ici...")
                    hashtags_str = st.text_input("Hashtags (virgules)", placeholder="milano2026, transport")
                    submitted = st.form_submit_button("Publier", type="primary", use_container_width=True)

                    if submitted and text:
                        fake = Faker()
                        ai = SentimentService()
                        analysis = ai.analyze_tweet(text)
                        hashtags = [h.strip() for h in hashtags_str.split(",") if h.strip()]

                        repo.create_tweet({
                            "tweet_id": fake.uuid4(),
                            "user_id": user_opts[author],
                            "text": text,
                            "hashtags": hashtags,
                            "created_at": datetime.now(),
                            "favorite_count": 0,
                            "in_reply_to_tweet_id": None,
                            "is_incident": analysis["is_incident"],
                            "sentiment_score": analysis["sentiment"]
                        })
                        st.success("Tweet publié.")
                        st.rerun()

            elif operation == "Modifier un tweet":
                tweets_list = list(db.tweets.find({}, {"_id": 0, "tweet_id": 1, "text": 1}).limit(50))
                tweet_opts = {f"{t['text'][:60]}...": t["tweet_id"] for t in tweets_list}
                selected = st.selectbox("Sélectionner", list(tweet_opts.keys()))
                if selected:
                    tid = tweet_opts[selected]
                    current = db.tweets.find_one({"tweet_id": tid}, {"_id": 0})
                    with st.form("edit_tweet"):
                        new_text = st.text_area("Nouveau texte", value=current.get("text", ""))
                        new_tags = st.text_input("Nouveaux hashtags", value=", ".join(current.get("hashtags", [])))
                        submitted = st.form_submit_button("Modifier", type="primary", use_container_width=True)
                        if submitted:
                            tags = [h.strip() for h in new_tags.split(",") if h.strip()]
                            repo.update_tweet(tid, {"text": new_text, "hashtags": tags})
                            st.success("Tweet mis à jour.")
                            st.rerun()

            elif operation == "Supprimer un tweet":
                tweets_list = list(db.tweets.find({}, {"_id": 0, "tweet_id": 1, "text": 1}).limit(50))
                tweet_opts = {f"{t['text'][:60]}...": t["tweet_id"] for t in tweets_list}
                selected = st.selectbox("Sélectionner", list(tweet_opts.keys()))
                if selected:
                    tid = tweet_opts[selected]
                    if st.button("Supprimer ce tweet", type="primary", use_container_width=True):
                        repo.delete_tweet(tid)
                        st.success("Tweet supprimé.")
                        st.rerun()

with tab_crisis:
    st.markdown('<div class="section-title">Crisis Mode — supervision</div>', unsafe_allow_html=True)

    crisis_filter = {
        "$or": [
            {"is_incident": True},
            {"sentiment_score": {"$lt": -0.4}},
            {"hashtags": {"$in": ["transportfail", "disaster", "alert", "safety", "metrom1", "shame"]}}
        ]
    }

    crisis_tweets = list(db.tweets.find(crisis_filter, {"_id": 0}).sort("created_at", -1))
    very_negative = db.tweets.count_documents({"sentiment_score": {"$lt": -0.5}})
    ops_alerts = db.tweets.count_documents({"user_id": "u_ops"})
    incident_count = db.tweets.count_documents({"is_incident": True})

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tweets critiques", len(crisis_tweets))
    c2.metric("Incidents confirmés", incident_count)
    c3.metric("Très négatifs", very_negative)
    c4.metric("Messages MilanoOps", ops_alerts)

    st.markdown("### Flux critique")
    if crisis_tweets:
        for tweet in crisis_tweets[:15]:
            render_tweet_card(tweet)
    else:
        st.success("Aucun signal critique détecté.")

    st.markdown("### Analyse de crise")
    g1, g2 = st.columns(2)

    with g1:
        crisis_tags = list(db.tweets.aggregate([
            {"$match": crisis_filter},
            {"$unwind": "$hashtags"},
            {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 8}
        ]))
        if crisis_tags:
            df_tags = pd.DataFrame(crisis_tags)
            df_tags.columns = ["Hashtag", "Count"]
            df_tags["Hashtag"] = df_tags["Hashtag"].apply(lambda x: f"#{x}")
            render_chart(df_tags, "Hashtag", "Count")

    with g2:
        crisis_users = list(db.tweets.aggregate([
            {"$match": crisis_filter},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 8}
        ]))
        if crisis_users:
            df_users = pd.DataFrame(crisis_users)
            usernames = []
            for uid in df_users["_id"]:
                user = db.users.find_one({"user_id": uid}, {"_id": 0, "username": 1})
                usernames.append(user["username"] if user else uid)
            df_users["Utilisateur"] = usernames
            df_users = df_users[["Utilisateur", "count"]]
            df_users.columns = ["Utilisateur", "Count"]
            render_chart(df_users, "Utilisateur", "Count")