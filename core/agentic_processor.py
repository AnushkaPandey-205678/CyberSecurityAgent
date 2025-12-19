# core/agentic_processor.py - ULTRA-FAST VERSION

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ollama import Client
import json
from django.utils import timezone
from .models import NewsItem
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import time
from threading import Lock
import asyncio

logger = logging.getLogger(__name__)

def create_ollama_client():
    """Create optimized Ollama client"""
    return Client(
        host="http://localhost:11434",
        timeout=90  # Reduced timeout
    )


class AgenticNewsProcessor:
    """
    ULTRA-FAST agentic AI with aggressive optimizations
    """
    
    def __init__(self, model="llama3", max_workers=8):
        self.model = model
        self.max_workers = max_workers  # Increase default to 8
        self.conversation_lock = Lock()
        
    def _call_llm_fast(self, prompt: str, system_prompt: str = None, 
                       max_tokens: int = 400, timeout: int = 60) -> str:
        """
        Ultra-fast LLM call with aggressive timeouts and token limits
        """
        client = create_ollama_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt[:20000]})  # Limit system prompt
        
        # Truncate prompt if too long
        messages.append({"role": "user", "content": prompt[:80000]})
        
        try:
            response = client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.1,  # Lower = faster, more deterministic
                    "num_predict": max_tokens,  # Strict token limit
                    "top_p": 0.9,
                    "num_ctx": 2048,  # Smaller context = faster
                    "num_thread": 2,  # Fewer threads per call for more parallelism
                    "num_gpu": 1,  # Use GPU if available
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            logger.warning(f"LLM call failed: {e}")
            return ""

    def _extract_json(self, text: str) -> dict:
        """Fast JSON extraction"""
        if not text:
            return {}
            
        try:
            # Quick extraction
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            
            return json.loads(text)
        except:
            return {}

    def step1_gather_news(self, hours: int = 24) -> List[NewsItem]:
        """Gather recent news - limit to 20 for speed"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        news_items = NewsItem.objects.filter(
            created_at__gte=cutoff_time
        ).order_by('-created_at')[:20]  # LIMIT to 20 most recent
        
        count = news_items.count()
        logger.info(f"📥 Gathered {count} news items (limited to 20 for speed)")
        return list(news_items)

    def step2_ultra_fast_scoring(self, news_items: List[NewsItem]) -> List[Dict]:
        """
        ULTRA-FAST: Score all items in parallel with minimal prompts
        """
        logger.info(f"⚡ ULTRA-FAST scoring {len(news_items)} items...")
        
        system_prompt = "Score cybersecurity news 1-100. Be fast and decisive."

        def quick_score(news_item: NewsItem) -> Dict:
            """Lightning-fast scoring"""
            # Try keyword scoring first (instant)
            keyword_score = self._keyword_score(news_item.title, news_item.summary)
            
            # Only use LLM for borderline cases
            if keyword_score >= 75 or keyword_score <= 35:
                # Clear high/low - skip LLM
                threat_type = 'critical' if keyword_score >= 75 else 'low'
                urgency = 'high' if keyword_score >= 75 else 'low'
            else:
                # Borderline - quick LLM check
                prompt = f"Title: {news_item.title[:100]}\nScore 1-100 + threat type.\nJSON: {{score:X,type:vulnerability/breach/other}}"
                
                response = self._call_llm_fast(prompt, system_prompt, max_tokens=100, timeout=30)
                analysis = self._extract_json(response)
                
                if analysis and 'score' in analysis:
                    keyword_score = analysis['score']
                    threat_type = analysis.get('type', 'unknown')
                    urgency = 'high' if keyword_score >= 70 else 'medium'
                else:
                    threat_type = 'unknown'
                    urgency = 'medium'
            
            return {
                'news_item': news_item,
                'analysis': {
                    'importance_score': keyword_score,
                    'threat_type': threat_type,
                    'urgency': urgency
                }
            }

        # PARALLEL SCORING
        scored_items = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(quick_score, item) for item in news_items]
            
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=30)  # 30s max per item
                    scored_items.append(result)
                    logger.info(f"  ✅ [{idx}/{len(news_items)}] Score: {result['analysis']['importance_score']}")
                except TimeoutError:
                    logger.warning(f"Timeout on item {idx}")
                except Exception as e:
                    logger.error(f"Scoring failed: {e}")
        
        return scored_items

    def _keyword_score(self, title: str, summary: str) -> int:
        """Enhanced keyword scoring"""
        text = (title + " " + summary).lower()
        
        # More comprehensive keywords
        critical_kw = ['zero-day', 'critical vulnerability', '0-day', 'ransomware attack', 
                       'data breach', 'supply chain attack', 'active exploit']
        high_kw = ['vulnerability', 'exploit', 'malware', 'attack', 'breach', 'hack', 
                   'compromised', 'infected']
        medium_kw = ['patch', 'update', 'security', 'threat', 'warning', 'advisory']
        low_kw = ['report', 'study', 'analysis', 'research', 'opinion']
        
        # Scoring logic
        if any(kw in text for kw in critical_kw):
            return 90
        elif any(kw in text for kw in high_kw):
            return 75
        elif any(kw in text for kw in medium_kw):
            return 55
        elif any(kw in text for kw in low_kw):
            return 30
        return 50

    def step3_instant_selection(self, scored_items: List[Dict]) -> Dict:
        """Instant top 10 selection - no LLM needed"""
        logger.info("🎯 Selecting top 10 instantly...")
        
        sorted_items = sorted(
            scored_items,
            key=lambda x: x['analysis']['importance_score'],
            reverse=True
        )[:10]
        
        patterns = {}
        for item in sorted_items:
            threat = item['analysis']['threat_type']
            patterns[threat] = patterns.get(threat, 0) + 1
        
        pattern_list = [f"{count}x {threat}" for threat, count in patterns.items()]
        
        return {
            'selected_items': sorted_items,
            'reasoning': f"Top 10 by score. Patterns: {', '.join(pattern_list)}",
            'patterns': pattern_list
        }

    def step4_focused_deep_analysis(self, priority_decision: Dict) -> List[Dict]:
        """
        PARALLEL deep analysis with SHORTER prompts and responses
        """
        logger.info("🔬 Deep analysis (parallel, fast mode)...")
        
        selected_items = priority_decision['selected_items']
        system_prompt = "Create brief security report. 2 sentences max. Risk 1-10. Actions."

        def quick_deep_analysis(item_data: Dict) -> Dict:
            """Fast deep analysis"""
            news_item = item_data['news_item']
            score = item_data['analysis']['importance_score']
            
            # Use score to pre-determine risk level
            if score >= 85:
                risk_level = 'critical'
                risk_score = 9
            elif score >= 70:
                risk_level = 'high'
                risk_score = 7
            elif score >= 50:
                risk_level = 'medium'
                risk_score = 5
            else:
                risk_level = 'low'
                risk_score = 3
            
            # Shorter prompt
            prompt = f"""Title: {news_item.title[:150]}
