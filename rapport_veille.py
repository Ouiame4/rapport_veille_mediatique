from fastapi import FastAPI, UploadFile, File 
from fastapi.responses import HTMLResponse 
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64

app = FastAPI()

# Palette et ordre des sentiments
desired_order = ['strongly positive', 'positive', 'neutral', 'negative', 'strongly negative']
palette_custom = ["#81C3D7", "#219ebc", "#D9DCD6", "#2F6690", "#16425B"]

# Fonction pour convertir un plot matplotlib en image base64
def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches='tight')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return image_base64

@app.post("/generate-report", response_class=HTMLResponse)
async def generate_report(file: UploadFile = File(...)):
    content = await file.read()
    df = pd.read_csv(io.BytesIO(content))

    # Nettoyage et transformation
    df['articleCreatedDate'] = pd.to_datetime(df['articleCreatedDate'], errors='coerce')
    df['sentimentHumanReadable'] = df['sentimentHumanReadable'].astype(str).str.strip().str.lower()
    df['Year'] = df['articleCreatedDate'].dt.year

    # Filtres par défaut : toutes les années et tous les auteurs
    df_filtered = df.copy()

    # ---------- KPIs ----------
    total_mentions = df_filtered.shape[0]
    positive = df_filtered[df_filtered['sentimentHumanReadable'] == 'positive'].shape[0]
    negative = df_filtered[df_filtered['sentimentHumanReadable'] == 'negative'].shape[0]
    neutral = df_filtered[df_filtered['sentimentHumanReadable'] == 'neutral'].shape[0]

    # ---------- Graph 1 : Évolution des mentions ----------
    df_filtered['Period'] = df_filtered['articleCreatedDate'].dt.to_period('M')
    mentions_over_time = df_filtered['Period'].value_counts().sort_index()

    fig1, ax1 = plt.subplots(figsize=(10, 4))
    ax1.plot(mentions_over_time.index.astype(str), mentions_over_time.values, marker='o', linestyle='-', color="#2F6690")
    ax1.set_title("Évolution des mentions (par mois)")
    ax1.set_xlabel("Période")
    ax1.set_ylabel("Nombre de mentions")
    plt.xticks(rotation=45)
    img1 = fig_to_base64(fig1)

    # ---------- Graph 2 : Répartition des sentiments ----------
    sentiment_counts_raw = df_filtered['sentimentHumanReadable'].value_counts()
    sentiment_counts = pd.Series([sentiment_counts_raw.get(s, 0) for s in desired_order], index=desired_order)

    fig2, ax2 = plt.subplots()
    sns.barplot(x=sentiment_counts.index, y=sentiment_counts.values, palette=palette_custom, ax=ax2)
    ax2.set_title("Répartition globale des sentiments")
    ax2.set_xlabel("Sentiment")
    ax2.set_ylabel("Nombre d'articles")
    img2 = fig_to_base64(fig2)

    # ---------- Graph 3 : Sentiments par auteur ----------
    author_sentiment = df_filtered.groupby(['authorName', 'sentimentHumanReadable']).size().unstack(fill_value=0)
    author_sentiment['Total'] = author_sentiment.sum(axis=1)
    top_authors = author_sentiment.sort_values(by='Total', ascending=False).head(10).drop(columns='Total')

    existing_sentiments = [s for s in desired_order if s in top_authors.columns]
    top_authors = top_authors[existing_sentiments]
    top_authors = top_authors.iloc[::-1]

    fig3, ax3 = plt.subplots(figsize=(10, 6))
    top_authors.plot(kind='barh', stacked=True,
                     ax=ax3,
                     color=[palette_custom[desired_order.index(s)] for s in existing_sentiments])
    ax3.set_title("Répartition des sentiments par auteur")
    ax3.set_xlabel("Nombre d'articles")
    ax3.set_ylabel("Auteur")
    img3 = fig_to_base64(fig3)

    # ---------- Tableau Top auteurs ----------
    top_table = (
        df_filtered['authorName']
        .value_counts()
        .reset_index()
        .rename(columns={'index': 'Auteur', 'authorName': 'Mentions'})
        .head(10)
        .to_html(index=False, classes="table table-striped", border=0)
    )

    # ---------- HTML ----------
    html = f"""
    <html>
    <head>
        <title>Rapport de Veille Médiatique</title>
        <style>
            body {{ font-family: Arial; padding: 20px; }}
            h1 {{ color: #2F6690; }}
            img {{ max-width: 100%; height: auto; margin-bottom: 30px; }}
            .kpis div {{ display: inline-block; margin-right: 40px; font-size: 18px; }}
            .table {{ width: 60%; margin-top: 20px; border-collapse: collapse; }}
            .table th, .table td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            .table th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>📊 Rapport d'Analyse de Veille Médiatique</h1>

        <div class="kpis">
            <div><strong>Mentions totales:</strong> {total_mentions}</div>
            <div><strong>Positives:</strong> {positive}</div>
            <div><strong>Négatives:</strong> {negative}</div>
            <div><strong>Neutres:</strong> {neutral}</div>
        </div>

        <h2>Évolution des mentions</h2>
        <img src="data:image/png;base64,{img1}" alt="Évolution mentions" />

        <h2>Répartition globale des sentiments</h2>
        <img src="data:image/png;base64,{img2}" alt="Sentiment global" />

        <h2>Répartition des sentiments par auteur</h2>
        <img src="data:image/png;base64,{img3}" alt="Sentiment par auteur" />

        <h2>Top Auteurs / Sources</h2>
        {top_table}
    </body>
    </html>
    """

    return HTMLResponse(content=html)
