# test_agentic.py - Run this to test the agentic AI system

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cyberagent.settings")
django.setup()

from core.agentic_processor import run_agentic_news_analysis, get_agent_top_10
from core.models import NewsItem
from django.utils import timezone
from datetime import timedelta
import json


def test_ollama_connection():
    """Test if Ollama is responding"""
    print("\n🔍 Testing Ollama connection...")
    try:
        from ollama import Client
        client = Client(host="http://localhost:11434", timeout=10)
        response = client.chat(
            model="llama3",
            messages=[{"role": "user", "content": "Hello, respond with just 'OK'"}],
            options={"num_predict": 10}
        )
        print(f"✅ Ollama is working: {response['message']['content']}")
        return True
    except Exception as e:
        print(f"❌ Ollama connection failed: {e}")
        print("\nMake sure Ollama is running:")
        print("  1. Start Ollama: ollama serve")
        print("  2. Pull model: ollama pull llama3")
        return False


def check_news_items():
    """Check if we have news items to analyze"""
    print("\n📊 Checking database...")
    
    total = NewsItem.objects.count()
    print(f"   Total news items: {total}")
    
    last_24h = NewsItem.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    ).count()
    print(f"   Last 24 hours: {last_24h}")
    
    processed = NewsItem.objects.filter(processed_by_llm=True).count()
    print(f"   Already processed: {processed}")
    
    if total == 0:
        print("\n⚠️  No news items found. Run scraper first:")
        print("   python manage.py morning_news_update --no-clean")
        return False
    
    return True


def run_test_analysis():
    """Run a test analysis on existing data"""
    print("\n🤖 Running Agentic AI Analysis...")
    print("=" * 70)
    
    try:
        # Run analysis on last 24 hours
        result = run_agentic_news_analysis(hours=24, model="llama3")
        
        if not result['success']:
            print(f"❌ Analysis failed: {result.get('error', 'Unknown error')}")
            return False
        
        # Display results
        print("\n✅ Analysis Complete!")
        print(f"   Total analyzed: {result['total_analyzed']}")
        print(f"   Top 10 selected: {result['top_10_count']}")
        print(f"   Processing time: {result['processing_time']:.1f}s")
        
        print(f"\n🧠 Agent Reasoning:")
        print(f"   {result['agent_reasoning']}")
        
        if result.get('identified_patterns'):
            print(f"\n🔍 Identified Patterns:")
            for pattern in result['identified_patterns']:
                print(f"   • {pattern}")
        
        print(f"\n🎯 TOP 10 MOST IMPORTANT NEWS:")
        print("=" * 70)
        
        for idx, item in enumerate(result['top_10_items'], 1):
            risk_emoji = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🟢'}
            emoji = risk_emoji.get(item['risk_level'], '⚪')
            
            print(f"\n[{idx}] {emoji} {item['risk_level'].upper()} (Score: {item['risk_score']}/10)")
            print(f"    {item['title']}")
            print(f"    {item['url']}")
            print(f"    Summary: {item['summary'][:150]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("=" * 70)
    print("🧪 AGENTIC AI TEST SUITE")
    print("=" * 70)
    
    # Test 1: Ollama connection
    if not test_ollama_connection():
        print("\n❌ Please fix Ollama connection first")
        return
    
    # Test 2: Check database
    if not check_news_items():
        print("\n⚠️  Need to scrape news first")
        print("\nRun one of these:")
        print("  python manage.py morning_news_update --no-clean")
        print("  curl -X POST http://localhost:8000/api/scrape/")
        return
    
    # Test 3: Run analysis
    success = run_test_analysis()
    
    if success:
        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)
        print("\nYou can now use the API endpoints:")
        print("  POST /api/agentic-analysis/")
        print("  POST /api/scrape-and-analyze/")
        print("  GET  /api/agent-top-10/")
    else:
        print("\n" + "=" * 70)
        print("❌ TESTS FAILED")
        print("=" * 70)


if __name__ == "__main__":
    main()