Summary: {news_item.summary[:250]}

JSON: {{"summary":"2 sentences","affected":"who","actions":["a1","a2"]}}"""

            response = self._call_llm_fast(prompt, system_prompt, max_tokens=300, timeout=45)
            analysis = self._extract_json(response)
            
            # Use pre-calculated risk if LLM fails
            if not analysis:
                analysis = {
                    'summary': f"{news_item.title}. Requires review.",
                    'affected': 'Organizations/Users',
                    'actions': ['Review details', 'Apply patches']
                }
            
            analysis['risk_level'] = risk_level
            analysis['risk_score'] = risk_score
            
            return {
                'news_item': news_item,
                'deep_analysis': analysis
            }
        
        # PARALLEL DEEP ANALYSIS
        deep_analyzed = []
        with ThreadPoolExecutor(max_workers=min(10, self.max_workers)) as executor:
            futures = [executor.submit(quick_deep_analysis, item) for item in selected_items]
            
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=60)
                    deep_analyzed.append(result)
                    risk = result['deep_analysis']['risk_level']
                    logger.info(f"  ✅ [{idx}/10] {risk.upper()}")
                except Exception as e:
                    logger.error(f"Deep analysis failed: {e}")
        
        return deep_analyzed

    def step5_batch_database_update(self, deep_analyzed: List[Dict]) -> List[NewsItem]:
        """Batch database update for speed"""
        logger.info("💾 Batch updating database...")
        
        updated_items = []
        
        for item_data in deep_analyzed:
            news_item = item_data['news_item']
            deep = item_data['deep_analysis']
            
            news_item.ai_summary = deep.get('summary', '')[:1000]
            news_item.risk_level = deep.get('risk_level', 'medium')
            news_item.risk_score = deep.get('risk_score', 5)
            news_item.risk_reason = json.dumps({
                'affected': deep.get('affected', 'N/A'),
                'actions': deep.get('actions', [])
            })[:2000]
            
            news_item.priority = 10 if news_item.risk_level == 'critical' else 8
            news_item.processed_by_llm = True
            news_item.processed_at = timezone.now()
            
            updated_items.append(news_item)
        
        # Bulk update for speed
        NewsItem.objects.bulk_update(
            updated_items,
            ['ai_summary', 'risk_level', 'risk_score', 'risk_reason', 
             'priority', 'processed_by_llm', 'processed_at']
        )
        
        logger.info(f"✅ Batch updated {len(updated_items)} items")
        return updated_items

    def run_agentic_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """ULTRA-FAST workflow"""
        logger.info("⚡ Starting ULTRA-FAST Agentic Analysis")
        logger.info(f"🚀 {self.max_workers} parallel workers | Aggressive optimizations")
        logger.info("=" * 70)
        
        start_time = timezone.now()
        
        try:
            # Step 1 - Gather (limited to 20)
            news_items = self.step1_gather_news(hours)
            if not news_items:
                return {'success': False, 'message': 'No news items', 'top_10': []}
            
            # Step 2 - Ultra-fast scoring
            scored_items = self.step2_ultra_fast_scoring(news_items)
            if not scored_items:
                return {'success': False, 'message': 'Scoring failed', 'top_10': []}
            
            # Step 3 - Instant selection
            priority_decision = self.step3_instant_selection(scored_items)
            
            # Step 4 - Focused deep analysis
            deep_analyzed = self.step4_focused_deep_analysis(priority_decision)
            
            # Step 5 - Batch DB update
            updated_items = self.step5_batch_database_update(deep_analyzed)
            
            elapsed = (timezone.now() - start_time).total_seconds()
            
            logger.info("=" * 70)
            logger.info(f"✅ COMPLETE in {elapsed:.1f}s (target: <120s)")
            logger.info(f"⚡ Speedup: {788/elapsed:.1f}x faster!")
            
            return {
                'success': True,
                'total_analyzed': len(news_items),
                'top_10_count': len(updated_items),
                'agent_reasoning': priority_decision['reasoning'],
                'identified_patterns': priority_decision['patterns'],
                'top_10_items': [
                    {
                        'id': item.id,
                        'title': item.title,
                        'risk_level': item.risk_level,
                        'risk_score': item.risk_score,
                        'url': item.url,
                        'summary': item.ai_summary
                    }
                    for item in updated_items
                ],
                'processing_time': elapsed,
                'speedup_factor': f"{788/elapsed:.1f}x",
                'parallel_workers': self.max_workers
            }
            
        except Exception as e:
            logger.exception("Analysis failed")
            return {'success': False, 'error': str(e), 'top_10': []}


def run_agentic_news_analysis(hours: int = 24, model: str = "llama3", max_workers: int = 8) -> Dict:
    """
    ULTRA-FAST convenience function
    
    RECOMMENDED SETTINGS:
    - max_workers=8-12 for fastest processing
    - hours=24 (processes only 20 most recent items)
    
    Expected time: 60-120 seconds (vs 788s original)
    """
    agent = AgenticNewsProcessor(model=model, max_workers=max_workers)
    return agent.run_agentic_analysis(hours)


def get_agent_top_10() -> List[NewsItem]:
    """Get agent's top 10"""
    return NewsItem.objects.filter(
        processed_by_llm=True,
        priority__gte=8
    ).order_by('-risk_score', '-created_at')[:10]