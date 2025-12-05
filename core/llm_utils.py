import ollama




PRIORITY_PROMPT = """
Given a list of cybersecurity news summaries, rank them by priority (1-10, 10 being most critical). 
Prioritize based on: global impact, severity of threats, new launches, urgency (e.g., exploits vs. announcements). 
Output as a sorted list with reasons:
Summaries: {summaries}
"""
def prioritize_news(summaries):
    combined = "\n".join(summaries)
    response = ollama.generate(model='llama3', prompt=PRIORITY_PROMPT.format(summaries=combined))
    return response['response'] 



def generate_summary(text, prompt):
    response = ollama.generate(model='llama3', prompt=prompt + text)
    return response['response']

# Example prompt for summarization
SUMMARY_PROMPT = """
Summarize the following cybersecurity news article in 100-200 words. 
Focus on key updates, new launches (apps/tools/devices), impacts, and global relevance. 
Make it concise and objective:
"""

# Test
if __name__ == '__main__':
    sample_text = "Long article text here..."
    print(generate_summary(sample_text, SUMMARY_PROMPT))