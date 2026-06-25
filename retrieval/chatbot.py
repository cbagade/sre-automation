#!/usr/bin/env python3
"""
Interactive Chatbot for RCA Incident Retrieval
Uses OpenAI SDK to retrieve relevant incidents based on user queries.
"""

import os
import sys
from dotenv import load_dotenv
from extract_ingested_inc import search_incidents, extract_keywords

# Load environment variables
load_dotenv()


def print_separator(char="=", length=80):
    """Print a separator line."""
    print(char * length)


def display_results(results, query):
    """Display search results in a formatted way."""
    if not results:
        print("\n❌ No matching incidents found.")
        print("💡 Try using different component names like: vcda, nsx, veeam, edge, backup, etc.")
        return
    
    print(f"\n✅ Found {len(results)} matching incident(s):\n")
    
    for i, result in enumerate(results, 1):
        print(f"{'─' * 80}")
        print(f"📋 Incident #{i}: {result['id']}")
        print(f"{'─' * 80}")
        
        # Get semantic similarity from result
        semantic_similarity = result.get('semantic_similarity', 0)
        
        print(f"📌 Title: {result.get('title', 'N/A')}")
        print(f"🎯 Component Match: {result['matched_count']}/{result['total_keywords']} keywords ({result['match_percentage']:.1f}%)")
        print(f"📊 Semantic Similarity: {semantic_similarity:.1f}%")
        print(f"🔑 Matched Keywords: {', '.join(result['matched_keywords'])}")
        print(f"📅 Date Occurred: {result.get('date_occurred', 'N/A')}")
        
        print(f"\n❗ Problem:")
        print(f"   {result.get('problem', 'N/A')}")
        
        print(f"\n🔍 Root Cause:")
        print(f"   {result.get('root_cause', 'N/A')[:300]}...")
        
        print(f"\n✅ Resolution:")
        print(f"   {result.get('resolution', 'N/A')[:200]}...")
        
        print(f"\n💥 Impact: {result.get('impact', 'N/A')}")
        
        if result.get('incident_number'):
            print(f"🎫 Incident: {result['incident_number']}")
        
        if result.get('cbc'):
            print(f"🔧 CBC: {result['cbc']}")
        
        if result.get('broadcom_kb'):
            print(f"📚 Broadcom KB: {result['broadcom_kb']}")
        
        print()


def run_chatbot():
    """Run the interactive chatbot."""
    print("\n" + "=" * 80)
    print("🤖 RCA Incident Retrieval Chatbot")
    print("=" * 80)
    print("\n💬 Ask me about incidents related to components like:")
    print("   • vcda, nsx, veeam, edge, backup, replication")
    print("   • vcenter, vsan, esxi, authentication, certificate")
    print("   • and more...")
    print("\n📌 Commands:")
    print("   • Type your query to search for incidents")
    print("   • Type 'quit' or 'exit' to end the session")
    print("   • Type 'help' for examples")
    print_separator()
    
    while True:
        try:
            # Get user input
            user_input = input("\n💬 You: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Thank you for using the RCA Incident Retrieval Chatbot!")
                print("   Goodbye!\n")
                break
            
            # Check for help command
            if user_input.lower() == 'help':
                print("\n📚 Example Queries:")
                print("   • 'vcda is down and replications are failing'")
                print("   • 'nsx edge deployment issues'")
                print("   • 'veeam backup jobs not working'")
                print("   • 'certificate authentication problems'")
                print("   • 'esxi host connectivity issues'")
                continue
            
            # Skip empty input
            if not user_input:
                continue
            
            # Extract keywords to show user what we're searching for
            keywords = extract_keywords(user_input, max_keywords=2)
            if keywords:
                print(f"\n🔍 Searching for incidents related to: {', '.join(keywords)}")
            
            # Search for incidents (top 3 results)
            print("⏳ Retrieving data...")
            results = search_incidents(user_input, threshold=50.0, top_k=3)
            
            # Display results
            display_results(results, user_input)
            
        except KeyboardInterrupt:
            print("\n\n👋 Session interrupted. Goodbye!\n")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("💡 Please try again with a different query.\n")


def main():
    """Main entry point."""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment variables.")
        print("💡 Please set your OpenAI API key in the .env file.\n")
        sys.exit(1)
    
    try:
        run_chatbot()
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()

# Made with Bob
