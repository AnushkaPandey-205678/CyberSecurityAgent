# core/agentic_processor.py - COMPREHENSIVE ANALYSIS VERSION

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from ollama import Client
import json
from django.utils import timezone
from .models import NewsItem
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from threading import Lock

logger = logging.getLogger(__name__)

def create_ollama_client():
    """Create Ollama client with generous timeouts"""
    return Client(
        host="http://localhost:11434",
        timeout=300  # 5 minutes for thorough analysis
    )


class AgenticNewsProcessor:
    """
    Comprehensive agentic AI processor focused on quality over speed
    """
    
    def __init__(self, model="llama3", max_workers=4):
        self.model = model
        self.max_workers = max_workers  # Reduced for quality
        self.conversation_lock = Lock()
        
    def _call_llm_comprehensive(self, prompt: str, system_prompt: str = None, 
                                max_tokens: int = 2000, timeout: int = 240) -> str:
        """
        Comprehensive LLM call with generous limits for thorough analysis
        """
        client = create_ollama_client()
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = client.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": 0.3,  # Balanced creativity and consistency
                    "num_predict": max_tokens,  # Generous token limit
                    "top_p": 0.95,
                    "num_ctx": 8192,  # Large context window
                    "num_thread": 4,  # More threads for quality
                    "num_gpu": 1,
                }
            )
            
            return response['message']['content'].strip()
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            return ""

    def _extract_json(self, text: str) -> dict:
        """Robust JSON extraction"""
        if not text:
            return {}
            
        try:
            # Try to extract JSON from markdown code blocks
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0]
            elif '```' in text:
                text = text.split('```')[1].split('```')[0]
            
            # Find JSON object boundaries
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            
            return json.loads(text)
        except Exception as e:
            logger.warning(f"JSON extraction failed: {e}")
            return {}

    def step1_gather_news(self, hours: int = 24, limit: int = None) -> List[NewsItem]:
        """Gather recent news - all items by default"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        news_query = NewsItem.objects.filter(
            created_at__gte=cutoff_time
        ).order_by('-created_at')
        
        if limit:
            news_query = news_query[:limit]
        
        news_items = list(news_query)
        count = len(news_items)
        logger.info(f"📥 Gathered {count} news items for comprehensive analysis")
        return news_items

    def step2_comprehensive_scoring(self, news_items: List[NewsItem]) -> List[Dict]:
        """
        Comprehensive scoring with full LLM analysis
        """
        logger.info(f"🔍 Comprehensive scoring of {len(news_items)} items...")
        
        system_prompt = """You are a cybersecurity analyst expert. Analyze each news item thoroughly and provide:
1. Importance score (1-100) based on severity, impact, and relevance
2. Threat type classification
3. Urgency level
4. Brief reasoning for your score

Consider:
- Technical severity and exploitability
- Potential business impact
- Affected user base
- Time sensitivity
- Strategic importance"""

        def comprehensive_score(news_item: NewsItem) -> Dict:
            """Thorough scoring with full context"""
            
            prompt = f"""Analyze this cybersecurity news item in detail:

TITLE: {news_item.title}

FULL CONTENT:
{news_item.content if news_item.content else news_item.summary}

SOURCE: {news_item.source}
PUBLISHED: {news_item.published_date}

