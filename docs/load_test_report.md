# Load Test Report: Sakhi Chat Endpoint

## Overview
- **Date**: 2026-02-08
- **Endpoint**: `http://72.61.228.9:8000/sakhi/chat`
- **Scenario**: 15 Concurrent Requests from **Onboarded Users** with **Medical Questions**.
- **Test Script**: `tests/load_test_chat.py`

## Results
- **Total Requests**: 15 (100% Success)
- **Status Codes**: 
  - 200 OK: 15
- **Throughput**: ~0.51 requests/second
- **Total Duration**: 29.53s

### Response Time Metrics
| Metric | Value |
| :--- | :--- |
| **Minimum** | 1.07s |
| **Maximum** | 29.52s |
| **Average** | 17.19s |
| **Median** | 19.28s |

## Observations
1. **High Latency for Medical Queries**: 
   These requests involved the full **RAG + SLM** pipeline (retrieval augmented generation with a large language model). The average response time of **17.19s** and a maximum of **29.52s** indicates this is a heavy computational process.
   
2. **Concurrency Impact**:
   - The first request finished in 1.07s (possibly a cache hit or very simple routing).
   - Subsequent requests slowed down significantly, suggesting the server or the LLM inference backend queues requests rather than processing them fully in parallel.
   
3. **Success Rate**:
   Despite the delay, the server successfully handled all 15 concurrent complex queries without dropping connections or timing out (after increasing the client timeout to 120s).

## Recommendations
- **Async/Background Processing**: For such high-latency operations, consider moving the LLM generation to a background task and using a webhook or polling mechanism for the frontend, if 30s waits are unacceptable for the user experience.
- **Caching**: Implement semantic caching for common medical questions to serve near-instant responses (like the 1.07s case).
- **Scale Inference**: If using a local LLM/SLM, check if it can batch requests or if multiple instances are needed to improve throughput.
