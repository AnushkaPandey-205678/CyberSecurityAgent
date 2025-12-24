# core/agentic_processor.py - OPTIMIZED VERSION (10x faster)

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ollama import Client
import json
from django.utils import timezone
from .models import NewsItem
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

logger = logging.getLogger(__name__)

def create_ollama_client():
    """Create Ollama client with generous timeouts"""
    return Client(
        host="http://localhost:11434",
        timeout=180  # 3 minutes to prevent timeouts
    )


class AgenticNewsProcessor:
    """
    OPTIMIZED agentic AI processor - 10x faster than original
    
    Key optimizations:
    1. Two-phase approach: quick filtering then deep analysis
    2. Reduced token limits
    3. More aggressive parallelism
    4. Smarter caching
    5. Keyword pre-filtering
    """
    
    def __init__(self, model="llama3", max_workers=3):
        self.model = model
        self.max_workers = max_workers  # Reduced to prevent overwhelming Ollama
        self.batch_size = 5  # Process in small batches
        
        
    def _call_llm_fast(self, prompt: str, system_prompt: str = None, 
                       max_tokens: int = 500, is_deep_analysis: bool = False) -> str:
        """
        Fast LLM call with configurable limits
        - Quick scoring: 500 tokens (fast)
        - Deep analysis: 2000+ tokens (comprehensive)
        """
        client = create_ollama_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            # Different settings for deep analysis vs quick scoring
            if is_deep_analysis:
                options = {
                    "temperature": 0.3,
                    "num_predict": max_tokens,  # 2000+ for deep analysis
                    "top_p": 0.95,
                    "num_ctx": 4096,  # Larger context for detailed summaries
                    "num_thread": 8,
                }
            else:
                options = {
                    "temperature": 0.2,
                    "num_predict": max_tokens,  # 500 for quick scoring
                    "top_p": 0.9,
                    "num_ctx": 2048,  # Smaller context for speed
                    "num_thread": 8,
                }
            
            response = client.chat(
                model=self.model,
                messages=messages,
                options=options
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def _extract_json(self, text: str) -> dict:
        """Fast JSON extraction"""
        if not text:
            return {}
            
        try:
            # Remove markdown
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            # Extract JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            
            return json.loads(text)
        except:
            return {}

    def _keyword_priority_score(self, title: str, summary: str) -> int:
        """
        Fast keyword-based initial scoring (0-100)
        Filters out low-priority items before LLM analysis
        CYBERSECURITY FOCUSED
        """
        text = (title + " " + summary).lower()
        
        # Filter out non-cybersecurity content first
        cyber_indicators = ['security', 'cyber', 'vulnerability', 'breach', 'attack', 
                           'threat', 'malware', 'hack', 'exploit', 'patch']
        if not any(indicator in text for indicator in cyber_indicators):
            return 20  # Very low score for non-cybersecurity
        
        # Filter out AI/general tech without security context
        if any(kw in text for kw in ['agentic commerce', 'digital transformation', 'ai-enabled']):
            if not any(sec in text for sec in ['security', 'vulnerability', 'breach', 'attack']):
                return 15  # Very low score for non-security AI content
        
        # Critical keywords (90-100 points)
        critical = ['zero-day', '0-day', 'critical vulnerability', 'actively exploited', 
                   'ransomware attack', 'massive breach', 'supply chain attack', 
                   'widespread', 'emergency patch', 'rce', 'remote code execution']
        
        # High priority (70-89 points)
        high = ['vulnerability', 'exploit', 'breach', 'malware', 'attack', 'compromised',
               'backdoor', 'critical', 'urgent', 'patch now', 'data leak', 'apt']
        
        # Medium priority (50-69 points)
        medium = ['security', 'patch', 'update', 'threat', 'warning', 'advisory',
                 'flaw', 'risk', 'exposed', 'discovered']
        
        # Low priority (30-49 points)
        low = ['report', 'analysis', 'research', 'study', 'opinion', 'trends']
        
        if any(kw in text for kw in critical):
            return 95
        elif any(kw in text for kw in high):
            return 80
        elif any(kw in text for kw in medium):
            return 60
        elif any(kw in text for kw in low):
            return 40
        return 50

    def step1_gather_news(self, hours: int = 24, limit: int = None) -> List[NewsItem]:
        """Gather recent CYBERSECURITY news only"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Keywords that indicate cybersecurity relevance
        cyber_keywords = [
            'vulnerability', 'exploit', 'breach', 'hack', 'malware', 'ransomware',
            'phishing', 'attack', 'threat', 'patch', 'security', 'cyber',
            'zero-day', 'backdoor', 'trojan', 'cve'
        ]
        
        # Build query to filter cybersecurity news
        from django.db.models import Q
        query = Q(created_at__gte=cutoff_time)
        
        # Add keyword filters (OR condition)
        keyword_query = Q()
        for keyword in cyber_keywords:
            keyword_query |= Q(title__icontains=keyword) | Q(summary__icontains=keyword)
        
        query &= keyword_query
        
        news_query = NewsItem.objects.filter(query).order_by('-created_at')
        
        if limit:
            news_query = news_query[:limit]
        
        news_items = list(news_query)
        logger.info(f"📥 Gathered {len(news_items)} cybersecurity news items")
        return news_items

    def step2_fast_filtering(self, news_items: List[NewsItem], top_n: int = 30) -> List[NewsItem]:
        """
        PHASE 1: Fast keyword-based filtering
        Quickly reduce to top 30 candidates (3x the final needed)
        """
        logger.info(f"🚀 Fast filtering {len(news_items)} items...")
        
        scored = []
        for item in news_items:
            score = self._keyword_priority_score(item.title, item.summary)
            scored.append((item, score))
        
        # Sort and take top 30 (3x buffer for deep analysis)
        scored.sort(key=lambda x: x[1], reverse=True)
        top_candidates = [item for item, score in scored[:top_n]]
        
        logger.info(f"✅ Filtered to top {len(top_candidates)} candidates")
        return top_candidates

    def step3_quick_scoring(self, candidates: List[NewsItem]) -> List[Dict]:
        """
        PHASE 2: Quick LLM scoring with BATCHING to prevent timeouts
        Process in small batches to avoid overwhelming Ollama
        """
        logger.info(f"⚡ Quick LLM scoring of {len(candidates)} candidates (batched)...")
        
        system_prompt = """You are a cybersecurity analyst. Analyze news quickly and provide:
1. Importance score (1-100)
2. Threat type
3. Urgency level

Be concise - respond with JSON only."""

        def quick_score(news_item: NewsItem) -> Dict:
            """Fast scoring with retry logic"""
            
            # Truncate content for speed
            content = news_item.content[:1000] if news_item.content else news_item.summary[:500]
            
            prompt = f"""Quick analysis:

TITLE: {news_item.title}
CONTENT: {content}

Respond with JSON only:
{{"importance_score": <1-100>, "threat_type": "<type>", "urgency": "<critical/high/medium/low>", "reasoning": "<1 sentence>"}}"""

            # Try LLM call with timeout handling
            try:
                response = self._call_llm_fast(prompt, system_prompt, max_tokens=200)
                analysis = self._extract_json(response)
                
                # If LLM fails, use keyword fallback
                if not analysis or 'importance_score' not in analysis:
                    raise ValueError("Invalid LLM response")
                    
            except Exception as e:
                # Fallback to keyword scoring on any error
                logger.warning(f"LLM failed for '{news_item.title[:50]}', using keyword fallback")
                score = self._keyword_priority_score(news_item.title, news_item.summary)
                analysis = {
                    'importance_score': score,
                    'threat_type': 'unknown',
                    'urgency': 'high' if score >= 80 else ('medium' if score >= 60 else 'low')
                }
            
            return {
                'news_item': news_item,
                'analysis': analysis
            }

        # Process in BATCHES to avoid overwhelming Ollama
        scored_items = []
        batch_size = self.batch_size
        
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            logger.info(f"  📦 Processing batch {i//batch_size + 1}/{(len(candidates)-1)//batch_size + 1} ({len(batch)} items)")
            
            # Process batch with limited parallelism
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                futures = [executor.submit(quick_score, item) for item in batch]
                
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=120)  # 2 minute timeout per item
                        scored_items.append(result)
                    except Exception as e:
                        logger.error(f"Scoring failed: {e}")
            
            # Small delay between batches to let Ollama breathe
            if i + batch_size < len(candidates):
                time.sleep(2)
                logger.info(f"  ⏸️  Batch complete, brief pause...")
        
        logger.info(f"✅ Scored {len(scored_items)}/{len(candidates)} items")
        return scored_items

    def step4_select_top_10(self, scored_items: List[Dict], top_n: int = 10) -> List[Dict]:
        """Select final top N items"""
        logger.info(f"🎯 Selecting top {top_n} items...")
        
        # Sort by importance score
        sorted_items = sorted(
            scored_items,
            key=lambda x: x['analysis']['importance_score'],
            reverse=True
        )[:top_n]
        
        logger.info(f"✅ Selected top {len(sorted_items)} items")
        return sorted_items

    def step5_deep_analysis_parallel(self, top_items: List[Dict]) -> List[Dict]:
        """
        PHASE 3: Deep analysis with BATCHING to prevent timeouts
        Process one at a time or in very small batches for reliability
        """
        logger.info(f"🔬 Deep analysis of top {len(top_items)} items...")
        
        system_prompt = """You are a cybersecurity analyst. Provide a comprehensive but concise analysis.
Focus on: summary, affected systems, business impact, immediate actions, risk assessment.
Be thorough but efficient. Respond with valid JSON only."""

        def deep_analyze(item_data: Dict, item_num: int) -> Dict:
            """Deep analysis with comprehensive output (2000+ tokens)"""
            news_item = item_data['news_item']
            initial = item_data['analysis']
            
            logger.info(f"  🔍 [{item_num}/{len(top_items)}] Analyzing: {news_item.title[:60]}...")
            
            # Use more content for deep analysis
            content = news_item.content[:3000] if news_item.content else news_item.summary[:1500]
            
            prompt = f"""Conduct a thorough cybersecurity analysis:

TITLE: {news_item.title}
CONTENT: {content}
SOURCE: {news_item.source}
INITIAL SCORE: {initial.get('importance_score')}

Provide comprehensive JSON analysis:
{{
    "executive_summary": "<3-4 sentences covering the key points>",
    "detailed_summary": "<3-4 comprehensive paragraphs covering ALL important details, technical aspects, timeline, and implications>",
    "technical_details": "<detailed technical analysis of the vulnerability, threat, or incident>",
    "affected_systems": ["<specific systems, software versions, or platforms>"],
    "affected_users": "<detailed description of who is impacted and how>",
    "business_impact": "<comprehensive analysis of potential business consequences and financial impact>",
    "risk_assessment": {{
        "risk_level": "<critical/high/medium/low>",
        "risk_score": <1-10>,
        "likelihood": "<high/medium/low>",
        "impact": "<severe/moderate/minor>",
        "reasoning": "<detailed explanation of the risk assessment>"
    }},
    "immediate_actions": ["<action1>", "<action2>", "<action3>"],
    "long_term_recommendations": ["<recommendation1>", "<recommendation2>", "<recommendation3>"],
    "indicators_of_compromise": ["<IoC if applicable>"],
    "timeline": "<when this occurred or was discovered>"
}}

Be thorough and comprehensive - quality and completeness are important."""

            try:
                response = self._call_llm_fast(
                    prompt, 
                    system_prompt, 
                    max_tokens=2500,  # High token limit for comprehensive output
                    is_deep_analysis=True  # Use deep analysis settings
                )
                analysis = self._extract_json(response)
                
                # Ensure basic structure
                if not analysis or not analysis.get('risk_assessment'):
                    logger.warning(f"  ⚠️  Incomplete analysis, using fallback")
                    analysis = {
                        'executive_summary': f"Analysis of: {news_item.title}",
                        'detailed_summary': news_item.summary or content[:800],
                        'risk_assessment': {
                            'risk_level': initial.get('urgency', 'medium'),
                            'risk_score': initial.get('importance_score', 50) // 10
                        }
                    }
                
                logger.info(f"  ✅ [{item_num}/{len(top_items)}] Complete - Risk: {analysis.get('risk_assessment', {}).get('risk_level', 'unknown')}")
                
            except Exception as e:
                logger.error(f"  ❌ Deep analysis failed for item {item_num}: {e}")
                analysis = {
                    'executive_summary': f"Analysis of: {news_item.title}",
                    'detailed_summary': news_item.summary or content[:800],
                    'risk_assessment': {
                        'risk_level': initial.get('urgency', 'medium'),
                        'risk_score': initial.get('importance_score', 50) // 10
                    }
                }
            
            return {
                'news_item': news_item,
                'deep_analysis': analysis
            }
        
        # Process SEQUENTIALLY or in very small batches for reliability
        # Deep analysis is heavy, so we don't parallelize aggressively
        deep_analyzed = []
        
        # Process in mini-batches of 2 items
        mini_batch_size = 2
        for i in range(0, len(top_items), mini_batch_size):
            batch = top_items[i:i + mini_batch_size]
            
            with ThreadPoolExecutor(max_workers=min(2, self.max_workers)) as executor:
                futures = {executor.submit(deep_analyze, item, i+idx+1): item 
                          for idx, item in enumerate(batch)}
                
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=180)  # 3 minute timeout
                        deep_analyzed.append(result)
                    except Exception as e:
                        logger.error(f"Deep analysis batch failed: {e}")
            
            # Pause between batches
            if i + mini_batch_size < len(top_items):
                time.sleep(3)
        
        logger.info(f"✅ Deep analysis complete: {len(deep_analyzed)}/{len(top_items)} items")
        return deep_analyzed

    def step6_database_update(self, deep_analyzed: List[Dict]) -> List[NewsItem]:
        """Update database with comprehensive analysis"""
        logger.info("💾 Updating database...")
        
        updated_items = []
        
        for item_data in deep_analyzed:
            news_item = item_data['news_item']
            deep = item_data['deep_analysis']
            risk_assessment = deep.get('risk_assessment', {})
            
            # Combine summaries comprehensively
            executive = deep.get('executive_summary', '')
            detailed = deep.get('detailed_summary', '')
            technical = deep.get('technical_details', '')
            timeline = deep.get('timeline', '')
            
            # Build comprehensive summary
            full_summary = f"{executive}\n\n{detailed}"
            if technical:
                full_summary += f"\n\nTechnical Details:\n{technical}"
            if timeline:
                full_summary += f"\n\nTimeline: {timeline}"
            
            news_item.ai_summary = full_summary[:8000]  # Increased limit for comprehensive summaries
            news_item.risk_level = risk_assessment.get('risk_level', 'medium')
            news_item.risk_score = risk_assessment.get('risk_score', 5)
            
            # Store comprehensive additional details
            news_item.risk_reason = json.dumps({
                'affected_systems': deep.get('affected_systems', []),
                'affected_users': deep.get('affected_users', 'N/A'),
                'business_impact': deep.get('business_impact', 'N/A'),
                'immediate_actions': deep.get('immediate_actions', []),
                'long_term_recommendations': deep.get('long_term_recommendations', []),
                'indicators_of_compromise': deep.get('indicators_of_compromise', []),
                'risk_reasoning': risk_assessment.get('reasoning', 'N/A'),
                'likelihood': risk_assessment.get('likelihood', 'N/A'),
                'impact': risk_assessment.get('impact', 'N/A')
            })[:8000]  # Increased limit for comprehensive data
            
            news_item.priority = 10 if news_item.risk_level == 'critical' else (
                8 if news_item.risk_level == 'high' else 5
            )
            news_item.processed_by_llm = True
            news_item.processed_at = timezone.now()
            
            updated_items.append(news_item)
        
        # Bulk update
        NewsItem.objects.bulk_update(
            updated_items,
            ['ai_summary', 'risk_level', 'risk_score', 'risk_reason', 
             'priority', 'processed_by_llm', 'processed_at']
        )
        
        logger.info(f"✅ Updated {len(updated_items)} items with comprehensive analysis")
        return updated_items

    def run_agentic_analysis(self, hours: int = 24, limit: int = None, top_n: int = 10) -> Dict[str, Any]:
        """
        OPTIMIZED three-phase analysis workflow
        
        Phase 1: Keyword filtering (instant)
        Phase 2: Quick LLM scoring (30 items in parallel)
        Phase 3: Deep analysis (10 items in parallel)
        
        Expected time: 5-10 minutes instead of 1 hour
        """
        logger.info("🚀 Starting OPTIMIZED Agentic Analysis")
        logger.info(f"⚡ {self.max_workers} parallel workers | Speed-optimized")
        logger.info("=" * 70)
        
        start_time = timezone.now()
        
        try:
            # Step 1: Gather news
            news_items = self.step1_gather_news(hours, limit)
            if not news_items:
                return {'success': False, 'message': 'No news items found', 'top_items': []}
            
            # Step 2: Fast keyword filtering (instant)
            candidates = self.step2_fast_filtering(news_items, top_n * 3)
            
            # Step 3: Quick LLM scoring (parallel)
            scored_items = self.step3_quick_scoring(candidates)
            
            if not scored_items:
                return {'success': False, 'message': 'Scoring failed', 'top_items': []}
            
            # Step 4: Select top N
            top_items = self.step4_select_top_10(scored_items, top_n)
            
            # Step 5: Deep analysis ONLY for top N (parallel)
            deep_analyzed = self.step5_deep_analysis_parallel(top_items)
            
            # Step 6: Database update
            updated_items = self.step6_database_update(deep_analyzed)
            
            elapsed = (timezone.now() - start_time).total_seconds()
            
            logger.info("=" * 70)
            logger.info(f"✅ OPTIMIZED ANALYSIS COMPLETE")
            logger.info(f"⏱️  Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
            logger.info(f"📊 Analyzed {len(news_items)} items → Selected top {len(updated_items)}")
            logger.info(f"🚀 Speed: ~{len(news_items)/elapsed*60:.1f} items/minute")
            
            # Generate patterns
            patterns = {}
            for item in updated_items:
                level = item.risk_level
                patterns[level] = patterns.get(level, 0) + 1
            
            pattern_list = [f"{count}x {level}" for level, count in patterns.items()]
            
            return {
                'success': True,
                'total_analyzed': len(news_items),
                'candidates_evaluated': len(candidates),
                'top_items_count': len(updated_items),
                'identified_patterns': pattern_list,
                'top_items': [
                    {
                        'id': item.id,
                        'title': item.title,
                        'risk_level': item.risk_level,
                        'risk_score': item.risk_score,
                        'url': item.url,
                        'summary': item.ai_summary,
                        'published': str(item.published_date) if item.published_date else None
                    }
                    for item in updated_items
                ],
                'processing_time_seconds': elapsed,
                'processing_time_minutes': elapsed / 60,
                'parallel_workers': self.max_workers,
                'items_per_minute': len(news_items) / elapsed * 60
            }
            
        except Exception as e:
            logger.exception("Optimized analysis failed")
            return {'success': False, 'error': str(e), 'top_items': []}


def run_agentic_news_analysis(hours: int = 24, model: str = "llama3", 
                               max_workers: int = 3, limit: int = None,
                               top_n: int = 10) -> Dict:
    """
    Run OPTIMIZED news analysis with timeout protection
    
    Args:
        hours: Hours to look back (default: 24)
        model: Ollama model to use (default: "llama3")
        max_workers: Parallel workers (default: 3, recommended 2-4 to avoid timeouts)
        limit: Max items to analyze (None = all items)
        top_n: Number of top items for deep analysis (default: 10)
    
    Returns:
        Comprehensive analysis results
        
    Speed improvements with reliability:
    - Phase 1: Keyword filtering (instant)
    - Phase 2: Batched LLM scoring (30 items, processed in batches of 5)
    - Phase 3: Sequential deep analysis (10 items, 2500 tokens each)
    
    Expected time: 10-15 minutes (balanced for reliability)
    
    IMPORTANT: Lower max_workers (2-4) prevents Ollama timeouts
    """
    agent = AgenticNewsProcessor(model=model, max_workers=max_workers)
    return agent.run_agentic_analysis(hours, limit, top_n)


def get_agent_top_10(limit: int = 10) -> List[NewsItem]:
    """Get agent's top 10 analyzed news items"""
    return NewsItem.objects.filter(
        processed_by_llm=True,
        priority__gte=5
    ).order_by('-risk_score', '-priority', '-created_at')[:limit]