Provide a comprehensive analysis in JSON format:
{{
    "importance_score": <1-100>,
    "threat_type": "<vulnerability/breach/malware/attack/advisory/other>",
    "urgency": "<critical/high/medium/low>",
    "reasoning": "<detailed explanation of score>",
    "key_concerns": ["<concern1>", "<concern2>"],
    "affected_systems": ["<system1>", "<system2>"],
    "severity_factors": {{
        "technical_severity": <1-10>,
        "business_impact": <1-10>,
        "time_sensitivity": <1-10>
    }}
}}"""

            response = self._call_llm_comprehensive(
                prompt, 
                system_prompt, 
                max_tokens=1500,
                timeout=180
            )
            
            analysis = self._extract_json(response)
            
            # Fallback to keyword scoring if LLM fails
            if not analysis or 'importance_score' not in analysis:
                logger.warning(f"LLM analysis failed for: {news_item.title[:50]}")
                keyword_score = self._keyword_score(news_item.title, news_item.summary)
                analysis = {
                    'importance_score': keyword_score,
                    'threat_type': 'unknown',
                    'urgency': 'medium',
                    'reasoning': 'Fallback analysis - LLM failed'
                }
            
            return {
                'news_item': news_item,
                'analysis': analysis
            }

        # Process with controlled parallelism for quality
        scored_items = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(comprehensive_score, item) for item in news_items]
            
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=240)  # 4 minutes per item
                    scored_items.append(result)
                    score = result['analysis']['importance_score']
                    logger.info(f"  ✅ [{idx}/{len(news_items)}] Score: {score} - {result['news_item'].title[:60]}")
                except Exception as e:
                    logger.error(f"Scoring failed for item {idx}: {e}")
        
        return scored_items

    def _keyword_score(self, title: str, summary: str) -> int:
        """Fallback keyword scoring"""
        text = (title + " " + summary).lower()
        
        critical_kw = ['zero-day', 'critical vulnerability', '0-day', 'ransomware attack', 
                       'data breach', 'supply chain attack', 'active exploit', 'rce']
        high_kw = ['vulnerability', 'exploit', 'malware', 'attack', 'breach', 'hack', 
                   'compromised', 'infected', 'backdoor']
        medium_kw = ['patch', 'update', 'security', 'threat', 'warning', 'advisory', 'flaw']
        low_kw = ['report', 'study', 'analysis', 'research', 'opinion', 'announcement']
        
        if any(kw in text for kw in critical_kw):
            return 90
        elif any(kw in text for kw in high_kw):
            return 75
        elif any(kw in text for kw in medium_kw):
            return 55
        elif any(kw in text for kw in low_kw):
            return 30
        return 50

    def step3_intelligent_selection(self, scored_items: List[Dict], top_n: int = 10) -> Dict:
        """Intelligent top N selection with LLM reasoning"""
        logger.info(f"🎯 Selecting top {top_n} items with AI reasoning...")
        
        # Sort by score
        sorted_items = sorted(
            scored_items,
            key=lambda x: x['analysis']['importance_score'],
            reverse=True
        )[:top_n]
        
        # Generate selection summary
        selection_context = "\n\n".join([
            f"{i+1}. [{item['analysis']['importance_score']}] {item['news_item'].title}\n   Threat: {item['analysis'].get('threat_type', 'unknown')}"
            for i, item in enumerate(sorted_items)
        ])
        
        system_prompt = "You are a cybersecurity strategist. Explain the selection rationale."
        prompt = f"""These are the top {top_n} cybersecurity news items selected:

{selection_context}

Provide a strategic summary:
1. Overall threat landscape assessment
2. Key patterns and trends identified
3. Priority recommendations

Keep response concise but insightful."""

        reasoning = self._call_llm_comprehensive(prompt, system_prompt, max_tokens=800)
        
        return {
            'selected_items': sorted_items,
            'reasoning': reasoning if reasoning else "Top items selected by importance score",
            'patterns': self._identify_patterns(sorted_items)
        }

    def _identify_patterns(self, items: List[Dict]) -> List[str]:
        """Identify patterns in selected items"""
        patterns = {}
        for item in items:
            threat = item['analysis'].get('threat_type', 'unknown')
            patterns[threat] = patterns.get(threat, 0) + 1
        
        return [f"{count}x {threat}" for threat, count in patterns.items()]

    def step4_comprehensive_deep_analysis(self, priority_decision: Dict) -> List[Dict]:
        """
        COMPREHENSIVE deep analysis - thorough summaries covering everything
        """
        logger.info("🔬 Comprehensive deep analysis starting...")
        
        selected_items = priority_decision['selected_items']
        
        system_prompt = """You are an expert cybersecurity analyst creating comprehensive threat intelligence reports.

For each news item, provide:
1. COMPLETE summary covering ALL important details
2. Technical analysis of the threat/vulnerability
3. Business impact assessment
4. Affected systems and users
5. Recommended actions (immediate and long-term)
6. Risk assessment with clear reasoning

