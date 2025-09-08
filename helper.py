from urlextract import URLExtract
from wordcloud import WordCloud
import pandas as pd
from collections import Counter
import emoji
import re

extract = URLExtract()

def advanced_word_filter(text, stop_words):
    """
    Advanced word filtering to remove non-meaningful words, special tokens,
    usernames, system messages, and other noise
    """
    # Convert to lowercase
    text = str(text).lower()
    
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '', text)
    
    # Remove phone numbers
    text = re.sub(r'\+?\d{10,15}', '', text)
    
    # Split into words
    words = text.split()
    
    filtered_words = []
    
    for word in words:
        word = word.strip('.,!?;:"()[]{}')
        
        # Skip if empty
        if not word:
            continue
            
        # Remove special tokens and system messages
        special_tokens = [
            '<media', 'omitted>', '<this', '<message', '<deleted>', 
            '<image', '<video', '<audio', '<document', '<sticker',
            '<gif', '<voice', '<contact', 'message', 'was', 'deleted',
            'this', 'omitted', 'note'
        ]
        if word in special_tokens:
            continue
            
        # Remove username patterns (@ mentions and parentheses)
        if '@' in word or '(' in word or ')' in word:
            continue
            
        # Remove pure numbers, symbols, or very short words
        if len(word) < 3 or word.isdigit():
            continue
            
        # Remove words that are mostly punctuation
        if sum(c.isalpha() for c in word) < len(word) * 0.5:
            continue
            
        # Remove common stop words
        if word in stop_words:
            continue
            
        # Only keep words with alphabetic characters
        if any(c.isalpha() for c in word):
            filtered_words.append(word)
    
    return filtered_words

