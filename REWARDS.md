# Reward Points System

## Point Allocation Table

| Points | Category | Condition | Example |
|:------:|----------|-----------|---------|
| **5** | 🆕 **NEW_QUESTION** | Medical question NOT in RAG (similarity < 0.4) | "Best fertility clinic in Mumbai?" |
| **3** | 🏥 **MEDICAL** | Medical question found in RAG (similarity ≥ 0.4) | "What is IVF?", "PCOS symptoms" |
| **2** | 🔄 **FOLLOW_UP** | User clicked a suggested follow-up question | (From suggestions) |
| **1** | 💬 **CONVERSATIONAL** | Greetings, thanks, small talk | "Hello", "Thanks", "How are you?" |

---

## Classification Flow

```
User Message
     │
     ▼
┌─────────────────────────┐
│  Is it a follow-up?     │──── YES ───► 2 pts (FOLLOW_UP)
└─────────────────────────┘
     │ NO
     ▼
┌─────────────────────────┐
│  Route = SLM_DIRECT?    │──── YES ───► 1 pt (CONVERSATIONAL)
│  (Small talk detected)  │
└─────────────────────────┘
     │ NO
     ▼
┌─────────────────────────┐
│  Route = SLM_RAG or     │
│  OPENAI_RAG (Medical)   │
└─────────────────────────┘
     │
     ▼
┌─────────────────────────┐
│  RAG Similarity < 0.4?  │──── YES ───► 5 pts (NEW_QUESTION)
│  (Not in knowledge base)│              + Store for KB expansion
└─────────────────────────┘
     │ NO
     ▼
           3 pts (MEDICAL)
```

---

## Route Priority

| Route | Description | When Used |
|-------|-------------|-----------|
| **SLM_DIRECT** | SLM alone (no RAG) | Greetings, small talk |
| **SLM_RAG** | SLM + RAG (Primary) | Standard medical queries |
| **OPENAI_RAG** | OpenAI + RAG (Fallback) | Complex medical queries |

---

## Commands

| Command | Action |
|---------|--------|
| `.rewards` | Shows user's total reward points |

---

## Technical Details

- **Threshold**: `NEW_QUESTION_THRESHOLD = 0.4`
- **Async**: All reward operations run via `asyncio.create_task()` (zero latency impact)
- **Storage**: New questions (< 0.4 similarity) are stored in `sakhi_new_questions` table
