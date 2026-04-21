import re
import requests
from bs4 import BeautifulSoup
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

sia = SentimentIntensityAnalyzer()

# Memory Array for Deduplication
SEEN_NEWS_HASHES = []

# Persistent Display State (Keeps old news on screen if no new news drops)
CURRENT_DISPLAY_NEWS = {
    "GLOBAL MACRO": None,
    "INDIA MACRO": None,
    "STOCK ACTION": None,
    "RESULTS & M&A": None
}

def calculate_similarity(text1, text2):
    """Jaccard Similarity to catch duplicate headlines"""
    words1 = set(re.findall(r'\w+', text1.lower()))
    words2 = set(re.findall(r'\w+', text2.lower()))
    if not words1 or not words2: return 0.0
    return len(words1.intersection(words2)) / len(words1.union(words2))

def get_news_feed():
    global SEEN_NEWS_HASHES, CURRENT_DISPLAY_NEWS
    
    feed_clusters = [
        {
            "cat": "GLOBAL MACRO", 
            "default_sym": "GLOBE",
            "urls": [
                "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000664",
                "https://finance.yahoo.com/news/rss"
            ]
        },
        {
            "cat": "INDIA MACRO", 
            "default_sym": "INDIA",
            "urls": [
                "https://www.livemint.com/rss/economy",
                "https://economictimes.indiatimes.com/news/economy/rssfeeds/1373380680.cms"
            ]
        },
        {
            "cat": "STOCK ACTION", 
            "default_sym": "CORP",
            "urls": [
                "https://economictimes.indiatimes.com/company/rssfeeds/2146842.cms",
                "https://www.livemint.com/rss/companies"
            ]
        },
        {
            "cat": "RESULTS & M&A", 
            "default_sym": "EARN",
            "urls": [
                "https://www.moneycontrol.com/rss/results.xml",
                "https://economictimes.indiatimes.com/markets/earnings/rssfeeds/94006536.cms"
            ]
        }
    ]
    
    final_news = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/rss+xml, application/xml, text/xml'
    }
    
    now_utc = datetime.now(timezone.utc)

    for cluster in feed_clusters:
        cat = cluster["cat"]
        story_added = False
        
        for url in cluster["urls"]:
            if story_added: break 
            
            try:
                r = requests.get(url, headers=headers, timeout=4)
                soup = BeautifulSoup(r.content, 'html.parser')
                items = soup.find_all('item')
                
                for item in items[:15]: # Scan up to 15 items deep
                    title = item.title.text if item.title else ""
                    if not title: continue
                    
                    # 🎯 1. STRICT TIME FILTER (35 MINUTES)
                    pub_date_tag = item.find('pubdate') or item.find('pubDate')
                    if pub_date_tag:
                        try:
                            # Convert RSS timestamp to UTC math
                            dt = parsedate_to_datetime(pub_date_tag.text)
                            age_mins = (now_utc - dt).total_seconds() / 60
                            
                            # If older than 35 mins, completely ignore it
                            if age_mins > 35:
                                continue 
                        except:
                            pass # If timestamp is missing/broken, proceed cautiously
                    
                    # Clean Description
                    raw_desc = item.description.text if item.description else ""
                    clean_desc = BeautifulSoup(raw_desc, "html.parser").text.strip()
                    if len(clean_desc) < 15:
                        desc = f"Live market coverage regarding {title[:40]}... Impact assessment pending."
                    else:
                        desc = clean_desc[:120] + "..."
                    
                    # NLP Deduplication
                    is_duplicate = any(calculate_similarity(title, seen) > 0.45 for seen in SEEN_NEWS_HASHES)
                    
                    if not is_duplicate:
                        SEEN_NEWS_HASHES.append(title)
                        if len(SEEN_NEWS_HASHES) > 100: SEEN_NEWS_HASHES.pop(0)
                        
                        score = sia.polarity_scores(title)['compound']
                        verdict = "BULLISH" if score >= 0.05 else "BEARISH" if score <= -0.05 else "NEUTRAL"
                        
                        symbol = cluster["default_sym"]
                        if cat in ["STOCK ACTION", "RESULTS & M&A"]:
                            words = title.replace("'", "").replace(",", "").replace(":", "").split()
                            ignore = {"Q1", "Q2", "Q3", "Q4", "FY23", "FY24", "BSE", "NSE", "CEO", "PAT", "YOY", "THE", "AND"}
                            symbol = next((w for w in words if w.isupper() and len(w) > 2 and w not in ignore), cluster["default_sym"])

                        # 🎯 2. UPDATE THE PERSISTENT MEMORY
                        CURRENT_DISPLAY_NEWS[cat] = {
                            "category": cat,
                            "title": title,
                            "desc": desc,
                            "symbol": symbol,
                            "verdict": verdict
                        }
                        story_added = True
                        break # Found our fresh story, break out!
                        
            except Exception as e:
                print(f"Failed pulling from {url}: {e}")
                continue

        # 🎯 3. IF NO NEW NEWS < 35 MINS, KEEP WHAT WE ALREADY HAVE
        # If the app just booted up and we have absolutely nothing, show Standby.
        if CURRENT_DISPLAY_NEWS[cat] is None:
            CURRENT_DISPLAY_NEWS[cat] = {
                "category": cat,
                "title": f"Monitoring {cat}...",
                "desc": "Awaiting fresh alerts from global exchanges.",
                "symbol": cluster["default_sym"],
                "verdict": "NEUTRAL"
            }
            
        final_news.append(CURRENT_DISPLAY_NEWS[cat])

    return final_news