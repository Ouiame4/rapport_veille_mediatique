import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# -------- Fonction de vérification du login --------
def check_login(username, password):
    return username == "admin" and password == "admin"

# -------- Gestion de session --------
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'data_uploaded' not in st.session_state:
    st.session_state.data_uploaded = False

# -------- Page 1 : Login --------
if not st.session_state.logged_in:
    st.title("🔐 Interface de connexion")

    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")

    if st.button("Se connecter"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.success("Connexion réussie !")
        else:
            st.error("Identifiants incorrects. Veuillez réessayer.")

# -------- Page 2 : Upload CSV --------
elif not st.session_state.data_uploaded:
    st.title("📁 Sélection du fichier CSV ")

    uploaded_file = st.file_uploader("Téléversez votre fichier CSV", type=["csv"])

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.session_state.df = df
        st.session_state.data_uploaded = True
        st.success("Fichier chargé avec succès !")

# -------- Page 3 : Rapport --------
else:
    st.title("📊 Rapport de Veille Médiatique ")

    df = st.session_state.df
    df['articleCreatedDate'] = pd.to_datetime(df['articleCreatedDate'], errors='coerce')
    df['sentimentHumanReadable'] = df['sentimentHumanReadable'].astype(str).str.strip().str.lower()

    desired_order = ['strongly positive', 'positive', 'neutral', 'negative', 'strongly negative']
    palette_custom = ["#81C3D7", "#219ebc", "#D9DCD6", "#2F6690", "#16425B"]

    # -------- Filtres --------
    df['Year'] = df['articleCreatedDate'].dt.year
    years_available = sorted(df['Year'].dropna().unique())
    min_year = int(min(years_available))
    max_year = int(max(years_available))

    selected_year_range = st.sidebar.slider(
        "Sélectionnez l'intervalle d'années :",
        min_value=min_year,
        max_value=max_year,
        value=(min_year, max_year),
        step=1
    )

    authors = df['authorName'].dropna().unique().tolist()
    selected_authors = st.sidebar.multiselect(
        "Sélectionnez les auteurs / sources :",
        options=authors,
        default=authors
    )

    # Application des filtres
    df_filtered = df[
        (df['Year'] >= selected_year_range[0]) &
        (df['Year'] <= selected_year_range[1]) &
        (df['authorName'].isin(selected_authors))
    ]

    # ---------- KPIs ----------
    st.header("Indicateurs Clés (KPIs)")

    positive = df_filtered[df_filtered['sentimentHumanReadable'] == 'positive'].shape[0]
    negative = df_filtered[df_filtered['sentimentHumanReadable'] == 'negative'].shape[0]
    neutral = df_filtered[df_filtered['sentimentHumanReadable'] == 'neutral'].shape[0]
    total_mentions = df_filtered.shape[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Mentions totales", total_mentions)
    col2.metric("Positives", positive)
    col3.metric("Négatives", negative)
    col4.metric("Neutres", neutral)

    # ---------- Granularité ----------
    st.subheader("Choisissez la granularité temporelle")

    granularity = st.selectbox(
        "Granularité d'analyse du volume de mentions :",
        ("Par jour", "Par semaine", "Par mois", "Par année")
    )

    if granularity == "Par jour":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.date
    elif granularity == "Par semaine":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('W')
    elif granularity == "Par mois":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('M')
    elif granularity == "Par année":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('Y')

    mentions_over_time = df_filtered['Period'].value_counts().sort_index()

    fig1, ax1 = plt.subplots(figsize=(10,4))
    ax1.plot(mentions_over_time.index.astype(str), mentions_over_time.values, marker='o', linestyle='-', color="#2F6690")
    ax1.set_title(f"Évolution des mentions ({granularity.lower()})")
    plt.xticks(rotation=45)
    st.pyplot(fig1)

    # ---------- Répartition des sentiments ----------
    st.subheader("Répartition globale des sentiments")

    sentiment_counts_raw = df_filtered['sentimentHumanReadable'].value_counts()

    sentiment_counts = pd.Series(
        [sentiment_counts_raw.get(s, 0) for s in desired_order],
        index=desired_order
    )

    fig2, ax2 = plt.subplots()
    sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values, palette=palette_custom, ax=ax2)

    ax2.set_ylabel("Nombre d'articles")
    ax2.set_xlabel("Sentiment")
    ax2.set_title("Répartition globale des sentiments")

    st.pyplot(fig2)

    # ---------- Répartition des sentiments pour les top auteurs ----------
    st.subheader("Répartition des sentiments pour les top auteurs")

    author_sentiment = df_filtered.groupby(['authorName', 'sentimentHumanReadable']).size().unstack(fill_value=0)
    author_sentiment['Total'] = author_sentiment.sum(axis=1)

    top_authors_sentiment = author_sentiment.sort_values(by='Total', ascending=False).head(10)
    top_authors_sentiment = top_authors_sentiment.drop(columns='Total')

    existing_sentiments = [s for s in desired_order if s in top_authors_sentiment.columns]
    top_authors_sentiment = top_authors_sentiment[existing_sentiments]

    top_authors_sentiment = top_authors_sentiment.iloc[::-1]

    fig3, ax3 = plt.subplots(figsize=(10,6))
    top_authors_sentiment.plot(
        kind='barh',
        stacked=True,
        ax=ax3,
        color=[palette_custom[desired_order.index(s)] for s in existing_sentiments]
    )
    ax3.set_xlabel("Nombre d'articles")
    ax3.set_ylabel("Auteur / Source")
    ax3.set_title("Répartition des sentiments par auteur")
    st.pyplot(fig3)

    
