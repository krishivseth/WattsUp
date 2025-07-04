#!/usr/bin/env python3
"""
Test script for the Google Reviews analysis system
"""

import os
import sys
import json
import logging

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reviews_analyzer import ReviewsAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_reviews_analyzer():
    """Test the reviews analyzer functionality"""
    
    # Define test parameters
    google_api_key = "AIzaSyALD1d2zJpPqOE0e_E5rrx7JiMdAUUmfds"
    openai_api_key = os.getenv('OPENAI_API_KEY')  # Get from environment
    
    # Test addresses
    test_addresses = [
        {
            "address": "123 Main St, Queens, NY",
            "building_name": None,
            "description": "Generic apartment building address"
        },
        {
            "address": "555 West 23rd Street, New York, NY",
            "building_name": "555 West 23rd",
            "description": "Specific building with name"
        },
        {
            "address": "The High Line, New York, NY",
            "building_name": "The High Line",
            "description": "Famous location to test search functionality"
        }
    ]
    
    try:
        # Initialize the reviews analyzer
        logger.info("Initializing ReviewsAnalyzer...")
        analyzer = ReviewsAnalyzer(google_api_key, openai_api_key)
        
        if not openai_api_key:
            logger.warning("OpenAI API key not found - will use basic analysis")
        
        # Test each address
        for i, test_case in enumerate(test_addresses, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Test Case {i}: {test_case['description']}")
            logger.info(f"Address: {test_case['address']}")
            logger.info(f"Building Name: {test_case['building_name']}")
            logger.info(f"{'='*60}")
            
            try:
                # Analyze reviews
                result = analyzer.analyze_building_reviews(
                    address=test_case['address'],
                    building_name=test_case['building_name']
                )
                
                # Print summary results
                print(f"\nResults for {test_case['address']}:")
                print(f"Status: {result.get('status', 'success')}")
                
                if result.get('status') == 'error':
                    print(f"Error: {result.get('error', 'Unknown error')}")
                    continue
                
                # Building info
                building_info = result.get('building_info', {})
                print(f"Building Name: {building_info.get('name', 'Unknown')}")
                print(f"Building Address: {building_info.get('address', 'Unknown')}")
                print(f"Overall Rating: {building_info.get('rating', 'N/A')}")
                print(f"Total Reviews: {building_info.get('total_reviews', 'N/A')}")
                
                # Reviews summary
                reviews_summary = result.get('reviews_summary', {})
                print(f"Recent Reviews Analyzed: {reviews_summary.get('total_reviews_analyzed', 0)}")
                print(f"Average Rating (Recent): {reviews_summary.get('average_rating', 0):.1f}")
                print(f"Analysis Period: {reviews_summary.get('analysis_period', 'N/A')}")
                
                # AI Analysis
                ai_analysis = result.get('ai_analysis', {})
                if ai_analysis:
                    print(f"\nAI Analysis:")
                    print(f"Summary: {ai_analysis.get('OVERALL_SUMMARY', 'N/A')}")
                    
                    pros = ai_analysis.get('PROS', [])
                    if pros:
                        print(f"Pros: {', '.join(pros[:3])}")  # Show first 3
                    
                    cons = ai_analysis.get('CONS', [])
                    if cons:
                        print(f"Cons: {', '.join(cons[:3])}")  # Show first 3
                
                # Recent reviews
                recent_reviews = result.get('recent_reviews', [])
                if recent_reviews:
                    print(f"\nSample Recent Reviews:")
                    for j, review in enumerate(recent_reviews[:2], 1):  # Show first 2
                        print(f"  {j}. {review.get('author', 'Anonymous')} ({review.get('rating', 'N/A')}/5)")
                        print(f"     {review.get('text', '')[:100]}...")
                
                print(f"\nData Source: {result.get('data_source', 'Unknown')}")
                
            except Exception as e:
                logger.error(f"Error analyzing {test_case['address']}: {e}")
                print(f"Error: {str(e)}")
            
            print("\n" + "-"*60 + "\n")
        
        logger.info("All tests completed!")
        
    except Exception as e:
        logger.error(f"Failed to initialize or run tests: {e}")
        return False
    
    return True

def test_api_integration():
    """Test the API integration"""
    import requests
    
    logger.info("Testing API integration...")
    
    # Test the /api/reviews endpoint
    test_payload = {
        "address": "123 Main St, Queens, NY",
        "building_name": "Test Building"
    }
    
    try:
        # Assuming the server is running on localhost:62031
        response = requests.post(
            'http://localhost:62031/api/reviews',
            json=test_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("API Test Successful!")
            print(f"Building Name: {result.get('building_info', {}).get('name', 'Unknown')}")
            print(f"Reviews Analyzed: {result.get('reviews_summary', {}).get('total_reviews_analyzed', 0)}")
        else:
            print(f"API Test Failed: Status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        logger.warning("Could not connect to API server - make sure the server is running")
    except Exception as e:
        logger.error(f"API test error: {e}")

if __name__ == "__main__":
    print("Google Reviews Analysis System Test")
    print("=" * 50)
    
    # Test the reviews analyzer
    if test_reviews_analyzer():
        print("\n✅ Reviews Analyzer test completed successfully!")
    else:
        print("\n❌ Reviews Analyzer test failed!")
        sys.exit(1)
    
    # Test API integration
    try:
        test_api_integration()
    except Exception as e:
        logger.error(f"API integration test error: {e}")
    
    print("\n🎉 All tests completed!") 