def fetch_stats(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    # fetch the number of messages
    num_messages = df.shape[0]
    
    # fetch the total number of words (excluding media and deleted messages)
    words = []
    for message in df['message']:
        if not str(message).startswith('<') and str(message).strip():
            words.extend(str(message).split())
    
    # fetch number of media messages
    num_media_messages = df[df['message'].str.contains('<Media omitted>|media omitted|<media|omitted>', case=False, na=False)].shape[0]
    
    # fetch number of links shared
    links = []
    for message in df['message']:
        if not str(message).startswith('<'):
            links.extend(extract.find_urls(str(message)))
    
    return num_messages, len(words), num_media_messages, len(links)

def most_busy_users(df):
    df_filtered = df[df['user'] != 'group_notification']
    x = df_filtered['user'].value_counts().head()
    df_percent = round((df_filtered['user'].value_counts() / df_filtered.shape[0]) * 100, 2).reset_index()
    df_percent.columns = ['name', 'percent']
    return x, df_percent

def create_wordcloud(selected_user, df):
    try:
        with open('stop_hinglish.txt', 'r', encoding='utf-8') as f:
            stop_words = set(f.read().lower().split())
    except FileNotFoundError:
        stop_words = set(['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
    
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    # Filter out system messages and media
    temp = df[df['user'] != 'group_notification']
    temp = temp[~temp['message'].str.startswith('<', na=False)]
    temp = temp[temp['message'].str.strip() != '']
    
    if temp.empty:
        wc = WordCloud(width=500, height=500, min_font_size=10, background_color='white')
        return wc.generate("No messages available")
    
    # Advanced filtering for wordcloud
    all_words = []
    for message in temp['message']:
        filtered_words = advanced_word_filter(str(message), stop_words)
        all_words.extend(filtered_words)
    
    if not all_words:
        wc = WordCloud(width=500, height=500, min_font_size=10, background_color='white')
        return wc.generate("No meaningful words found")
    
    wc = WordCloud(width=500, height=500, min_font_size=10, background_color='white', 
                   max_words=100, relative_scaling=0.5, colormap='viridis')
    df_wc = wc.generate(' '.join(all_words))
    return df_wc

def most_common_words(selected_user, df):
    try:
        with open('stop_hinglish.txt', 'r', encoding='utf-8') as f:
            stop_words = set(f.read().lower().split())
    except FileNotFoundError:
        stop_words = set(['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'])
    
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    temp = df[df['user'] != 'group_notification']
    temp = temp[~temp['message'].str.startswith('<', na=False)]
    temp = temp[temp['message'].str.strip() != '']
    
    # Enhanced word filtering
    all_words = []
    for message in temp['message']:
        filtered_words = advanced_word_filter(str(message), stop_words)
        all_words.extend(filtered_words)
    
    if not all_words:
        return pd.DataFrame({0: ['No meaningful words'], 1: [0]})
    
    # Get most common words
    word_counts = Counter(all_words)
    most_common_df = pd.DataFrame(word_counts.most_common(20))
    
    return most_common_df

def emoji_helper(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    emojis = []
    
    # Known good emojis (you can expand this list)
    common_emojis = {
        '😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😆', '😉', '😊', '😋', '😎', '😍', '😘',
        '🥰', '😗', '😙', '😚', '☺️', '🙂', '🤗', '🤩', '🤔', '🤨', '😐', '😑', '😶', '🙄',
        '😏', '😣', '😥', '😮', '🤐', '😯', '😪', '😫', '😴', '😌', '😛', '😜', '😝', '🤤',
        '😒', '😓', '😔', '😕', '🙃', '🤑', '😲', '☹️', '🙁', '😖', '😞', '😟', '😤', '😢',
        '😭', '😦', '😧', '😨', '😩', '🤯', '😬', '😰', '😱', '🥵', '🥶', '😳', '🤪', '😵',
        '🥴', '😠', '😡', '🤬', '😷', '🤒', '🤕', '🤢', '🤮', '🤧', '😇', '🥳', '🥺', '🤠',
        '🤡', '🤥', '🤫', '🤭', '🧐', '🤓', '😈', '👿', '👹', '👺', '💀', '☠️', '👻', '👽',
        '👾', '🤖', '🎃', '😺', '😸', '😹', '😻', '😼', '😽', '🙀', '😿', '😾', '❤️', '🧡',
        '💛', '💚', '💙', '💜', '🤎', '🖤', '🤍', '💔', '❣️', '💕', '💞', '💓', '💗', '💖',
        '💘', '💝', '💟', '♥️', '💯', '💢', '💥', '💫', '💦', '💨', '🕳️', '💬', '👁️‍🗨️',
        '🗨️', '🗯️', '💭', '💤', '👋', '🤚', '🖐️', '✋', '🖖', '👌', '🤌', '🤏', '✌️',
        '🤞', '🤟', '🤘', '🤙', '👈', '👉', '👆', '🖕', '👇', '☝️', '👍', '👎', '👊',
        '✊', '🤛', '🤜', '👏', '🙌', '👐', '🤲', '🤝', '🙏', '✍️', '💅', '🤳', '💪',
        '🦾', '🦵', '🦿', '🦶', '👂', '🦻', '👃', '🧠', '🫀', '🫁', '🦷', '🦴', '👀',
        '👁️', '👅', '👄', '💋', '🩸'
    }
    
    for message in df['message']:
        if not str(message).startswith('<'):
            message_text = str(message)
            
            # Method 1: Use regex to find emoji patterns
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002702-\U000027B0"  # dingbats
                "\U000024C2-\U0001F251"
                "]+", 
                flags=re.UNICODE
            )
            
            found_emojis = emoji_pattern.findall(message_text)
            
            # Method 2: Use emoji library as backup
            try:
                emoji_list = emoji.distinct_emoji_list(message_text)
                found_emojis.extend(emoji_list)
            except:
                pass
            
            # Filter and add valid emojis
            for e in found_emojis:
                if e in common_emojis or (len(e) == 1 and ord(e) > 1000):
                    emojis.append(e)
    
    if not emojis:
        return pd.DataFrame({0: ['No emojis found'], 1: [0]})
    
    # Count and return top emojis
    emoji_counts = Counter(emojis)
    top_emojis = emoji_counts.most_common(20)  # Limit to top 20
    
    emoji_df = pd.DataFrame(top_emojis)
    return emoji_df

def monthly_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    timeline = df.groupby(['year', 'month_num', 'month']).count()['message'].reset_index()
    
    time = []
    for i in range(timeline.shape[0]):
        time.append(timeline['month'][i] + "-" + str(timeline['year'][i]))
    
    timeline['time'] = time
    return timeline

def daily_timeline(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    daily_timeline = df.groupby('only_date').count()['message'].reset_index()
    return daily_timeline

def week_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    return df['day_name'].value_counts()

def month_activity_map(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    return df['month'].value_counts()

def activity_heatmap(selected_user, df):
    if selected_user != 'Overall':
        df = df[df['user'] == selected_user]
    
    user_heatmap = df.pivot_table(index='day_name', columns='period', values='message', aggfunc='count').fillna(0)
    return user_heatmap
