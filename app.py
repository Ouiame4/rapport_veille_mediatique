import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import squarify
from collections import Counter
import re

st.set_page_config(page_title="Dashboard Veille Médiatique", layout="wide")

# --------- Upload ---------
uploaded_file = st.file_uploader("📁 Téléversez votre fichier CSV", type=["csv"])

# --------- Rapport ---------
if uploaded_file is not None:
    st.title("📊 Rapport d'Analyse de Veille Médiatique")

    df = pd.read_csv(uploaded_file)
    df['articleCreatedDate'] = pd.to_datetime(df['articleCreatedDate'], errors='coerce')
    df['sentimentHumanReadable'] = df['sentimentHumanReadable'].astype(str).str.strip().str.lower()

    # Palette et ordre de sentiments
    desired_order = ['strongly positive', 'positive', 'neutral', 'negative', 'strongly negative']
    palette_custom = ["#81C3D7", "#219ebc", "#D9DCD6", "#2F6690", "#16425B"]

    # --------- Filtres Sidebar ---------
    st.sidebar.header("🧰 Filtres")

    df['Year'] = df['articleCreatedDate'].dt.year
    years_available = sorted(df['Year'].dropna().unique())
    selected_year_range = st.sidebar.slider(
        "📅 Intervalle d'années :", 
        min_value=int(min(years_available)), 
        max_value=int(max(years_available)), 
        value=(int(min(years_available)), int(max(years_available)))
    )

    authors = df['authorName'].dropna().unique().tolist()
    selected_authors = st.sidebar.multiselect(
        "📝 Auteurs / Sources :", 
        options=authors, 
        default=authors
    )

    # Application des filtres
    df_filtered = df[
        (df['Year'] >= selected_year_range[0]) & 
        (df['Year'] <= selected_year_range[1]) & 
        (df['authorName'].isin(selected_authors))
    ]

    # --------- KPIs ---------
    st.header("📌 Indicateurs Clés")
    col1, col2, col3, col4 = st.columns(4)

    total_mentions = df_filtered.shape[0]
    positive = df_filtered[df_filtered['sentimentHumanReadable'] == 'positive'].shape[0]
    negative = df_filtered[df_filtered['sentimentHumanReadable'] == 'negative'].shape[0]
    neutral = df_filtered[df_filtered['sentimentHumanReadable'] == 'neutral'].shape[0]

    col1.metric("Mentions totales", total_mentions)
    col2.metric("Positives", positive)
    col3.metric("Négatives", negative)
    col4.metric("Neutres", neutral)

    # --------- Évolution des mentions ---------
    granularity = st.sidebar.selectbox(
        "📊 Granularité temporelle :",
        options=["Par jour", "Par semaine", "Par mois", "Par année"]
    )

    if granularity == "Par jour":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.date
    elif granularity == "Par semaine":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('W')
    elif granularity == "Par mois":
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('M')
    else:
        df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('Y')

    mentions_over_time = df_filtered['Period'].value_counts().sort_index()

    # --------- Graphique 1 ---------
    fig1, ax1 = plt.subplots(figsize=(6, 4))
    ax1.plot(mentions_over_time.index.astype(str), mentions_over_time.values, marker='o', linestyle='-', color="#2F6690")
    ax1.set_title("📈 Évolution des mentions")
    plt.xticks(rotation=45)

    # --------- Graphique 2 ---------
    sentiment_counts_raw = df_filtered['sentimentHumanReadable'].value_counts()
    sentiment_counts = pd.Series(
        [sentiment_counts_raw.get(s, 0) for s in desired_order],
        index=desired_order
    )
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values, palette=palette_custom, ax=ax2)
    ax2.set_ylabel("Nombre d'articles")
    ax2.set_xlabel("Sentiment")
    ax2.set_title("📊 Répartition des sentiments")

    # --------- Graphique 3 ---------
    author_sentiment = df_filtered.groupby(['authorName', 'sentimentHumanReadable']).size().unstack(fill_value=0)
    author_sentiment['Total'] = author_sentiment.sum(axis=1)
    top_authors_sentiment = author_sentiment.sort_values(by='Total', ascending=False).head(10).drop(columns='Total')
    existing_sentiments = [s for s in desired_order if s in top_authors_sentiment.columns]
    top_authors_sentiment = top_authors_sentiment[existing_sentiments].iloc[::-1]

    fig3, ax3 = plt.subplots(figsize=(6, 4))
    top_authors_sentiment.plot(
        kind='barh',
        stacked=True,
        ax=ax3,
        color=[palette_custom[desired_order.index(s)] for s in existing_sentiments]
    )
    ax3.set_xlabel("Nombre d'articles")
    ax3.set_ylabel("Auteur / Source")
    ax3.set_title("📚 Sentiments par auteur")

    # --------- Graphique 4 : Treemap des mots-clés ---------
    st.subheader("🧠 Analyse des mots-clés les plus fréquents (Titres)")

    all_titles = df_filtered['articleTitle'].dropna().astype(str).str.lower()
    words = re.findall(r'\b[a-z]{4,}\b', ' '.join(all_titles))  # mots >= 4 lettres
    stopwords = set([
        "avec", "pour", "dans", "les", "des", "une", "mais", "chez", "vous", "plus", "très", 
        "cette", "dont", "cela", "aussi", "être", "sont", "entre", "leurs", "comme", "tout"
    ])
    filtered_words = [word for word in words if word not in stopwords]

    word_freq = Counter(filtered_words)
    common_words = word_freq.most_common(15)

    labels = [f"{word}\n({count})" for word, count in common_words]
    sizes = [count for _, count in common_words]

    fig4, ax4 = plt.subplots(figsize=(6, 4))
    squarify.plot(sizes=sizes, label=labels, alpha=.8, color=sns.color_palette("Blues", len(sizes)))
    plt.axis('off')
    plt.title("📌 Top mots-clés dans les titres")

    # --------- Affichage 2x2 ---------
    st.subheader("📈 Visualisations")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.pyplot(fig1)
    with col_g2:
        st.pyplot(fig2)

    col_g3, col_g4 = st.columns(2)
    with col_g3:
        st.pyplot(fig3)
    with col_g4:
        st.pyplot(fig4)
