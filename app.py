import streamlit as st
import matplotlib.pyplot as plt
import seaborn as sns
import re
from datetime import datetime

import auth
import preprocessor, helper
from ai_analyzer import AIAnalyzer
from report_generator import ReportGenerator
import database

st.set_page_config(page_title="WhatsApp Chat Analyzer", page_icon="💬", layout="wide")

# Auth
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def signup_ui():
    st.subheader("Create New Account")
    name = st.text_input("Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Sign Up"):
        if name and email and password:
            success = auth.register_user(email, password, name)
            if success: st.success("Account created! Please log in.")
            else: st.error("Email is already registered.")
        else: st.warning("Please fill all fields.")

def login_ui():
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")
    if st.button("Login"):
        if email and password:
            valid = auth.login_user(email, password)
            if valid:
                st.session_state['authenticated'] = True
                st.session_state['user_email'] = email
                st.rerun()  # rerun per docs [2][3][4]
            else: st.error("Invalid email or password.")
        else: st.warning("Please enter both email and password.")

def auth_ui():
    st.title("Welcome to WhatsApp Chat Analyzer")
    tab_login, tab_signup = st.tabs(["Login", "Signup"])
    with tab_login: login_ui()
    with tab_signup: signup_ui()

if not st.session_state['authenticated']:
    auth_ui(); st.stop()
else:
    st.sidebar.write(f"Logged in as: {st.session_state.get('user_email','')}")
    if st.sidebar.button("Logout"):
        for k in ['authenticated','user_email']:
            if k in st.session_state: del st.session_state[k]
        st.rerun()

# DB init
try:
    database.init_schema()
except Exception as e:
    st.warning(f"DB init warning: {e}")

# Navigation
section = st.sidebar.radio("Navigate", ["Analyze", "AI Insights", "My Reports", "Profile", "Help"])

# Detect format
def detect_export_format(data):
    ios_pattern = r'\[\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2}\s?(AM|PM)?\]'
    if re.search(ios_pattern, data): return 'iOS'
    android_pattern = r'\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s-\s'
    if re.search(android_pattern, data): return 'Android'
    return 'Unknown'

ai = AIAnalyzer()
rep = ReportGenerator()

# Shared upload
st.sidebar.title("💬 WhatsApp Chat Analyzer")
uploaded_file = st.sidebar.file_uploader("Choose your WhatsApp chat export file", type=['txt'],
                                         help="Export your WhatsApp chat as a .txt file from iOS or Android")
selected_user = "Overall"
df = None
detected_format = "Unknown"

if section in ["Analyze","AI Insights"] and uploaded_file is not None:
    try:
        data = uploaded_file.getvalue().decode("utf-8")
        detected_format = detect_export_format(data)
        with st.spinner("🔄 Processing your chat..."):
            df = preprocessor.preprocess(data)
        user_list = df['user'].unique().tolist()
        if 'group_notification' in user_list: user_list.remove('group_notification')
        user_list.sort(); user_list.insert(0,"Overall")
        selected_user = st.sidebar.selectbox("📊 Show analysis for:", user_list)
        if detected_format != 'Unknown': st.sidebar.success(f"📱 Detected: {detected_format}")
        else: st.sidebar.warning("⚠️ Could not detect format")
    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")

