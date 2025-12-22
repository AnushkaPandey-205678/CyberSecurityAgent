# 🤖 Cyberagent - AI-Powered Cybersecurity News Analyzer

An intelligent, agentic AI system that automatically scrapes, analyzes, and prioritizes cybersecurity news using local LLM models (via Ollama). The system provides comprehensive threat intelligence reports with risk assessments, affected systems analysis, and actionable recommendations.

## 📋 Table of Contents

- [Features](#-features)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [Usage](#-usage)
- [How It Works](#-how-it-works)
- [Scheduling](#-scheduling)
- [Troubleshooting](#-troubleshooting)

---

## ✨ Features

### Core Capabilities
- 🔍 **Automated News Scraping** - Fetches latest cybersecurity news from multiple sources
- 🧠 **AI-Powered Analysis** - Uses local LLM (Ollama) for comprehensive threat assessment
- 📊 **Intelligent Prioritization** - Scores and ranks news by importance (1-100)
- 🎯 **Top N Selection** - Identifies most critical news items (default: top 10)
- 📝 **Comprehensive Summaries** - Generates detailed reports covering:
  - Executive summaries
  - Technical analysis
  - Affected systems and users
  - Business impact assessment
  - Risk scoring (1-10)
  - Immediate actions
  - Long-term recommendations
- 🔒 **Risk Classification** - Categorizes threats as Critical/High/Medium/Low
- 💾 **Database Storage** - Persistent storage with Django ORM
- 🌐 **Web Interface** - View and filter analyzed news
- 📈 **RESTful API** - Programmatic access to analysis results
- ⚡ **Parallel Processing** - Multi-threaded analysis for efficiency
- 📅 **Flexible Timeframes** - Analyze news from any time period

---

### Workflow

1. **Scraping Phase**
   - Fetches latest cybersecurity news from configured sources
   - Extracts title, content, summary, URL, published date
   - Stores raw data in database

2. **Analysis Phase**
   - **Step 1: Gather** - Retrieves recent news items
   - **Step 2: Score** - Assigns importance scores (1-100) using LLM
   - **Step 3: Select** - Chooses top N items based on scores and patterns
   - **Step 4: Deep Analysis** - Comprehensive LLM analysis of selected items
   - **Step 5: Store** - Updates database with analysis results

3. **Presentation Phase**
   - Web interface displays prioritized news
   - API provides programmatic access
   - Risk levels and actionable insights highlighted

---

## 📦 Prerequisites

### System Requirements
- **OS**: Linux, macOS, or Windows
- **Python**: 3.8 or higher
- **RAM**: 8GB minimum (16GB recommended for larger models)
- **Disk**: 10GB free space (for Ollama models)
- **CPU/GPU**: GPU recommended but not required

### Required Software

1. **Python 3.8+**
   ```bash
   # Check version
   python3 --version
   ```

2. **Ollama** (Local LLM Runtime)
   - Download from: https://ollama.ai
   - **Linux/macOS**:
     ```bash
     curl https://ollama.ai/install.sh | sh
     ```
   - **Windows**: Download installer from website


---

## 🚀 Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/cyberagent.git
cd cyberagent
```

### Step 2: Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv myenv
source myenv/bin/activate
```

**Windows:**
```cmd
python -m venv myenv
myenv\Scripts\activate
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**requirements.txt** should contain:
```
Django>=4.2.0
djangorestframework>=3.14.0
ollama>=0.1.0
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
python-dateutil>=2.8.0
```

### Step 4: Install Ollama Model

```bash
# Start Ollama service (if not already running)
ollama serve

# Pull LLaMA 3 model (in a new terminal)
ollama pull llama3

# Or use other models:
# ollama pull mistral
# ollama pull llama3.1
```

Verify installation:
```bash
ollama list
```

### Step 5: Configure Django

```bash
# Applying Migrations
python manage.py makemigrations

# Create database
python manage.py migrate

```

### Step 6: Verify Installation

```bash
# Test Django server
python manage.py runserver

# Visit: http://localhost:8000
```

---

## 🎯 Usage

### Command Line Interface

#### Basic Analysis (Top 10 from last 24 hours)

```bash
python manage.py agentic_news_update
```

#### With Scraping

```bash
python manage.py agentic_news_update --scrape-first
```

#### Show AI Reasoning

```bash
python manage.py agentic_news_update --show-reasoning
```

#### Show Detailed Analysis

```bash
python manage.py agentic_news_update --show-details
```

#### Custom Parameters

```bash
# Analyze last 48 hours, select top 20 items
python manage.py agentic_news_update --hours 48 --top-n 20

# Limit analysis to 50 most recent items
python manage.py agentic_news_update --limit 50

# Use fewer workers (slower systems)
python manage.py agentic_news_update --workers 2

# Use different model
python manage.py agentic_news_update --model mistral

# Full comprehensive analysis
python manage.py agentic_news_update \
    --scrape-first \
    --show-reasoning \
    --show-details \
    --hours 24 \
    --top-n 10
```

### Cross-Platform Script

Use the included `run_morning_update.sh` script:

**Linux/macOS:**
```bash
chmod +x run_morning_update.sh
./run_morning_update.sh
```

### Web Interface

```bash
# Start Django server
python manage.py runserver

# Access web interface
# Browse to: http://localhost:8000
```

Features:
- View all analyzed news
- Filter by risk level
- Sort by risk score
- View detailed analysis

---

## 🔍 How It Works

### 1. News Gathering

The scraper collects news from configured sources:
- Fetches RSS feeds or scrapes HTML
- Extracts: title, content, summary, URL, date
- Stores in database with `processed_by_llm=False`

### 2. Scoring Phase

Each news item receives an importance score:

```
Score = AI Assessment considering:
  - Technical severity (vulnerability details)
  - Business impact (affected organizations)
  - Time sensitivity (active exploits)
  - Affected user base
  - Strategic importance
```

Score Range:
- **8-10**: Critical threats (zero-days, active attacks)
- **7-8**: High importance (major vulnerabilities)
- **5-6**: Medium importance (patches, advisories)
- **Below 5**: Low importance (research, opinions)

### 3. Selection Phase

AI agent selects top N items:
- Sorts by importance score
- Identifies patterns (e.g., "3x ransomware, 2x supply chain")
- Provides strategic reasoning
- Ensures diversity in threat types

### 4. Deep Analysis Phase

Selected items undergo comprehensive analysis:

**Input to LLM:**
```
TITLE: [Full title]
CONTENT: [Complete article text]
SOURCE: [Source URL]
PUBLISHED: [Date]
INITIAL SCORE: [Importance score]
```

**LLM Output:**
```json
{
  "executive_summary": "Brief overview",
  "detailed_summary": "Comprehensive 2-3 paragraph analysis",
  "technical_details": "Vulnerability specifics",
  "affected_systems": ["System A", "System B"],
  "affected_users": "Who is impacted",
  "business_impact": "Potential consequences",
  "risk_assessment": {
    "risk_level": "critical",
    "risk_score": 9,
    "reasoning": "Why this score"
  },
  "immediate_actions": ["Action 1", "Action 2"],
  "long_term_recommendations": ["Recommendation 1"]
}
```

### 5. Storage Phase

Results stored in database:
- `ai_summary`: Comprehensive summary (5000 chars)
- `risk_level`: critical/high/medium/low
- `risk_score`: 1-10
- `risk_reason`: JSON with detailed analysis
- `priority`: 10 (critical), 8 (high), 5 (medium)
- `processed_by_llm`: True
- `processed_at`: Timestamp
\
---

## ⏰ Scheduling

### Linux/macOS (Cron)

```bash
# Edit crontab
crontab -e

# Run daily at 9:00 AM
0 9 * * * cd /path/to/Cyberagent && /usr/bin/python3 run_morning_update.sh >> /path/to/logs/cron.log 2>&1

# Run every 6 hours
0 */6 * * * cd /path/to/Cyberagent && /usr/bin/python3 run_morning_update.sh

# Run twice daily (9 AM and 9 PM)
0 9,21 * * * cd /path/to/Cyberagent && /usr/bin/python3 run_morning_update.sh
```

### Windows (Task Scheduler)

1. Open **Task Scheduler**
2. Click **Create Basic Task**
3. Name: "Cyberagent Analysis"
4. Trigger: **Daily** at **9:00 AM**
5. Action: **Start a program**
   - Program: `C:\Python39\python.exe`
   - Arguments: `run_morning_update.sh`
   - Start in: `C:\path\to\cyberagent`
6. Click **Finish**

---

## 🔧 Troubleshooting

### Ollama Connection Issues

**Problem**: `Connection refused to localhost:11434`

**Solution**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/version

# Start Ollama service
ollama serve

# Check model is installed
ollama list
```

### Memory Issues

**Problem**: `Out of memory` or slow processing

**Solution**:
```bash
# Use smaller model
ollama pull llama3:8b  # Instead of 70b

# Reduce workers
python manage.py agentic_news_update --workers 2

# Limit items
python manage.py agentic_news_update --limit 20
```

### Analysis Taking Too Long

**Problem**: Analysis takes hours

**Solutions**:
1. **Limit items**: `--limit 30`
2. **Reduce workers**: `--workers 2` (less parallel = more stable)
3. **Use faster model**: `--model llama3:8b`
4. **Reduce token limit**: Edit `max_tokens` in `agentic_processor.py`

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'ollama'`

**Solution**:
```bash
# Ensure virtual environment is activated
source myenv/bin/activate  # Linux/macOS
myenv\Scripts\activate     # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Log Files

Check logs for debugging:
```bash
# Application logs
tail -f logs/agentic_news_*.log

# Django logs
tail -f logs/django.log

# Ollama logs (Linux)
journalctl -u ollama -f
```

---

## 📊 Performance Tips

### Optimal Settings

**For Speed** (3-5 minutes):
```bash
python manage.py agentic_news_update \
    --limit 20 \
    --top-n 5 \
    --workers 6 \
    --model llama3:8b
```

**For Quality** (10-30 minutes):
```bash
python manage.py agentic_news_update \
    --top-n 10 \
    --workers 4 \
    --model llama3 \
    --show-details
```

**Balanced** (5-15 minutes):
```bash
python manage.py agentic_news_update \
    --limit 50 \
    --top-n 10 \
    --workers 4
```

### Hardware Recommendations

| Hardware | Workers | Model | Expected Time |
|----------|---------|-------|---------------|
| CPU only (4 cores) | 2 | llama3:8b | 15-30 min |
| CPU only (8+ cores) | 4 | llama3 | 10-20 min |
| GPU (8GB VRAM) | 4 | llama3 | 5-10 min |
| GPU (16GB+ VRAM) | 6 | llama3:70b | 8-15 min |

---



