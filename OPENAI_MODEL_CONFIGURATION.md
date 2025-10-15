# OpenAI Model Configuration Guide

**Last Updated**: October 7, 2025
**Owner**: Kevin Vandever
**Purpose**: Guide for configuring and tuning OpenAI models for MC Press Chatbot

---

## 📋 Table of Contents

1. [Current Configuration](#current-configuration)
2. [Environment Variable Override System](#environment-variable-override-system)
3. [Available OpenAI Models](#available-openai-models)
4. [Configuration Parameters](#configuration-parameters)
5. [Tuning Guidelines](#tuning-guidelines)
6. [Model Deprecation Status](#model-deprecation-status)
7. [Cost Analysis](#cost-analysis)
8. [Quick Experiments](#quick-experiments)

---

## 🎯 Current Configuration

**As of October 7, 2025:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| **Model** | `gpt-4o-mini` | Best balance of quality, speed, and cost |
| **Temperature** | `0.5` | Balanced between accuracy and expansiveness |
| **Max Tokens** | `3000` | Room for comprehensive, in-depth responses |
| **Stream** | `true` | Real-time response streaming for better UX |

**Previous Configuration (before Oct 7, 2025):**
- Model: `gpt-3.5-turbo` (legacy)
- Temperature: `0.3` (too conservative)
- Max Tokens: `2000` (too limited)

**Changes Made:**
- ✅ Upgraded to GPT-4o-mini for better reasoning
- ✅ Increased temperature for more comprehensive responses
- ✅ Increased max tokens for deeper explanations
- ✅ Enhanced system prompt to emphasize depth and synthesis

---

## 🎛️ Environment Variable Override System

### How It Works

The code in `backend/config.py` is already configured to read from environment variables:

```python
# OpenAI Configuration
OPENAI_CONFIG = {
    "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.5")),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "3000")),
    "stream": True
}
```

**Logic:**
1. Check for environment variable (e.g., `OPENAI_MODEL`)
2. If not found, use default value (e.g., `"gpt-4o-mini"`)
3. Environment variables always override code defaults

### Setting Environment Variables in Railway

**Railway Dashboard:**
1. Go to your Railway project
2. Select the backend service
3. Click **Variables** tab
4. Click **+ New Variable**
5. Add variable (e.g., `OPENAI_MODEL = gpt-4o`)
6. Railway will automatically redeploy (~30 seconds)

**Available Variables:**
```bash
OPENAI_MODEL=gpt-4o-mini          # Model to use
OPENAI_TEMPERATURE=0.5            # Response creativity (0.0-2.0)
OPENAI_MAX_TOKENS=3000            # Maximum response length
```

**Benefits:**
- ✅ No code changes needed
- ✅ No git commits required
- ✅ Fast redeployment (30 seconds vs 3-5 minutes)
- ✅ Easy to revert (delete variable = back to defaults)
- ✅ Test different configs without touching code

---

## 🤖 Available OpenAI Models

### Current Production Models (2025)

| Model | Context | Input Cost | Output Cost | Best For | Status |
|-------|---------|-----------|-------------|----------|--------|
| **gpt-4o-mini** | 128K | $0.15/1M | $0.60/1M | Cost-effective quality | ✅ **Recommended** |
| **gpt-4o** | 128K | $2.50/1M | $10.00/1M | Premium quality | ✅ Active |
| **gpt-4-turbo** | 128K | $10.00/1M | $30.00/1M | Legacy premium | ✅ Active |
| **gpt-3.5-turbo** | 16K | $0.50/1M | $1.50/1M | Legacy | ⚠️ Being phased out |
| **gpt-4.1** | 1M | Higher | Higher | Latest flagship | ✅ Active |

### Model Characteristics

**gpt-4o-mini** (Current Choice):
- ✅ 70% cheaper than gpt-3.5-turbo
- ✅ Better reasoning and depth than gpt-3.5-turbo
- ✅ Good at synthesis across multiple sources
- ✅ Fast responses (<2 seconds)
- ✅ 128K context window (plenty for RAG)

**gpt-4o** (Premium Option):
- ✅ Best-in-class quality
- ✅ Excellent at complex reasoning
- ✅ Superior synthesis across sources
- ❌ 16x more expensive than gpt-4o-mini
- 💡 Use if quality is more important than cost

**gpt-3.5-turbo** (Legacy):
- ⚠️ Being phased out over time
- ❌ Shallower responses
- ❌ Limited reasoning depth
- ❌ More expensive than gpt-4o-mini
- 🚫 Not recommended for new projects

---

## ⚙️ Configuration Parameters

### 1. Model (`OPENAI_MODEL`)

**What it does:** Selects which OpenAI model to use

**Options:**
- `gpt-4o-mini` - Default, recommended
- `gpt-4o` - Premium quality
- `gpt-4-turbo` - Legacy premium
- `gpt-3.5-turbo` - Legacy (not recommended)

**When to change:**
- Try `gpt-4o` if responses still lack depth
- Stick with `gpt-4o-mini` for cost-effective quality

---

### 2. Temperature (`OPENAI_TEMPERATURE`)

**What it does:** Controls response creativity and variability

**Range:** 0.0 to 2.0
- **0.0** = Deterministic, factual, minimal creativity
- **0.3** = Very conservative (previous setting)
- **0.5** = Balanced accuracy + expansiveness ✅ **Current**
- **0.7** = More creative, varied responses
- **1.0** = High creativity
- **2.0** = Maximum randomness (not recommended)

**Use Cases:**

| Temperature | Best For | Response Style |
|-------------|----------|----------------|
| 0.0 - 0.2 | Factual lookups, exact answers | Deterministic, terse |
| 0.3 - 0.5 | Technical documentation (RAG) | Accurate + comprehensive ✅ |
| 0.6 - 0.8 | Creative explanations, tutorials | Expansive, varied |
| 0.9+ | Creative writing, brainstorming | Highly variable |

**For MC Press Chatbot:**
- Current: `0.5` (good balance)
- Too shallow? Try: `0.6` or `0.7`
- Too verbose? Try: `0.4`
- Need exact quotes? Try: `0.2`

---

### 3. Max Tokens (`OPENAI_MAX_TOKENS`)

**What it does:** Maximum length of the response

**Typical Values:**
- `1000` = Short, concise answers (~750 words)
- `2000` = Medium answers (~1500 words) - previous setting
- `3000` = Comprehensive answers (~2250 words) ✅ **Current**
- `4000` = Very detailed answers (~3000 words)
- `8000` = Maximum depth (~6000 words)

**Token Estimation:**
- 1 token ≈ 0.75 words
- 1000 tokens ≈ 750 words ≈ 1-2 paragraphs
- 3000 tokens ≈ 2250 words ≈ 4-6 paragraphs

**Considerations:**
- Higher tokens = more comprehensive BUT slower + more expensive
- RAG context uses ~5000-6000 tokens, leaving room for response
- GPT-4o-mini context limit: 128K tokens (total input + output)

**For MC Press Chatbot:**
- Current: `3000` (good depth)
- Want more detail? Try: `4000`
- Need faster responses? Try: `2500`
- Maximum depth? Try: `5000` (but may be overkill)

---

## 🎯 Tuning Guidelines

### Finding Your Optimal Configuration

**Step 1: Start with Current Defaults**
```bash
# Already set in code (no env vars needed)
Model: gpt-4o-mini
Temperature: 0.5
Max Tokens: 3000
```

**Step 2: Test with Real Queries**

Try these test queries and evaluate:

1. **Conceptual:** "What is RPG programming?"
2. **How-to:** "How do I create a subfile in RPG?"
3. **Complex:** "Explain the differences between embedded SQL and native DB2 file operations"

**Evaluate:**
- ✅ Depth sufficient? (comprehensive explanations with examples)
- ✅ Accuracy maintained? (cites sources, stays factual)
- ✅ Response time acceptable? (<3 seconds)
- ✅ Cost sustainable? (check OpenAI dashboard)

**Step 3: Adjust Based on Results**

| Issue | Try This |
|-------|----------|
| Responses too shallow | Increase temperature to 0.6-0.7 |
| Responses too verbose | Decrease max_tokens to 2500 |
| Responses too conservative | Increase temperature to 0.6 |
| Responses too creative | Decrease temperature to 0.4 |
| Not enough detail | Increase max_tokens to 4000 |
| Too slow | Decrease max_tokens to 2500 |
| Too expensive | Stick with gpt-4o-mini, adjust tokens |
| Quality not good enough | Try gpt-4o model |

**Step 4: Monitor Over 48 Hours**

Track:
- User feedback on response quality
- OpenAI API costs (should be ~$0.002-0.004 per query)
- Average response time (target: <3 seconds)
- Confidence scores in logs (target: 0.3-0.8)

---

## 📊 Cost Analysis

### Current Configuration Cost

**Model: gpt-4o-mini**
- Input: $0.15 per 1M tokens
- Output: $0.60 per 1M tokens

**Typical Query Breakdown:**
```
Input tokens:
  - System prompt: ~500 tokens
  - Context (12 sources): ~5000 tokens
  - User query: ~100 tokens
  - Conversation history: ~400 tokens
  Total input: ~6000 tokens

Output tokens: ~2000-3000 tokens (depends on answer)
```

**Cost Per Query:**
```
Input:  6000 tokens × $0.15 / 1M = $0.0009
Output: 2500 tokens × $0.60 / 1M = $0.0015
Total: ~$0.0024 per query
```

**Monthly Estimates:**

| Queries/Month | Cost (gpt-4o-mini) | Cost (gpt-4o) | Savings |
|---------------|-------------------|---------------|---------|
| 1,000 | $2.40 | $40.00 | 94% |
| 5,000 | $12.00 | $200.00 | 94% |
| 10,000 | $24.00 | $400.00 | 94% |
| 50,000 | $120.00 | $2,000.00 | 94% |

**Cost Optimization Tips:**
1. ✅ Use gpt-4o-mini (not gpt-4o) for most queries
2. ✅ Optimize context size (max_sources = 8-12)
3. ✅ Adjust max_tokens based on query complexity
4. ✅ Use caching for repeated queries (if implemented)
5. ⚠️ Monitor usage in OpenAI dashboard

---

## 🧪 Quick Experiments

### Experiment 1: More Expansive Responses

**Goal:** Even more detailed, comprehensive answers

**Railway Environment Variables:**
```bash
OPENAI_TEMPERATURE=0.6
OPENAI_MAX_TOKENS=4000
```

**Expected:**
- More varied phrasing
- More examples and context
- Longer, more detailed answers
- Slightly higher cost (~$0.003 per query)

**When to use:** If current responses still feel shallow

---

### Experiment 2: Premium Quality

**Goal:** Best possible answer quality

**Railway Environment Variables:**
```bash
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.5
OPENAI_MAX_TOKENS=4000
```

**Expected:**
- Excellent synthesis across sources
- Superior reasoning and depth
- More nuanced explanations
- 16x higher cost (~$0.040 per query)

**When to use:** Quality is paramount, cost is not a concern

---

### Experiment 3: More Conservative

**Goal:** Shorter, more focused answers (if current is too verbose)

**Railway Environment Variables:**
```bash
OPENAI_TEMPERATURE=0.4
OPENAI_MAX_TOKENS=2500
```

**Expected:**
- More concise responses
- Less elaboration
- Faster response time
- Lower cost (~$0.002 per query)

**When to use:** Users prefer quick, direct answers

---

### Experiment 4: Maximum Depth

**Goal:** Extremely comprehensive, tutorial-style answers

**Railway Environment Variables:**
```bash
OPENAI_MODEL=gpt-4o
OPENAI_TEMPERATURE=0.6
OPENAI_MAX_TOKENS=5000
```

**Expected:**
- Very detailed, in-depth responses
- Multiple examples and use cases
- Tutorial-quality explanations
- High cost (~$0.060 per query)

**When to use:** Educational use case, premium offering

---

## 🚨 Model Deprecation Status

### Official OpenAI Deprecation Timeline (as of Oct 2025)

**Already Deprecated:**
- ❌ **GPT-4.5 Preview** - EOL July 14, 2025
- ❌ **GPT-4/3.5 "-0314/-0301" snapshots** - EOL June 13, 2024
- ❌ **Completions API models** - EOL January 4, 2024
- ❌ **Legacy embeddings** - EOL January 4, 2024

**Currently Active (Safe to Use):**
- ✅ **gpt-4o-mini** - Current, recommended
- ✅ **gpt-4o** - Current, premium
- ✅ **gpt-4-turbo** - Legacy but supported
- ✅ **gpt-3.5-turbo** - Legacy, being phased out eventually

**Future Deprecations:**
- ⚠️ **Assistants API v2** - Will be deprecated H1 2026 (we don't use this)

**Best Practices:**
1. ✅ Avoid "preview" models in production
2. ✅ Pin specific snapshots for stability (or use env vars for flexibility)
3. ✅ Prefer "4o" family models for longevity
4. ✅ Monitor OpenAI deprecation page: https://platform.openai.com/docs/deprecations
5. ✅ Use environment variables for easy migration

---

## 📚 Additional Resources

### Official OpenAI Documentation
- **Pricing:** https://openai.com/api/pricing/
- **Models:** https://platform.openai.com/docs/models
- **Deprecations:** https://platform.openai.com/docs/deprecations
- **Chat Completions API:** https://platform.openai.com/docs/api-reference/chat

### MC Press Chatbot Documentation
- **Technology Stack:** [TECHNOLOGY_STACK.md](./TECHNOLOGY_STACK.md)
- **Deployment Guide:** [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **AI Agents Reference:** [README_AI_AGENTS.md](./README_AI_AGENTS.md)

### Configuration Files
- **Backend Config:** `backend/config.py` (line 45-51)
- **Chat Handler:** `backend/chat_handler.py` (system prompt line 110-152)

---

## 🎯 Quick Reference Card

**Current Production Config:**
```bash
Model: gpt-4o-mini
Temperature: 0.5
Max Tokens: 3000
Cost per query: ~$0.0024
```

**Override in Railway:**
```bash
OPENAI_MODEL=gpt-4o-mini          # Model selection
OPENAI_TEMPERATURE=0.5            # 0.0-2.0, default 0.5
OPENAI_MAX_TOKENS=3000            # 1000-8000, default 3000
```

**Common Adjustments:**
- More depth? → Temperature 0.6-0.7
- More detail? → Max tokens 4000
- Premium quality? → Model gpt-4o
- More concise? → Temperature 0.4, Max tokens 2500

**Monitoring:**
- OpenAI Dashboard: https://platform.openai.com/usage
- Railway Logs: Check for model initialization
- Test endpoint: https://mcpress-chatbot-production.up.railway.app/health

---

**Document Version:** 1.0
**Last Updated:** October 7, 2025
**Next Review:** When model performance needs adjustment or OpenAI releases new models
