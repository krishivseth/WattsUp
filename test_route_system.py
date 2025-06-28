#!/usr/bin/env python3
"""
Test script for the Route Planning system
"""

import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_route_api():
    """Test the route planning API endpoint"""
    
    print("="*60)
    print("NYC SAFE ROUTE PLANNING - API TEST")
    print("="*60)
    
    # Test data
    test_routes = [
        {
            'name': 'Manhattan to Brooklyn',
            'origin': 'Times Square, Manhattan, NY',
            'destination': 'Brooklyn Bridge, Brooklyn, NY'
        },
        {
            'name': 'Queens to Manhattan',
            'origin': 'Astoria, Queens, NY',
            'destination': 'Central Park, Manhattan, NY'
        },
        {
            'name': 'Local Route',
            'origin': '123 Main St, Queens, NY',
            'destination': '456 Broadway, Manhattan, NY'
        }
    ]
    
    base_url = "http://127.0.0.1:5002"
    
    # Test health endpoint first
    print("\n1. Testing backend health...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running")
        else:
            print("❌ Backend health check failed")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        print("Make sure to run: python app.py")
        return False
    
    # Test route analysis
    print("\n2. Testing route analysis...")
    
    for i, route_test in enumerate(test_routes, 1):
        print(f"\n{'='*50}")
        print(f"🗺️  TEST {i}: {route_test['name']}")
        print(f"{'='*50}")
        
        try:
            # Make API request
            response = requests.post(
                f"{base_url}/api/safe-routes",
                json={
                    'origin': route_test['origin'],
                    'destination': route_test['destination'],
                    'mode': 'driving'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                print_route_analysis(data)
            else:
                print(f"❌ API Error: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
    
    print(f"\n{'='*60}")
    print("✅ Route API Testing Complete!")
    print(f"{'='*60}")
    
    return True

def print_route_analysis(data):
    """Print formatted route analysis results"""
    
    if 'error' in data:
        print(f"❌ Error: {data['error']}")
        return
    
    routes = data.get('routes', [])
    
    print(f"📍 From: {data.get('origin_address', 'Unknown')}")
    print(f"📍 To: {data.get('destination_address', 'Unknown')}")
    print(f"📊 Total Routes Analyzed: {data.get('total_routes_analyzed', 0)}")
    
    if not routes:
        print("❌ No routes found")
        return
    
    print(f"\n🗺️  ROUTE OPTIONS:")
    print("-" * 50)
    
    for i, route in enumerate(routes, 1):
        route_type = route.get('route_type', 'unknown')
        safety_score = route.get('overall_safety_score', 0)
        safety_grade = route.get('overall_safety_grade', 'N/A')
        duration = route.get('total_duration', {}).get('text', 'Unknown')
        distance = route.get('total_distance', {}).get('text', 'Unknown')
        description = route.get('safety_description', '')
        
        # Route type emoji
        type_emoji = {
            'safest': '🛡️',
            'balanced': '⚖️',
            'fastest': '⚡',
            'analyzed': '🗺️'
        }.get(route_type, '📍')
        
        # Safety grade emoji
        grade_emoji = {
            'A': '🟢',
            'B': '🟡',
            'C': '🟠',
            'D': '🔴',
            'F': '⚫'
        }.get(safety_grade, '⚪')
        
        print(f"{type_emoji} {route_type.upper()} ROUTE")
        print(f"   {grade_emoji} Safety: Grade {safety_grade} ({safety_score:.1f}/5.0)")
        print(f"   ⏱️  Duration: {duration}")
        print(f"   📏 Distance: {distance}")
        print(f"   💬 {description}")
        
        # Show warnings if any
        warnings = route.get('warnings', [])
        if warnings:
            for warning in warnings:
                print(f"   ⚠️  {warning}")
        
        print()
    
    # Show recommendation
    recommendation = data.get('recommendation', {})
    if recommendation.get('reason'):
        print(f"💡 RECOMMENDATION:")
        print(f"   {recommendation['reason']}")

def main():
    """Main test function"""
    try:
        print("🚀 Starting Route Planning System Tests...")
        print("\nNote: This test requires:")
        print("1. Backend running (python app.py)")
        print("2. Google Maps API key configured")
        print("3. Internet connection for Google Maps API")
        
        input("\nPress Enter to continue...")
        
        success = test_route_api()
        if success:
            print("\n🎉 Route planning system is working!")
            print("\nNext steps:")
            print("1. Configure Google Maps API key in route-planner.html")
            print("2. Build extension: cd frontend && npm run build:extension")
            print("3. Load extension in Chrome and test full workflow")
        else:
            print("\n❌ Tests failed. Check the error messages above.")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Test cancelled by user")
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main() 