Be thorough - quality and completeness are more important than brevity."""

        def thorough_deep_analysis(item_data: Dict) -> Dict:
            """Comprehensive deep analysis"""
            news_item = item_data['news_item']
            initial_analysis = item_data['analysis']
            
            prompt = f"""Conduct a comprehensive analysis of this cybersecurity news:

TITLE: {news_item.title}

FULL CONTENT:
{news_item.content if news_item.content else news_item.summary}

SOURCE: {news_item.source}
URL: {news_item.url}
PUBLISHED: {news_item.published_date}

INITIAL ASSESSMENT:
- Importance Score: {initial_analysis.get('importance_score')}
- Threat Type: {initial_analysis.get('threat_type')}
- Urgency: {initial_analysis.get('urgency')}
- Reasoning: {initial_analysis.get('reasoning', 'N/A')}

Provide a COMPREHENSIVE analysis in JSON format:
{{
    "executive_summary": "<3-4 sentence overview covering key points>",
    "detailed_summary": "<thorough 2-3 paragraph summary covering ALL important details>",
    "technical_details": "<technical analysis of the vulnerability/threat/incident>",
    "affected_systems": ["<specific systems, software, or platforms affected>"],
    "affected_users": "<who is impacted and how>",
    "business_impact": "<potential business consequences>",
    "risk_assessment": {{
        "risk_level": "<critical/high/medium/low>",
        "risk_score": <1-10>,
        "likelihood": "<high/medium/low>",
        "impact": "<severe/moderate/minor>",
        "reasoning": "<detailed risk rationale>"
    }},
    "immediate_actions": ["<action1>", "<action2>", "<action3>"],
    "long_term_recommendations": ["<recommendation1>", "<recommendation2>"],
    "indicators_of_compromise": ["<IoC1 if applicable>"],
    "references": ["<additional resources>"]
}}

