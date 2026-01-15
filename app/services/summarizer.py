import os
from groq import Groq

MODEL_NAME = "llama-3.1-8b-instant"

def get_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable not set. Get free key at https://console.groq.com")
    return Groq(api_key=api_key)

def generate_summary(transcript: str, title: str) -> dict:
    """Generate summary and key takeaways from transcript."""

    client = get_client()

    prompt = f"""You are a helpful assistant that summarizes video content.

Video Title: {title}

Transcript:
{transcript[:12000]}

Please provide:
1. A concise summary of the video content (2-3 paragraphs)
2. 5-7 key takeaways as bullet points

Format your response exactly as follows:

SUMMARY:
[Your summary here]

KEY TAKEAWAYS:
- [Takeaway 1]
- [Takeaway 2]
- [Takeaway 3]
- [Takeaway 4]
- [Takeaway 5]
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{'role': 'user', 'content': prompt}],
        temperature=0.3,
        max_tokens=2000,
    )

    content = response.choices[0].message.content

    summary = ""
    takeaways = []

    if "SUMMARY:" in content and "KEY TAKEAWAYS:" in content:
        parts = content.split("KEY TAKEAWAYS:")
        summary_part = parts[0].replace("SUMMARY:", "").strip()
        takeaways_part = parts[1].strip()

        summary = summary_part

        for line in takeaways_part.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•') or (len(line) > 2 and line[0].isdigit()):
                takeaway = line.lstrip('-•0123456789.').strip()
                if takeaway:
                    takeaways.append(takeaway)
    else:
        summary = content
        takeaways = ["Summary generated - please review the content above"]

    return {
        'summary': summary,
        'key_takeaways': takeaways[:7],
    }
