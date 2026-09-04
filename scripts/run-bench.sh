#!/bin/bash
cd ~/benchmark
exec python3 benchmark_llm.py --cases cases.jsonl --models qwen3:8b gpt-oss:20b gemma4:26b qwen3.8:27b > bench-final.log 2>&1