Take your time to be thorough and accurate."""

            logger.info(f"  🔍 Analyzing: {news_item.title[:80]}...")
            
            response = self._call_llm_comprehensive(
                prompt, 
                system_prompt, 
                max_tokens=2500,  # Very generous for comprehensive output
                timeout=300  # 5 minutes
            )
            
            analysis = self._extract_json(response)
            
            # Ensure we have basic structure even if parsing fails
            if not analysis:
                analysis = {
                    'executive_summary': f"Analysis of: {news_item.title}",
                    'detailed_summary': news_item.summary or news_item.content[:500],
                    'risk_assessment': {
                        'risk_level': initial_analysis.get('urgency', 'medium'),
                        'risk_score': initial_analysis.get('importance_score', 50) // 10
                    }
                }
            
            return {
                'news_item': news_item,
                'deep_analysis': analysis
            }
        
        # Process with quality-focused parallelism
        deep_analyzed = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(thorough_deep_analysis, item) for item in selected_items]
            
            for idx, future in enumerate(as_completed(futures), 1):
                try:
                    result = future.result(timeout=360)  # 6 minutes per item
                    deep_analyzed.append(result)
                    risk = result['deep_analysis'].get('risk_assessment', {}).get('risk_level', 'unknown')
                    logger.info(f"  ✅ [{idx}/{len(selected_items)}] {risk.upper()} - Complete")
                except Exception as e:
                    logger.error(f"Deep analysis failed for item {idx}: {e}")
        
        return deep_analyzed

    def step5_database_update(self, deep_analyzed: List[Dict]) -> List[NewsItem]:
        """Update database with comprehensive analysis"""
        logger.info("💾 Updating database with comprehensive analysis...")
        
        updated_items = []
        
        for item_data in deep_analyzed:
            news_item = item_data['news_item']
            deep = item_data['deep_analysis']
            risk_assessment = deep.get('risk_assessment', {})
            
            # Store comprehensive summary
            detailed_summary = deep.get('detailed_summary', '')
            executive_summary = deep.get('executive_summary', '')
            technical_details = deep.get('technical_details', '')
            
            # Combine for full summary
            full_summary = f"{executive_summary}\n\n{detailed_summary}"
            if technical_details:
                full_summary += f"\n\nTechnical Details: {technical_details}"
            
            news_item.ai_summary = full_summary[:5000]  # Store comprehensive summary
            news_item.risk_level = risk_assessment.get('risk_level', 'medium')
            news_item.risk_score = risk_assessment.get('risk_score', 5)
            
            # Store additional analysis details
            news_item.risk_reason = json.dumps({
                'affected_systems': deep.get('affected_systems', []),
                'affected_users': deep.get('affected_users', 'N/A'),
                'business_impact': deep.get('business_impact', 'N/A'),
                'immediate_actions': deep.get('immediate_actions', []),
                'long_term_recommendations': deep.get('long_term_recommendations', []),
                'risk_reasoning': risk_assessment.get('reasoning', 'N/A')
            })[:5000]  # Increased limit for comprehensive data
            
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
        Comprehensive analysis workflow - quality over speed
        
        Args:
            hours: Hours to look back for news
            limit: Maximum number of items to analyze (None = all)
            top_n: Number of top items to select for deep analysis
        """
        logger.info("🎯 Starting COMPREHENSIVE Agentic Analysis")
        logger.info(f"📊 {self.max_workers} parallel workers | Quality-focused")
        logger.info("⏱️  Taking as much time as needed for thorough analysis")
        logger.info("=" * 70)
        
        start_time = timezone.now()
        
        try:
            # Step 1 - Gather all relevant news
            news_items = self.step1_gather_news(hours, limit)
            if not news_items:
                return {'success': False, 'message': 'No news items found', 'top_items': []}
            
            # Step 2 - Comprehensive scoring
            scored_items = self.step2_comprehensive_scoring(news_items)
            if not scored_items:
                return {'success': False, 'message': 'Scoring failed', 'top_items': []}
            
            # Step 3 - Intelligent selection
            priority_decision = self.step3_intelligent_selection(scored_items, top_n)
            
            # Step 4 - Comprehensive deep analysis
            deep_analyzed = self.step4_comprehensive_deep_analysis(priority_decision)
            
            # Step 5 - Database update
            updated_items = self.step5_database_update(deep_analyzed)
            
            elapsed = (timezone.now() - start_time).total_seconds()
            
            logger.info("=" * 70)
            logger.info(f"✅ ANALYSIS COMPLETE")
            logger.info(f"⏱️  Total time: {elapsed:.1f}s ({elapsed/60:.1f} minutes)")
            logger.info(f"📊 Analyzed {len(news_items)} items, selected top {len(updated_items)}")
            
            return {
                'success': True,
                'total_analyzed': len(news_items),
                'top_items_count': len(updated_items),
                'agent_reasoning': priority_decision['reasoning'],
                'identified_patterns': priority_decision['patterns'],
                'top_items': [
                    {
                        'id': item.id,
                        'title': item.title,
                        'risk_level': item.risk_level,
                        'risk_score': item.risk_score,
                        'url': item.url,
                        'summary': item.ai_summary,
                        'published': str(item.published_date)
                    }
                    for item in updated_items
                ],
                'processing_time_seconds': elapsed,
                'processing_time_minutes': elapsed / 60,
                'parallel_workers': self.max_workers
            }
            
        except Exception as e:
            logger.exception("Comprehensive analysis failed")
            return {'success': False, 'error': str(e), 'top_items': []}


def run_agentic_news_analysis(hours: int = 24, model: str = "llama3", 
                               max_workers: int = 4, limit: int = None,
                               top_n: int = 10) -> Dict:
    """
    Run comprehensive news analysis
    
    Args:
        hours: Hours to look back (default: 24)
        model: Ollama model to use (default: "llama3")
        max_workers: Parallel workers (default: 4, recommended 2-6)
        limit: Max items to analyze (None = all items)
        top_n: Number of top items for deep analysis (default: 10)
    
    Returns:
        Comprehensive analysis results
        
    Note: This prioritizes quality over speed. Analysis may take 
    several minutes to hours depending on the number of items.
    """
    agent = AgenticNewsProcessor(model=model, max_workers=max_workers)
    return agent.run_agentic_analysis(hours, limit, top_n)


def get_agent_top_10(limit: int = 10) -> List[NewsItem]:
    """Get agent's top 10 analyzed new items"""
    return NewsItem.objects.filter(
        processed_by_llm=True,
        priority__gte=5
    ).order_by('-risk_score', '-priority', '-created_at')[:limit]