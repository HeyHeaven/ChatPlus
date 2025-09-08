import pandas as pd
import numpy as np
import re
from textblob import TextBlob
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class AIAnalyzer:
    def __init__(self, max_features: int = 2000):
        self.vectorizer = TfidfVectorizer(max_features=max_features, stop_words="english", ngram_range=(1, 2))

    def _filter_text_df(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty or "message" not in df.columns:
            return pd.DataFrame(columns=["message", "only_date"])
        mask = ~df["message"].str.contains(r"<|omitted|deleted", case=False, na=False)
        return df.loc[mask, ["message", "only_date"]].copy()

    def analyze_sentiment(self, df: pd.DataFrame, selected_user: str = "Overall") -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame(columns=["date", "avg_sentiment", "message_count"])
        if selected_user != "Overall":
            df = df[df["user"] == selected_user]
        text_df = self._filter_text_df(df)
        if text_df.empty:
            return pd.DataFrame(columns=["date", "avg_sentiment", "message_count"])
        scores, dates = [], []
        for _, row in text_df.iterrows():
            msg = str(row["message"])
            try:
                s = TextBlob(msg).sentiment.polarity  # [-1, 1] [6][7]
            except Exception:
                s = 0.0
            scores.append(s); dates.append(row["only_date"])
        sdf = pd.DataFrame({"date": dates, "sentiment": scores})
        daily = sdf.groupby("date")["sentiment"].agg(["mean", "count"]).reset_index()
        daily.columns = ["date", "avg_sentiment", "message_count"]
        return daily

    def generate_sentiment_chart(self, sentiment_df: pd.DataFrame):
        if sentiment_df is None or sentiment_df.empty:
            return None
        fig = make_subplots(rows=2, cols=1, subplot_titles=("Sentiment Over Time", "Message Volume"), vertical_spacing=0.1)
        fig.add_trace(
            go.Scatter(x=sentiment_df["date"], y=sentiment_df["avg_sentiment"], mode="lines+markers",
                       name="Sentiment Score", line=dict(color="blue", width=2), marker=dict(size=6)),
            row=1, col=1
        )
        fig.add_trace(
            go.Bar(x=sentiment_df["date"], y=sentiment_df["message_count"], name="Message Count",
                   marker_color="lightblue", opacity=0.85),
            row=2, col=1
        )
        fig.update_layout(title="AI-Powered Sentiment Analysis", height=600, showlegend=True)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Sentiment (-1 to 1)", row=1, col=1)  # [6]
        fig.update_yaxes(title_text="Message Count", row=2, col=1)
        return fig

    def extract_topics(self, df: pd.DataFrame, selected_user: str = "Overall", n_topics: int = 5):
        if df is None or df.empty:
            return None, None
        if selected_user != "Overall":
            df = df[df["user"] == selected_user]
        text_df = self._filter_text_df(df)
        texts = []
        for msg in text_df["message"]:
            t = re.sub(r"[^\w\s]", " ", str(msg).lower())
            t = re.sub(r"\s+", " ", t).strip()
            if len(t) > 10:
                texts.append(t)
        if len(texts) < 10:
            return None, None
        try:
            X = self.vectorizer.fit_transform(texts)
            n_comp = max(1, min(n_topics, X.shape))
            lda = LatentDirichletAllocation(n_components=n_comp, random_state=42, max_iter=50)
            dist = lda.fit_transform(X)
            vocab = self.vectorizer.get_feature_names_out()
            topics = []
            for comp in lda.components_:
                idx = comp.argsort()[-10:][::-1]
                topics.append([vocab[i] for i in idx])
            return topics, dist
        except Exception:
            return None, None

    def generate_topic_chart(self, topics):
        if not topics:
            return None
        fig = make_subplots(rows=1, cols=len(topics), subplot_titles=[f"Topic {i+1}" for i in range(len(topics))])
        for i, words in enumerate(topics):
            top = words[:8]
            scores = list(range(len(top), 0, -1))
            fig.add_trace(
                go.Bar(x=scores, y=top, orientation="h", name=f"Topic {i+1}"),
                row=1, col=i+1
            )
        fig.update_layout(title="AI-Discovered Conversation Topics", height=400, showlegend=False)
        return fig

    def analyze_communication_patterns(self, df: pd.DataFrame, selected_user: str = "Overall") -> dict:
        out = {}
        if df is None or df.empty:
            return out
        if selected_user != "Overall":
            df = df[df["user"] == selected_user]
        if "date" in df.columns:
            df_sorted = df.sort_values("date")
            rtimes = []
            for i in range(1, len(df_sorted)):
                if df_sorted.iloc[i]["user"] != df_sorted.iloc[i-1]["user"]:
                    diff = df_sorted.iloc[i]["date"] - df_sorted.iloc[i-1]["date"]
                    rtimes.append(diff.total_seconds()/60.0)
            if rtimes:
                out["avg_response_time"] = float(np.mean(rtimes))
                out["response_time_std"] = float(np.std(rtimes))
        mask = ~df["message"].str.contains(r"<|omitted|deleted", case=False, na=False)
        lens = [len(str(m)) for m in df.loc[mask, "message"]]
        if lens:
            out["avg_message_length"] = float(np.mean(lens))
            out["message_length_std"] = float(np.std(lens))
        if "hour" in df.columns:
            h = df.groupby("hour").size()
            if not h.empty:
                out["peak_hour"] = int(h.idxmax()); out["peak_activity"] = int(h.max())
        return out

    def generate_ai_summary(self, df: pd.DataFrame, selected_user: str = "Overall") -> str:
        if df is None or df.empty:
            return "No data available for AI summary."
        if selected_user != "Overall":
            df = df[df["user"] == selected_user]
        total = len(df); users = df["user"].nunique()
        sent = self.analyze_sentiment(df, selected_user)
        avg = float(sent["avg_sentiment"].mean()) if not sent.empty else 0.0
        topics, _ = self.extract_topics(df, selected_user, n_topics=3)
        pat = self.analyze_communication_patterns(df, selected_user)
        lines = []
        lines.append("🤖 AI-Generated Summary Report")
        lines.append("")
        lines.append("📊 Overview")
        lines.append(f"- Total Messages: {total:,}")
        lines.append(f"- Unique Participants: {users}")
        if "only_date" in df.columns:
            lines.append(f"- Analysis Period: {df['only_date'].min()} to {df['only_date'].max()}")
        lines.append("")
        lines.append("😊 Sentiment")
        label = "Positive" if avg > 0.1 else ("Neutral" if avg > -0.1 else "Negative")
        lines.append(f"- Overall Sentiment: {label} (score {avg:.3f})")
        lines.append("")
        lines.append("🎯 Topics")
        if topics:
            for i, w in enumerate(topics[:3]):
                lines.append(f"- Topic {i+1}: {', '.join(w[:5])}")
        else:
            lines.append("- Insufficient data for topics")
        lines.append("")
        lines.append("⏰ Patterns")
        if "peak_hour" in pat: lines.append(f"- Peak Hour: {pat['peak_hour']:02d}:00")
        if "avg_message_length" in pat: lines.append(f"- Avg Message Length: {pat['avg_message_length']:.0f} chars")
        if "avg_response_time" in pat: lines.append(f"- Avg Response Time: {pat['avg_response_time']:.1f} minutes")
        lines.append("")
        lines.append("💡 Insight")
        engagement = "high" if total > 1000 else ("moderate" if total > 500 else "low")
        lines.append(f"- Engagement appears {engagement}. Optimize around peak hour.")
        return "\n".join(lines)
