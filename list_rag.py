import os
from pathlib import Path

rag_path = Path("/Users/Damon/klaviyo/klaviyo-audit-automation/emailpilot-orchestrator/rag/corpus")

if rag_path.exists():
    print(f"Listing contents of {rag_path}:")
    for item in rag_path.iterdir():
        if item.is_dir():
            print(f"DIR: {item.name}")
else:
    print(f"Path does not exist: {rag_path}")
