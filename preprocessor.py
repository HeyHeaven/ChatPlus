import re
import pandas as pd
from datetime import datetime

def preprocess(data):
    """
    Universal WhatsApp chat preprocessor that handles ALL export formats:
    - iOS: [08/07/24, 11:44:33 AM] username: message
    - Android: 13/01/24, 12:01 - username: message
    - Various date formats and edge cases
    """
    
    # Define all possible WhatsApp export patterns with priority order
    patterns = [
        # iOS Patterns (check first as they're more specific)
        {
            'name': 'iOS_12h_seconds',
            'pattern': r'\[(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2}\s(?:AM|PM))\]',
            'date_formats': [
                '%d/%m/%y, %I:%M:%S %p',    # [08/07/24, 11:44:33 AM]
                '%d/%m/%Y, %I:%M:%S %p',    # [08/07/2024, 11:44:33 AM]
                '%m/%d/%y, %I:%M:%S %p',    # US format [07/08/24, 11:44:33 AM]
                '%m/%d/%Y, %I:%M:%S %p',    # US format [07/08/2024, 11:44:33 AM]
            ]
        },
        {
            'name': 'iOS_24h_seconds',
            'pattern': r'\[(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2})\]',
            'date_formats': [
                '%d/%m/%y, %H:%M:%S',       # [08/07/24, 23:44:33]
                '%d/%m/%Y, %H:%M:%S',       # [08/07/2024, 23:44:33]
                '%m/%d/%y, %H:%M:%S',       # US format
                '%m/%d/%Y, %H:%M:%S',       # US format
            ]
        },
        {
            'name': 'iOS_12h_no_seconds',
            'pattern': r'\[(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}\s(?:AM|PM))\]',
            'date_formats': [
                '%d/%m/%y, %I:%M %p',       # [08/07/24, 11:44 AM]
                '%d/%m/%Y, %I:%M %p',       # [08/07/2024, 11:44 AM]
                '%m/%d/%y, %I:%M %p',       # US format
                '%m/%d/%Y, %I:%M %p',       # US format
            ]
        },
        # Android Patterns (check after iOS)
        {
            'name': 'Android_standard',
            'pattern': r'(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2})\s-\s',
            'date_formats': [
                '%d/%m/%y, %H:%M',          # 13/01/24, 12:01 - 
                '%d/%m/%Y, %H:%M',          # 13/01/2024, 12:01 -
                '%m/%d/%y, %H:%M',          # US format
                '%m/%d/%Y, %H:%M',          # US format
            ]
        },
        {
            'name': 'Android_with_seconds',
            'pattern': r'(\d{1,2}/\d{1,2}/\d{2,4},\s\d{1,2}:\d{2}:\d{2})\s-\s',
            'date_formats': [
                '%d/%m/%y, %H:%M:%S',       # 13/01/24, 12:01:30 -
                '%d/%m/%Y, %H:%M:%S',       # 13/01/2024, 12:01:30 -
            ]
        }
    ]
    
    messages = []
    dates = []
    used_pattern = None
    used_formats = []
    
    # Try each pattern until we find a working one
    for pattern_info in patterns:
        pattern = pattern_info['pattern']
        test_dates = re.findall(pattern, data)
        
        if test_dates and len(test_dates) > 3:  # Need reasonable number of messages
            print(f"✅ Detected format: {pattern_info['name']}")
            
            # Split messages using the same pattern
            split_data = re.split(pattern, data)
            
            # Extract messages (skip first empty element)
            raw_messages = []
            for i in range(2, len(split_data), 2):  # Every other element starting from index 2
                if i < len(split_data):
                    raw_messages.append(split_data[i])
            
            # Ensure we have matching dates and messages
            min_length = min(len(test_dates), len(raw_messages))
            dates = test_dates[:min_length]
            messages = raw_messages[:min_length]
            used_pattern = pattern_info['name']
            used_formats = pattern_info['date_formats']
            break
    
    if not dates:
        raise ValueError("❌ Could not detect WhatsApp chat format. Supported formats:\n"
                        "- iOS: [DD/MM/YY, HH:MM:SS AM/PM] username: message\n"
                        "- Android: DD/MM/YY, HH:MM - username: message")
    
    print(f"📱 Processing {len(dates)} messages using {used_pattern} format")
    
    # Parse dates with multiple format attempts
    def parse_date_flexible(date_str):
        date_str = date_str.strip('[]').strip()
        
        for fmt in used_formats:
            try:
                return pd.to_datetime(date_str, format=fmt)
            except:
                continue
        
        # Fallback to pandas automatic parsing
        try:
            return pd.to_datetime(date_str, dayfirst=True)
        except:
            print(f"⚠️  Failed to parse date: {date_str}")
            return pd.NaT
    
    parsed_dates = [parse_date_flexible(d) for d in dates]
    
    # Create DataFrame
    df = pd.DataFrame({
        'user_message': messages,
        'message_date': parsed_dates
    })
    
    # Remove rows with failed date parsing
    original_count = len(df)
    df = df.dropna(subset=['message_date'])
    if len(df) < original_count:
        print(f"⚠️  Removed {original_count - len(df)} messages with invalid dates")
    
    df.rename(columns={'message_date': 'date'}, inplace=True)
    
    # Extract users and messages with enhanced parsing
    users = []
    clean_messages = []
    
    system_keywords = [
        'Messages and calls are end-to-end encrypted',
        'created group',
        'added you',
        'left',
        'joined using',
        'changed the group',
        'security code changed',
        'deleted this message',
        'message was deleted',
        'media omitted',
        'sticker omitted',
        'image omitted',
        'video omitted',
        'audio omitted',
        'document omitted',
        'gif omitted'
    ]
    
    for message in df['user_message']:
        message = str(message).strip()
        
        # Check for system messages
        is_system = any(keyword.lower() in message.lower() for keyword in system_keywords)
        
        if is_system:
            users.append('group_notification')
            clean_messages.append(message)
            continue
        
        # Extract username and message content
        if ':' in message:
            parts = message.split(':', 1)
            if len(parts) == 2:
                username = parts[0].strip()
                msg_content = parts[1].strip()
                
                # Clean username
                username = re.sub(r'[\-\s]*$', '', username)
                username = re.sub(r'^[\-\s]*', '', username)
                
                # Validate username
                if (username and 
                    len(username) < 50 and 
                    not username.startswith('http') and
                    not username.isdigit() and
                    not re.match(r'^\d+/\d+/\d+', username)):
                    
                    users.append(username)
                    clean_messages.append(msg_content if msg_content else '<Empty message>')
                else:
                    users.append('group_notification')
                    clean_messages.append(message)
            else:
                users.append('group_notification')
                clean_messages.append(message)
        else:
            users.append('group_notification')
            clean_messages.append(message)
    
    # Update DataFrame
    df['user'] = users
    df['message'] = clean_messages
    df.drop(columns=['user_message'], inplace=True)
    
    # Add time-based features
    df['only_date'] = df['date'].dt.date
    df['year'] = df['date'].dt.year
    df['month_num'] = df['date'].dt.month
    df['month'] = df['date'].dt.month_name()
    df['day'] = df['date'].dt.day
    df['day_name'] = df['date'].dt.day_name()
    df['hour'] = df['date'].dt.hour
    df['minute'] = df['date'].dt.minute
    
    # Create time periods for activity heatmap
    period = []
    for hour in df['hour']:
        if hour == 23:
            period.append("23-00")
        elif hour == 0:
            period.append("00-01")
        else:
            period.append(f"{hour:02d}-{hour+1:02d}")
    
    df['period'] = period
    
    # Print summary
    unique_users = [u for u in df['user'].unique() if u != 'group_notification']
    print(f"✅ Successfully processed {len(df)} messages")
    print(f"👥 Found {len(unique_users)} unique users: {', '.join(unique_users[:5])}")
    if len(unique_users) > 5:
        print(f"    ... and {len(unique_users) - 5} more")
    
    return df