# Analyze
if section == "Analyze":
    st.header("Analyze")
    if df is None:
        st.info("👆 Upload a chat file to start analysis.")
    else:
        if st.sidebar.button("🚀 Show Analysis", type="primary"):
            num_messages, words, num_media_messages, num_links = helper.fetch_stats(selected_user, df)
            st.title("📊 WhatsApp Chat Analysis")
            st.markdown(f"**Analysis for:** `{selected_user}` | **Format:** `{detected_format}`")

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("💬 Total Messages", f"{num_messages:,}")
            c2.metric("📝 Total Words", f"{words:,}")
            c3.metric("📸 Media Shared", f"{num_media_messages:,}")
            c4.metric("🔗 Links Shared", f"{num_links:,}")

            st.markdown("---")
            charts_data = {}

            colA,colB = st.columns(2)
            with colA:
                st.subheader("📅 Monthly Timeline")
                timeline = helper.monthly_timeline(selected_user, df)
                if not timeline.empty:
                    fig, ax = plt.subplots(figsize=(10,5))
                    ax.plot(timeline['time'], timeline['message'], color='green', marker='o', linewidth=2)
                    ax.set_xlabel('Month-Year'); ax.set_ylabel('Message Count'); ax.grid(True, alpha=0.3)
                    plt.xticks(rotation=45); plt.tight_layout(); st.pyplot(fig)
                    charts_data["timeline"] = timeline
                else: st.info("No timeline data available")
            with colB:
                st.subheader("📆 Daily Timeline")
                daily = helper.daily_timeline(selected_user, df)
                if not daily.empty:
                    fig, ax = plt.subplots(figsize=(10,5))
                    ax.plot(daily['only_date'], daily['message'], color='black', alpha=0.7, linewidth=1)
                    ax.set_xlabel('Date'); ax.set_ylabel('Message Count'); ax.grid(True, alpha=0.3)
                    plt.xticks(rotation=45); plt.tight_layout(); st.pyplot(fig)
                else: st.info("No daily timeline data available")

            st.markdown("---")
            st.subheader("📈 Activity Patterns")
            colC,colD = st.columns(2)
            with colC:
                st.write("**Most Busy Day**")
                busy_day = helper.week_activity_map(selected_user, df)
                if not busy_day.empty:
                    fig, ax = plt.subplots(figsize=(8,6))
                    bars = ax.bar(busy_day.index, busy_day.values, color='purple', alpha=0.8)
                    ax.set_xlabel('Day of Week'); ax.set_ylabel('Message Count'); ax.grid(True, alpha=0.3)
                    for b in bars: ax.text(b.get_x()+b.get_width()/2., b.get_height(), f'{int(b.get_height())}', ha='center', va='bottom')
                    plt.xticks(rotation=45); plt.tight_layout(); st.pyplot(fig)
                else: st.info("No activity data available")
            with colD:
                st.write("**Most Busy Month**")
                busy_month = helper.month_activity_map(selected_user, df)
                if not busy_month.empty:
                    fig, ax = plt.subplots(figsize=(8,6))
                    bars = ax.bar(busy_month.index, busy_month.values, color='orange', alpha=0.8)
                    ax.set_xlabel('Month'); ax.set_ylabel('Message Count'); ax.grid(True, alpha=0.3)
                    for b in bars: ax.text(b.get_x()+b.get_width()/2., b.get_height(), f'{int(b.get_height())}', ha='center', va='bottom')
                    plt.xticks(rotation=45); plt.tight_layout(); st.pyplot(fig)
                else: st.info("No monthly activity data available")

            st.markdown("---")
            st.subheader("🔥 Weekly Activity Heatmap")
            heat = helper.activity_heatmap(selected_user, df)
            if not heat.empty:
                fig, ax = plt.subplots(figsize=(12,6))
                sns.heatmap(heat, cmap='YlOrRd', ax=ax, annot=True, fmt='.0f', cbar_kws={'label':'Message Count'})
                ax.set_xlabel('Time Period (Hour)'); ax.set_ylabel('Day of Week'); ax.set_title('Message Activity Throughout the Week')
                plt.tight_layout(); st.pyplot(fig)
            else: st.info("No heatmap data available")

            if selected_user == 'Overall':
                st.markdown("---")
                st.subheader("👥 Most Active Users")
                x, new_df = helper.most_busy_users(df)
                if not x.empty:
                    charts_data["user_activity"] = x
                    cx, cy = st.columns(2)
                    with cx:
                        st.write("**Message Count by User**")
                        fig, ax = plt.subplots(figsize=(8,6))
                        bars = ax.bar(range(len(x)), x.values, color='red', alpha=0.8)
                        ax.set_xlabel('Users'); ax.set_ylabel('Message Count')
                        ax.set_xticks(range(len(x))); ax.set_xticklabels(x.index, rotation=45, ha='right')
                        ax.grid(True, alpha=0.3)
                        for b in bars: ax.text(b.get_x()+b.get_width()/2., b.get_height(), f'{int(b.get_height())}', ha='center', va='bottom')
                        plt.tight_layout(); st.pyplot(fig)
                    with cy:
                        st.write("**User Activity Percentage**"); st.dataframe(new_df, use_container_width=True)

            st.markdown("---")
            colW, colZ = st.columns(2)
            with colW:
                st.subheader("☁️ Word Cloud")
                try:
                    df_wc = helper.create_wordcloud(selected_user, df)
                    fig, ax = plt.subplots(figsize=(8,6)); ax.imshow(df_wc, interpolation='bilinear')
                    ax.axis("off"); ax.set_title('Most Frequently Used Words', fontsize=14, fontweight='bold', pad=20)
                    st.pyplot(fig)
                except Exception as e: st.error(f"Could not generate word cloud: {str(e)}")
            with colZ:
                st.subheader("📝 Most Common Words")
                mdf = helper.most_common_words(selected_user, df)
                if not mdf.empty and len(mdf.columns) >= 2:
                    charts_data["word_analysis"] = mdf
                    top_words = mdf.iloc[:, :2].copy()
                    top_words.columns = ["word","count"]
                    top_words = top_words.head(15)
                    fig, ax = plt.subplots(figsize=(8,8))
                    bars = ax.barh(top_words["word"].astype(str), top_words["count"].astype(float),                 color='skyblue', alpha=0.8)
                    ax.set_xlabel('Frequency'); ax.set_ylabel('Words'); ax.set_title('Top 15 Most Common Words')
                    ax.grid(True, alpha=0.3)
                    for bar in bars:
                        width = bar.get_width()
                        ax.text(width, bar.get_y()+bar.get_height()/2., f'{int(width)}', ha='left', va='center')
                    plt.tight_layout(); st.pyplot(fig)
                else:
                    st.info("No meaningful words found")

            st.markdown("---")
            st.subheader("😊 Emoji Analysis")
            emoji_df = helper.emoji_helper(selected_user, df)
            if not emoji_df.empty and len(emoji_df.columns) >= 2 and len(emoji_df) > 0:
                cE1, cE2 = st.columns(2)
                with cE1:
                    st.write("**Most Used Emojis**")
                    display_df = emoji_df.copy(); display_df.columns = ['Emoji','Count']
                    st.dataframe(display_df.head(15), use_container_width=True)
                with cE2:
                    st.write("**Emoji Distribution**")
                    fig, ax = plt.subplots(figsize=(8,8))
                    top_emojis = emoji_df.head(8)
                    wedges, texts, autotexts = ax.pie(top_emojis.iloc[:,1], labels=top_emojis.iloc[:,0],
                                                       autopct="%0.1f%%", startangle=90, textprops={'fontsize': 12})
                    for t in texts: t.set_fontsize(20)
                    for autot in autotexts: autot.set_color('white'); autot.set_fontweight('bold')
                    ax.set_title('Top Emojis Used', fontsize=16, fontweight='bold', pad=20)
                    st.pyplot(fig)

            # Quick Stats
            if st.sidebar.button("📈 Show Quick Stats"):
                st.subheader("📊 Quick Chat Statistics")
                q1,q2,q3 = st.columns(3)
                with q1: st.metric("📅 Date Range", f"{df['only_date'].min()} to {df['only_date'].max()}")
                with q2:
                    active_user = df[df['user']!='group_notification']['user'].value_counts().index if len(df[df['user']!='group_notification'])>0 else "N/A"
                    st.metric("🏆 Most Active User", active_user)
                with q3:
                    total_days = (df['only_date'].max() - df['only_date'].min()).days
                    avg_messages = len(df) / max(total_days, 1); st.metric("📈 Avg Messages/Day", f"{avg_messages:.1f}")

            # Downloads and Save
            analysis_data = {
                "total_messages": num_messages,
                "total_words": words,
                "media_messages": num_media_messages,
                "links_shared": num_links,
                "date_range": f"{df['only_date'].min()} to {df['only_date'].max()}",
            }
            try: analysis_data["ai_summary"] = AIAnalyzer().generate_ai_summary(df, selected_user)
            except Exception: pass

            st.markdown("---")
            d1,d2,d3 = st.columns(3)
            with d1:
                pdf_buf = rep.generate_pdf_report(analysis_data, selected_user, detected_format, charts_data)
                st.download_button("Download PDF Report", data=pdf_buf.getvalue(), file_name="whatsapp_report.pdf", mime="application/pdf")
            with d2:
                docx_buf = rep.generate_docx_report(analysis_data, selected_user, detected_format, charts_data)
                st.download_button("Download DOCX Report", data=docx_buf.getvalue(),
                                   file_name="whatsapp_report.docx",
                                   mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            with d3:
                def _sanitize_for_json(d):
                    clean = {}
                    for k,v in d.items():
                        try:
                            if hasattr(v, 'item'):
                                v = v.item()
                            if isinstance(v, (int, float, str)) or v is None:
                                clean[k] = v
                            else:
                                clean[k] = str(v)
                        except Exception:
                            clean[k] = str(v)
                    return clean
                if st.button("Save Report", type="primary"):
                    with st.spinner("Saving report..."):
                        try:
                            safe_kpis = _sanitize_for_json(analysis_data)
                            rid = database.create_report(
                                st.session_state['user_email'],
                                f"Report - {selected_user} - {datetime.now():%Y-%m-%d}",
                                safe_kpis,
                                safe_kpis.get("ai_summary"),
                            )
                            st.session_state['last_saved_report_id'] = rid
                            st.toast(f"Saved report #{rid}")
                            st.success("Report saved. Find it under 'My Reports'.")
                        except Exception as e:
                            st.error("Save failed. Please ensure the database is reachable and you are logged in.")
                            st.exception(e)

# AI Insights
elif section == "AI Insights":
    st.header("AI Insights")
    if uploaded_file is None:
        st.info("Upload a chat and return here for AI insights.")
    else:
        try:
            sent_df = ai.analyze_sentiment(df, selected_user)
            fig = ai.generate_sentiment_chart(sent_df)
            if fig: st.plotly_chart(fig, use_container_width=True)
            topics, _ = ai.extract_topics(df, selected_user, n_topics=3)
            topic_fig = ai.generate_topic_chart(topics)
            if topic_fig: st.plotly_chart(topic_fig, use_container_width=True)
            summary_text = ai.generate_ai_summary(df, selected_user)
            st.subheader("AI Summary"); st.write(summary_text)
            st.caption("Sentiment polarity ranges from -1 (negative) to +1 (positive).")
        except Exception as e: st.error(f"AI analysis error: {e}")

# My Reports
elif section == "My Reports":
    st.header("My Reports")
    try:
        rows = database.list_reports(st.session_state['user_email'])
        if not rows: st.info("No saved reports yet.")
        for r in rows:

            cX,cY,cZ = st.columns([6,2,2])
            with cX: st.write(f"#{r['id']} • {r['title']} • {r['created_at']}")
            with cY:
                if st.button(f"Open #{r['id']}", key=f"open_{r['id']}"):
                    rec = database.get_report(r['id'])
                    if rec: st.session_state['report_view'] = rec; st.rerun()
            with cZ:
                if st.button(f"Delete #{r['id']}", key=f"del_{r['id']}"):
                    ok = database.delete_report(r['id'], st.session_state['user_email'])
                    if ok: st.success(f"Deleted #{r['id']}"); st.rerun()
                    else: st.error("Delete failed")
        if 'report_view' in st.session_state:
            st.markdown("---")
            rec = st.session_state['report_view']
            st.subheader(rec['title'])
            kpis = rec['kpi_json']
            for k,v in kpis.items(): st.write(f"- {k}: {v}")
            if rec.get('summary_text'): st.markdown("**AI Summary**"); st.write(rec['summary_text'])
            pdf = rep.generate_pdf_report(kpis | {"ai_summary": rec.get("summary_text")}, rec['title'], 'N/A', {})
            st.download_button("Download PDF", data=pdf.getvalue(), file_name=f"report_{rec['id']}.pdf", mime="application/pdf")
            docx = rep.generate_docx_report(kpis | {"ai_summary": rec.get("summary_text")}, rec['title'], 'N/A', {})
            st.download_button("Download DOCX", data=docx.getvalue(), file_name=f"report_{rec['id']}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e: st.error(f"Listing failed: {e}")

# Profile
elif section == "Profile":
    st.header("Profile")
    email = st.session_state['user_email']
    st.write(f"Email: {email}")
    try:
        rep_count = database.count_reports(email)
        st.write(f"Reports saved: {rep_count}")
    except Exception:
        st.write("Reports saved: N/A")

    user = None
    try: user = database.get_user(email)
    except Exception: pass

    st.subheader("Update Profile")
    current_name = user.get('name') if user else ""
    new_name = st.text_input("Name", value=current_name or "")
    if st.button("Save Name"):
        try:
            if new_name:
                ok = database.update_user_name(email, new_name)
                if ok: st.success("Name updated"); st.rerun()
                else: st.error("Update failed")
            else:
                st.warning("Name cannot be empty")
        except Exception as e:
            st.error(f"Update error: {e}")

    st.subheader("Change Password")
    pw1 = st.text_input("New Password", type="password")
    pw2 = st.text_input("Confirm New Password", type="password")
    if st.button("Update Password"):
        if not pw1:
            st.warning("Enter a new password")
        elif pw1 != pw2:
            st.warning("Passwords do not match")
        else:
            try:
                ok = database.change_user_password(email, pw1)
                if ok: st.success("Password updated")
                else: st.error("Password update failed")
            except Exception as e:
                st.error(f"Password update error: {e}")

# Help
else:
    st.header("Help")
    st.markdown("- Export WhatsApp chats as .txt without media.")
    st.markdown("- Use Analyze for charts; AI Insights for sentiment/topics.")
    st.markdown("- Save reports, then find them under My Reports.")
