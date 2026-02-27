from textblob import TextBlob

# ---------- SENTIMENT ----------
def analyze_sentiment(text):
    polarity = TextBlob(text).sentiment.polarity

    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"


# ---------- ISSUE CLASSIFICATION ----------
def classify_issue(text):
    text = text.lower()

    if any(word in text for word in ["delay", "late", "pending"]):
        return "Payment Delay"

    if any(word in text for word in ["eligible", "eligibility", "criteria"]):
        return "Eligibility Issue"

    if any(word in text for word in ["website", "app", "server", "technical"]):
        return "Technical Issue"

    if any(word in text for word in ["good", "helpful", "excellent", "benefit"]):
        return "General Praise"

    return "Other"
