"""
Milano 2026 Ops Center — Dashboard Streamlit
Layout: KPIs en haut | CRUD a gauche | Requetes + Graphes a droite
"""

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")

from core.repositories import MilanoRepository
from core.database import DatabaseManager

# ---------- CONFIG ----------
st.set_page_config(page_title="Milano 2026 — Ops Center", layout="wide", initial_sidebar_state="collapsed")

# ---------- CUSTOM CSS ----------
st.markdown("""
<style>
    /* Clean dark theme overrides */
    .block-container { padding-top: 1.5rem; padding-bottom: 0; }
    h1, h2, h3 { font-family: 'Segoe UI', sans-serif; }
    
    /* KPI cards */
    .kpi-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .kpi-value {
        font-size: 2.4rem;
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
    
    /* Section headers */
    .section-title {
        font-size: 1rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        color: #8b949e;
        border-bottom: 2px solid #30363d;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }
    
    /* Query result styling */
    .query-box {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 16px;
        font-family: 'Courier New', monospace;
        font-size: 0.85rem;
        color: #c9d1d9;
        margin-bottom: 12px;
    }
    
    /* Streamlit overrides */
    div[data-testid="stMetric"] { background: #161b22; border-radius: 8px; padding: 12px; border: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { background: #161b22; border-radius: 6px; padding: 8px 16px; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ---------- INIT ----------
repo = MilanoRepository()
db = repo.mongo

# ---------- HEADER ----------
st.markdown("## Milano 2026 — Ops Center")
st.caption("Plateforme de monitoring et d'analyse des tweets JO Milano-Cortina 2026")

# ═══════════════════════════════════════════
# SECTION 1 : KPI SUMMARY (HAUT)
# ═══════════════════════════════════════════

nb_users = db.users.count_documents({})
nb_tweets = db.tweets.count_documents({})
nb_hashtags = len(db.tweets.distinct("hashtags"))
nb_replies = db.tweets.count_documents({"in_reply_to_tweet_id": {"$ne": None}})
nb_incidents = db.tweets.count_documents({"is_incident": True})

# Roles distribution for mini chart
roles_pipeline = [
    {"$group": {"_id": "$role", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
roles_data = list(db.users.aggregate(roles_pipeline))

# Top hashtags for mini chart
hashtags_pipeline = [
    {"$unwind": "$hashtags"},
    {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 5}
]
top_tags = list(db.tweets.aggregate(hashtags_pipeline))

# KPI row
k1, k2, k3, k4, k5, k6 = st.columns(6)

with k1:
    st.markdown(f"""<div class="kpi-card kpi-blue">
        <div class="kpi-value">{nb_users}</div>
        <div class="kpi-label">Utilisateurs</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""<div class="kpi-card kpi-green">
        <div class="kpi-value">{nb_tweets}</div>
        <div class="kpi-label">Tweets</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""<div class="kpi-card kpi-purple">
        <div class="kpi-value">{nb_hashtags}</div>
        <div class="kpi-label">Hashtags distincts</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""<div class="kpi-card kpi-orange">
        <div class="kpi-value">{nb_replies}</div>
        <div class="kpi-label">Reponses</div>
    </div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""<div class="kpi-card kpi-red">
        <div class="kpi-value">{nb_incidents}</div>
        <div class="kpi-label">Incidents IA</div>
    </div>""", unsafe_allow_html=True)
with k6:
    avg_likes = list(db.tweets.aggregate([{"$group": {"_id": None, "avg": {"$avg": "$favorite_count"}}}]))
    avg_val = round(avg_likes[0]["avg"], 1) if avg_likes else 0
    st.markdown(f"""<div class="kpi-card kpi-teal">
        <div class="kpi-value">{avg_val}</div>
        <div class="kpi-label">Likes moyen</div>
    </div>""", unsafe_allow_html=True)

# Mini charts row
st.markdown("")
mc1, mc2 = st.columns(2)

with mc1:
    st.markdown('<div class="section-title">Repartition par role</div>', unsafe_allow_html=True)
    if roles_data:
        fig, ax = plt.subplots(figsize=(4, 2.5))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        colors = ["#58a6ff", "#3fb950", "#bc8cff", "#d29922", "#f85149"]
        roles = [r["_id"] for r in roles_data]
        counts = [r["count"] for r in roles_data]
        bars = ax.barh(roles, counts, color=colors[:len(roles)], height=0.6, edgecolor="none")
        ax.set_xlim(0, max(counts) * 1.3)
        for bar, val in zip(bars, counts):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2, str(val),
                    va="center", fontsize=10, color="#e6edf3", fontweight="bold")
        ax.tick_params(colors="#8b949e", labelsize=9)
        ax.spines[:].set_visible(False)
        ax.xaxis.set_visible(False)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

with mc2:
    st.markdown('<div class="section-title">Top 5 hashtags</div>', unsafe_allow_html=True)
    if top_tags:
        fig, ax = plt.subplots(figsize=(4, 2.5))
        fig.patch.set_facecolor("#0d1117")
        ax.set_facecolor("#0d1117")
        colors = ["#3fb950", "#58a6ff", "#bc8cff", "#d29922", "#f85149"]
        tags = [f"#{t['_id']}" for t in top_tags]
        vals = [t["count"] for t in top_tags]
        bars = ax.barh(tags, vals, color=colors[:len(tags)], height=0.6, edgecolor="none")
        ax.set_xlim(0, max(vals) * 1.3)
        for bar, val in zip(bars, vals):
            ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2, str(val),
                    va="center", fontsize=10, color="#e6edf3", fontweight="bold")
        ax.tick_params(colors="#8b949e", labelsize=9)
        ax.spines[:].set_visible(False)
        ax.xaxis.set_visible(False)
        ax.invert_yaxis()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close(fig)

st.divider()

# ═══════════════════════════════════════════
# SECTION 2 : GAUCHE (CRUD) | DROITE (REQUETES)
# ═══════════════════════════════════════════

col_left, col_right = st.columns([1, 2])

# ───────── GAUCHE : CRUD ─────────
with col_left:
    st.markdown('<div class="section-title">Gestion des donnees</div>', unsafe_allow_html=True)
    
    crud_tab = st.radio("Entite", ["Users", "Tweets"], horizontal=True, label_visibility="collapsed")
    
    if crud_tab == "Users":
        operation = st.selectbox("Operation", ["Ajouter un utilisateur", "Modifier un utilisateur", "Supprimer un utilisateur"], key="user_op")
        
        if operation == "Ajouter un utilisateur":
            with st.form("add_user", clear_on_submit=True):
                uid = st.text_input("User ID", placeholder="ex: u_100")
                uname = st.text_input("Username", placeholder="ex: jean_dupont")
                role = st.selectbox("Role", ["fan", "volunteer", "journalist", "staff"])
                country = st.text_input("Pays", placeholder="ex: France")
                submitted = st.form_submit_button("Ajouter", type="primary", use_container_width=True)
                if submitted and uid and uname:
                    from datetime import datetime
                    user_data = {
                        "user_id": uid, "username": uname,
                        "role": role, "country": country, "created_at": datetime.now()
                    }
                    try:
                        repo.create_user(user_data)
                        st.success(f"Utilisateur '{uname}' cree avec succes.")
                    except Exception as e:
                        st.error(f"Erreur : {e}")
                        
        elif operation == "Modifier un utilisateur":
            users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
            user_options = {f"{u['username']} ({u['user_id']})": u["user_id"] for u in users_list}
            selected = st.selectbox("Selectionner", list(user_options.keys()), key="edit_user_select")
            if selected:
                uid = user_options[selected]
                current = db.users.find_one({"user_id": uid}, {"_id": 0})
                with st.form("edit_user"):
                    new_name = st.text_input("Nouveau username", value=current.get("username", ""))
                    new_role = st.selectbox("Nouveau role", ["fan", "volunteer", "journalist", "staff"],
                                           index=["fan", "volunteer", "journalist", "staff"].index(current.get("role", "fan")))
                    new_country = st.text_input("Nouveau pays", value=current.get("country", ""))
                    submitted = st.form_submit_button("Modifier", type="primary", use_container_width=True)
                    if submitted:
                        repo.update_user(uid, {"username": new_name, "role": new_role, "country": new_country})
                        st.success(f"Utilisateur '{uid}' mis a jour.")
                        st.rerun()
                        
        elif operation == "Supprimer un utilisateur":
            users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
            user_options = {f"{u['username']} ({u['user_id']})": u["user_id"] for u in users_list}
            selected = st.selectbox("Selectionner", list(user_options.keys()), key="del_user_select")
            if selected:
                uid = user_options[selected]
                if st.button(f"Supprimer {selected}", type="primary", use_container_width=True):
                    repo.delete_user(uid)
                    st.success(f"Utilisateur '{uid}' supprime.")
                    st.rerun()
    
    else:  # Tweets
        operation = st.selectbox("Operation", ["Ajouter un tweet", "Modifier un tweet", "Supprimer un tweet"], key="tweet_op")
        
        if operation == "Ajouter un tweet":
            with st.form("add_tweet", clear_on_submit=True):
                # User select
                users_list = list(db.users.find({}, {"_id": 0, "user_id": 1, "username": 1}))
                user_options = {f"{u['username']}": u["user_id"] for u in users_list}
                author = st.selectbox("Auteur", list(user_options.keys()))
                text = st.text_area("Texte du tweet", placeholder="Votre tweet ici...")
                hashtags_str = st.text_input("Hashtags (separes par des virgules)", placeholder="milano2026, transport")
                submitted = st.form_submit_button("Publier", type="primary", use_container_width=True)
                if submitted and text:
                    from datetime import datetime
                    from faker import Faker
                    from core.services import SentimentService
                    fake = Faker()
                    ai = SentimentService()
                    analysis = ai.analyze_tweet(text)
                    hashtags = [h.strip() for h in hashtags_str.split(",") if h.strip()]
                    tweet_data = {
                        "tweet_id": fake.uuid4(),
                        "user_id": user_options[author],
                        "text": text,
                        "hashtags": hashtags,
                        "created_at": datetime.now(),
                        "favorite_count": 0,
                        "in_reply_to_tweet_id": None,
                        "is_incident": analysis["is_incident"],
                        "sentiment_score": analysis["sentiment"]
                    }
                    repo.create_tweet(tweet_data)
                    st.success("Tweet publie avec succes.")
                    
        elif operation == "Modifier un tweet":
            tweets_list = list(db.tweets.find({}, {"_id": 0, "tweet_id": 1, "text": 1}).limit(50))
            tweet_options = {f"{t['text'][:60]}...": t["tweet_id"] for t in tweets_list}
            selected = st.selectbox("Selectionner un tweet", list(tweet_options.keys()), key="edit_tweet_select")
            if selected:
                tid = tweet_options[selected]
                current = db.tweets.find_one({"tweet_id": tid}, {"_id": 0})
                with st.form("edit_tweet"):
                    new_text = st.text_area("Nouveau texte", value=current.get("text", ""))
                    new_tags = st.text_input("Nouveaux hashtags", value=", ".join(current.get("hashtags", [])))
                    submitted = st.form_submit_button("Modifier", type="primary", use_container_width=True)
                    if submitted:
                        tags = [h.strip() for h in new_tags.split(",") if h.strip()]
                        repo.update_tweet(tid, {"text": new_text, "hashtags": tags})
                        st.success("Tweet mis a jour.")
                        st.rerun()
                        
        elif operation == "Supprimer un tweet":
            tweets_list = list(db.tweets.find({}, {"_id": 0, "tweet_id": 1, "text": 1}).limit(50))
            tweet_options = {f"{t['text'][:60]}...": t["tweet_id"] for t in tweets_list}
            selected = st.selectbox("Selectionner un tweet", list(tweet_options.keys()), key="del_tweet_select")
            if selected:
                tid = tweet_options[selected]
                if st.button(f"Supprimer ce tweet", type="primary", use_container_width=True):
                    repo.delete_tweet(tid)
                    st.success("Tweet supprime.")
                    st.rerun()

# ───────── DROITE : REQUETES + GRAPHS ─────────
with col_right:
    st.markdown('<div class="section-title">Requetes MongoDB & Neo4j</div>', unsafe_allow_html=True)
    
    # Définition des requêtes
    queries = {
        "Q1 — Nombre d'utilisateurs": "mongo",
        "Q2 — Nombre de tweets": "mongo",
        "Q3 — Hashtags distincts": "mongo",
        "Q4 — Tweets par hashtag (filtre)": "mongo",
        "Q5 — Users distincts avec #milano2026": "mongo",
        "Q6 — Tweets qui sont des reponses": "mongo",
        "Q7 — Followers de MilanoOps": "neo4j",
        "Q8 — Suivis par MilanoOps": "neo4j",
        "Q9 — Relations reciproques MilanoOps": "neo4j",
        "Q10 — Users avec +10 followers": "neo4j",
        "Q11 — Users suivant +5 personnes": "neo4j",
        "Q12 — Top 10 tweets populaires": "mongo",
        "Q13 — Top 10 hashtags populaires": "mongo",
        "Q14 — Tweets initiateurs de discussion": "neo4j",
        "Q15 — Discussion la plus longue": "neo4j",
        "Q16 — Debut et fin de chaque conversation": "neo4j",
    }
    
    selected_query = st.selectbox(
        "Choisir une requete",
        list(queries.keys()),
        key="query_select"
    )
    
    query_type = queries[selected_query]
    badge_color = "#3fb950" if query_type == "mongo" else "#bc8cff"
    badge_label = "MongoDB" if query_type == "mongo" else "Neo4j"
    st.markdown(f'<span style="background:{badge_color}22;color:{badge_color};padding:4px 10px;border-radius:4px;font-size:0.8rem;font-weight:600;">{badge_label}</span>', unsafe_allow_html=True)

    # Parametre pour Q4
    hashtag_param = None
    if selected_query == "Q4 — Tweets par hashtag (filtre)":
        all_tags = db.tweets.distinct("hashtags")
        hashtag_param = st.selectbox("Choisir un hashtag", all_tags, key="q4_hashtag")

    st.markdown("")
    
    # ═══ EXECUTION DES REQUETES ═══
    
    neo4j_session = None
    
    def get_neo4j():
        return DatabaseManager().get_neo4j_session()
    
    result_data = None
    result_text = ""
    chart_data = None
    chart_type = None  # "bar", "pie", "table"
    
    if selected_query == "Q1 — Nombre d'utilisateurs":
        count = db.users.count_documents({})
        result_text = f"Nombre total d'utilisateurs : **{count}**"
        # Mini chart: users by role
        chart_data = pd.DataFrame(list(db.users.aggregate(roles_pipeline)))
        if not chart_data.empty:
            chart_data.columns = ["Role", "Count"]
            chart_type = "bar"
    
    elif selected_query == "Q2 — Nombre de tweets":
        count = db.tweets.count_documents({})
        result_text = f"Nombre total de tweets : **{count}**"
        # Chart: tweets par heure
        time_pipeline = [
            {"$group": {"_id": {"$hour": "$created_at"}, "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}}
        ]
        time_data = list(db.tweets.aggregate(time_pipeline))
        if time_data:
            chart_data = pd.DataFrame(time_data)
            chart_data.columns = ["Heure", "Count"]
            chart_type = "bar"
    
    elif selected_query == "Q3 — Hashtags distincts":
        tags = db.tweets.distinct("hashtags")
        result_text = f"Nombre de hashtags distincts : **{len(tags)}**\n\nListe : {', '.join(f'`#{t}`' for t in tags)}"
    
    elif selected_query == "Q4 — Tweets par hashtag (filtre)":
        if hashtag_param:
            count = db.tweets.count_documents({"hashtags": hashtag_param})
            result_text = f"Tweets contenant **#{hashtag_param}** : **{count}**"
            # Chart: sentiment distribution pour ce hashtag
            sent_pipeline = [
                {"$match": {"hashtags": hashtag_param}},
                {"$bucket": {
                    "groupBy": "$sentiment_score",
                    "boundaries": [-1, -0.5, -0.1, 0.1, 0.5, 1.01],
                    "default": "other",
                    "output": {"count": {"$sum": 1}}
                }}
            ]
            try:
                sent_data = list(db.tweets.aggregate(sent_pipeline))
                if sent_data:
                    labels = ["Tres negatif", "Negatif", "Neutre", "Positif", "Tres positif"]
                    chart_data = pd.DataFrame(sent_data)
                    chart_data["Label"] = labels[:len(chart_data)]
                    chart_data = chart_data[["Label", "count"]]
                    chart_data.columns = ["Sentiment", "Count"]
                    chart_type = "bar"
            except Exception:
                pass
    
    elif selected_query == "Q5 — Users distincts avec #milano2026":
        user_ids = db.tweets.distinct("user_id", {"hashtags": "milano2026"})
        result_text = f"Utilisateurs distincts ayant utilise #milano2026 : **{len(user_ids)}**"
        # Chart: ces users par role
        if user_ids:
            role_pipeline = [
                {"$match": {"user_id": {"$in": user_ids}}},
                {"$group": {"_id": "$role", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            role_data = list(db.users.aggregate(role_pipeline))
            if role_data:
                chart_data = pd.DataFrame(role_data)
                chart_data.columns = ["Role", "Count"]
                chart_type = "pie"
    
    elif selected_query == "Q6 — Tweets qui sont des reponses":
        replies = list(db.tweets.find(
            {"in_reply_to_tweet_id": {"$ne": None}},
            {"_id": 0, "tweet_id": 1, "user_id": 1, "text": 1, "in_reply_to_tweet_id": 1, "sentiment_score": 1}
        ))
        result_text = f"Nombre de tweets-reponses : **{len(replies)}**"
        result_data = pd.DataFrame(replies) if replies else None
    
    elif selected_query == "Q7 — Followers de MilanoOps":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (f:User)-[:FOLLOWS]->(m:User {username: 'MilanoOps'})
                RETURN f.username AS follower, f.user_id AS uid
            """)
            records = [dict(r) for r in res]
        result_text = f"Nombre de followers de MilanoOps : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
    
    elif selected_query == "Q8 — Suivis par MilanoOps":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User)
                RETURN u.username AS following
            """)
            records = [dict(r) for r in res]
        if records:
            result_text = f"MilanoOps suit **{len(records)}** utilisateurs."
            result_data = pd.DataFrame(records)
        else:
            result_text = "MilanoOps ne suit aucun utilisateur. C'est coherent : un compte officiel/institutionnel n'a pas d'abonnements sortants."
    
    elif selected_query == "Q9 — Relations reciproques MilanoOps":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (m:User {username: 'MilanoOps'})-[:FOLLOWS]->(u:User)-[:FOLLOWS]->(m)
                RETURN u.username AS mutual
            """)
            records = [dict(r) for r in res]
        if records:
            result_text = f"Relations reciproques : **{len(records)}**"
            result_data = pd.DataFrame(records)
        else:
            result_text = "Aucune relation reciproque. MilanoOps ne possede aucun abonnement sortant, donc aucun lien bidirectionnel n'est possible."
    
    elif selected_query == "Q10 — Users avec +10 followers":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (f:User)-[:FOLLOWS]->(u:User)
                WITH u, COUNT(f) AS followers
                WHERE followers > 10
                RETURN u.username AS username, followers
                ORDER BY followers DESC
            """)
            records = [dict(r) for r in res]
        result_text = f"Utilisateurs avec plus de 10 followers : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
            chart_data = result_data.copy()
            chart_data.columns = ["Username", "Count"]
            chart_type = "bar"
    
    elif selected_query == "Q11 — Users suivant +5 personnes":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (u:User)-[:FOLLOWS]->(f:User)
                WITH u, COUNT(f) AS following
                WHERE following > 5
                RETURN u.username AS username, following
                ORDER BY following DESC
            """)
            records = [dict(r) for r in res]
        result_text = f"Utilisateurs suivant plus de 5 personnes : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
            chart_data = result_data.copy()
            chart_data.columns = ["Username", "Count"]
            chart_type = "bar"
    
    elif selected_query == "Q12 — Top 10 tweets populaires":
        top_tweets = list(db.tweets.find(
            {}, {"_id": 0, "tweet_id": 1, "text": 1, "favorite_count": 1, "user_id": 1, "hashtags": 1}
        ).sort("favorite_count", -1).limit(10))
        result_text = f"Top 10 tweets par nombre de likes :"
        if top_tweets:
            result_data = pd.DataFrame(top_tweets)
            chart_data = pd.DataFrame({
                "Tweet": [t["tweet_id"][:8] + "..." for t in top_tweets],
                "Count": [t["favorite_count"] for t in top_tweets]
            })
            chart_type = "bar"
    
    elif selected_query == "Q13 — Top 10 hashtags populaires":
        pipeline = [
            {"$unwind": "$hashtags"},
            {"$group": {"_id": "$hashtags", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        tags_result = list(db.tweets.aggregate(pipeline))
        result_text = "Top 10 hashtags par frequence d'apparition :"
        if tags_result:
            chart_data = pd.DataFrame(tags_result)
            chart_data.columns = ["Hashtag", "Count"]
            chart_data["Hashtag"] = chart_data["Hashtag"].apply(lambda x: f"#{x}")
            chart_type = "bar"
            result_data = chart_data.copy()
    
    elif selected_query == "Q14 — Tweets initiateurs de discussion":
        with get_neo4j() as session:
            res = session.run("""
                MATCH (reply:Tweet)-[:REPLY_TO]->(start:Tweet)
                WHERE NOT (start)-[:REPLY_TO]->()
                RETURN DISTINCT start.tweet_id AS thread_start
            """)
            records = [dict(r) for r in res]
        result_text = f"Tweets initiant un thread (debut de discussion) : **{len(records)}**"
        if records:
            # Enrichir avec les donnees MongoDB
            start_ids = [r["thread_start"] for r in records]
            tweets_info = list(db.tweets.find(
                {"tweet_id": {"$in": start_ids}},
                {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1, "favorite_count": 1}
            ))
            if tweets_info:
                result_data = pd.DataFrame(tweets_info)
    
    elif selected_query == "Q15 — Discussion la plus longue":
        with get_neo4j() as session:
            res = session.run("""
                MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet)
                WHERE NOT (start)-[:REPLY_TO]->()
                RETURN length(path) AS depth, 
                       [n IN nodes(path) | n.tweet_id] AS thread
                ORDER BY depth DESC LIMIT 1
            """)
            record = res.single()
        if record:
            depth = record["depth"]
            thread = record["thread"]
            result_text = f"Discussion la plus longue : **{depth}** niveaux ({depth + 1} tweets)\n\nChaine : {' -> '.join(t[:8] + '...' for t in thread)}"
            # Enrichir
            tweets_info = list(db.tweets.find(
                {"tweet_id": {"$in": thread}},
                {"_id": 0, "tweet_id": 1, "text": 1, "user_id": 1}
            ))
            if tweets_info:
                result_data = pd.DataFrame(tweets_info)
        else:
            result_text = "Aucune discussion trouvee."
    
    elif selected_query == "Q16 — Debut et fin de chaque conversation":
        with get_neo4j() as session:
            res = session.run("""
                MATCH path = (end:Tweet)-[:REPLY_TO*]->(start:Tweet)
                WHERE NOT (start)-[:REPLY_TO]->() AND NOT ()-[:REPLY_TO]->(end)
                RETURN start.tweet_id AS debut, end.tweet_id AS fin, length(path) AS longueur
                ORDER BY longueur DESC
            """)
            records = [dict(r) for r in res]
        result_text = f"Conversations identifiees : **{len(records)}**"
        if records:
            result_data = pd.DataFrame(records)
    
    # ═══ AFFICHAGE RESULTAT + GRAPH ═══
    
    st.markdown(result_text)
    
    # Tableau de resultats
    if result_data is not None and not result_data.empty:
        st.dataframe(result_data, use_container_width=True, hide_index=True)
    
    # Graphique
    if chart_data is not None and not chart_data.empty and chart_type:
        st.markdown("")
        
        if chart_type == "bar":
            fig, ax = plt.subplots(figsize=(8, 3.5))
            fig.patch.set_facecolor("#0d1117")
            ax.set_facecolor("#0d1117")
            
            col_name = chart_data.columns[0]
            val_name = chart_data.columns[1]
            
            colors_palette = ["#58a6ff", "#3fb950", "#bc8cff", "#d29922", "#f85149",
                              "#39d2c0", "#f778ba", "#58a6ff", "#3fb950", "#bc8cff"]
            
            bars = ax.barh(
                chart_data[col_name].astype(str),
                chart_data[val_name],
                color=colors_palette[:len(chart_data)],
                height=0.6,
                edgecolor="none"
            )
            
            max_val = chart_data[val_name].max()
            ax.set_xlim(0, max_val * 1.25)
            
            for bar, val in zip(bars, chart_data[val_name]):
                ax.text(bar.get_width() + max_val * 0.02, bar.get_y() + bar.get_height()/2,
                        str(int(val)), va="center", fontsize=10, color="#e6edf3", fontweight="bold")
            
            ax.tick_params(colors="#8b949e", labelsize=9)
            ax.spines[:].set_visible(False)
            ax.xaxis.set_visible(False)
            ax.invert_yaxis()
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
        
        elif chart_type == "pie":
            fig, ax = plt.subplots(figsize=(4, 4))
            fig.patch.set_facecolor("#0d1117")
            colors_palette = ["#58a6ff", "#3fb950", "#bc8cff", "#d29922", "#f85149"]
            ax.pie(
                chart_data[chart_data.columns[1]],
                labels=chart_data[chart_data.columns[0]],
                colors=colors_palette[:len(chart_data)],
                autopct="%1.0f%%",
                textprops={"color": "#e6edf3", "fontsize": 10}
            )
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)

# ═══════════════════════════════════════════
# SECTION 3 : LIVE FEED (BAS)
# ═══════════════════════════════════════════
st.divider()
st.markdown('<div class="section-title">Live Feed — derniers tweets</div>', unsafe_allow_html=True)

feed_col1, feed_col2 = st.columns([1, 1])

with feed_col1:
    st.markdown("**Derniers tweets**")
    latest = list(db.tweets.find({}, {"_id": 0}).sort("created_at", -1).limit(8))
    for t in latest:
        sentiment = t.get("sentiment_score", 0)
        incident_marker = " [INCIDENT]" if t.get("is_incident") else ""
        color = "#f85149" if sentiment < -0.3 else "#3fb950" if sentiment > 0.3 else "#d29922"
        st.markdown(f"""<div style="background:#161b22;border:1px solid #30363d;border-radius:8px;padding:10px 14px;margin-bottom:6px;border-left:3px solid {color};">
            <div style="font-size:0.8rem;color:#8b949e;">{t.get('user_id','')} | Likes: {t.get('favorite_count',0)} | Sentiment: {sentiment:.2f}{incident_marker}</div>
            <div style="font-size:0.9rem;color:#e6edf3;margin-top:4px;">{t.get('text','')[:120]}</div>
            <div style="font-size:0.75rem;color:#58a6ff;margin-top:4px;">{' '.join(f'#{h}' for h in t.get('hashtags',[]))}</div>
        </div>""", unsafe_allow_html=True)

with feed_col2:
    st.markdown("**Alertes incidents (IA)**")
    incidents = list(db.tweets.find({"is_incident": True}, {"_id": 0}).sort("created_at", -1).limit(8))
    if incidents:
        for t in incidents:
            st.markdown(f"""<div style="background:#1a0d0d;border:1px solid #f8514933;border-radius:8px;padding:10px 14px;margin-bottom:6px;border-left:3px solid #f85149;">
                <div style="font-size:0.8rem;color:#f85149;font-weight:600;">INCIDENT — Sentiment: {t.get('sentiment_score',0):.2f}</div>
                <div style="font-size:0.9rem;color:#e6edf3;margin-top:4px;">{t.get('text','')[:120]}</div>
                <div style="font-size:0.75rem;color:#8b949e;margin-top:4px;">{t.get('user_id','')} | {' '.join(f'#{h}' for h in t.get('hashtags',[]))}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.info("Aucun incident detecte.")