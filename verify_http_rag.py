#!/usr/bin/env python3
"""
Test script to verify HttpRAGClient integration with CalendarAgent
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.http_rag_client import HttpRAGClient

async def test_rag_integration():
    """Test RAG retrieval for christopher-bean-coffee"""
    
    print("=" * 80)
    print("Testing HttpRAGClient Integration")
    print("=" * 80)
    
    # Initialize client
    rag_client = HttpRAGClient()
    print(f"\n✓ Initialized HttpRAGClient")
    print(f"  Base URL: {rag_client.rag_api_base_url}")
    
    # Test client ID
    client_id = "christopher-bean-coffee"
    print(f"\n📋 Testing RAG retrieval for: {client_id}")
    
    # Test get_all_data
    print("\n1. Testing get_all_data()...")
    rag_data = await rag_client.get_all_data(client_id)
    
    print(f"\n   Categories retrieved:")
    for category, data in rag_data.items():
        if data:
            content_preview = data.get("content", "")[:100] if isinstance(data, dict) else str(data)[:100]
            print(f"   ✓ {category}: {len(data.get('content', '') if isinstance(data, dict) else '')} chars")
            print(f"     Preview: {content_preview}...")
        else:
            print(f"   ✗ {category}: No data")
    
    # Test format_for_prompt
    print("\n2. Testing format_for_prompt()...")
    formatted = await rag_client.format_for_prompt(client_id)
    print(f"   ✓ Formatted prompt: {len(formatted)} characters")
    print(f"\n   Preview (first 500 chars):")
    print(f"   {formatted[:500]}...")
    
    # Test product catalog extraction
    print("\n3. Testing product catalog extraction...")
    product_catalog_data = rag_data.get("product_catalog")
    if product_catalog_data:
        if isinstance(product_catalog_data, dict) and "content" in product_catalog_data:
            product_catalog_formatted = product_catalog_data["content"]
            print(f"   ✓ Product catalog: {len(product_catalog_formatted)} characters")
            print(f"   Preview: {product_catalog_formatted[:200]}...")
        else:
            print(f"   ⚠ Unexpected format: {type(product_catalog_data)}")
    else:
        print(f"   ✗ No product catalog found")
    
    # Test semantic retrieval
    print("\n4. Testing semantic retrieval...")
    result = await rag_client.retrieve_semantic(
        client_id,
        "brand voice and tone guidelines",
        top_k=3,
        score_threshold=0.3
    )
    
    if result.get("success"):
        snippets = result.get("data", {}).get("snippets", [])
        print(f"   ✓ Retrieved {len(snippets)} snippets")
        for i, snippet in enumerate(snippets, 1):
            print(f"   Snippet {i}:")
            print(f"     - Score: {snippet.get('score', 0):.2f}")
            print(f"     - Doc: {snippet.get('doc_title', 'Unknown')}")
            print(f"     - Content: {snippet.get('content', '')[:100]}...")
    else:
        print(f"   ✗ Retrieval failed: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 80)
    print("✅ RAG Integration Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_rag_integration())
