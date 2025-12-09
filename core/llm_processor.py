from ollama import Client
import sqlite3

client = Client(host="http://localhost:11434")

DB_PATH = "cybernews.db"


def analyze_news_with_llm(title, content):
    prompt = f"""
You are a cybersecurity expert. Analyze the following cyber security news.

Title: {title}
Content: {content}

Tasks:
1. Provide a short summary (max 5 sentences).
2. Assess the cyber risk priority as High / Medium / Low.
3. Identify the category (Malware, Vulnerability, Ransomware, Government Alert, Cloud Security, etc.)
4. Give reasoning in 2–3 lines.

Return only JSON in this format:
{{
  "summary": "...",
  "risk": "...",
  "category": "...",
  "reason": "..."
}}
"""

    response = client.chat(model="llama3", messages=[{"role": "user", "content": prompt}])
    return response["message"]["content"]


def process_unanalyzed_news():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT id, title, content FROM news WHERE processed = 0")
    rows = cursor.fetchall()

    for news_id, title, content in rows:
        try:
            analysis_json = analyze_news_with_llm(title, content)

            cursor.execute("""
            UPDATE news 
            SET summary = ?, risk_score = ?, category = ?, processed = 1
            WHERE id = ?
            """, (
                eval(analysis_json)["summary"],
                eval(analysis_json)["risk"],
                eval(analysis_json)["category"],
                news_id
            ))

            conn.commit()
            print(f"[OK] Processed news ID: {news_id}")

        except Exception as e:
            print(f"[ERROR] {e}")

    conn.close()
