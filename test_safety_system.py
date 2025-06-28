#!/usr/bin/env python3
"""
Test script for the SafetyAnalyzer system
"""

import logging
import json
from safety_analyzer import SafetyAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_safety_analyzer():
    """Test the SafetyAnalyzer system with various NYC areas"""
    
    print("="*60)
    print("NYC APARTMENT HUNTING - SAFETY ANALYZER TEST")
    print("="*60)
    
    # Initialize safety analyzer
    print("\n1. Initializing Safety Analyzer...")
    analyzer = SafetyAnalyzer('crime_data.json')
    
    if not analyzer.load_data():
        print("❌ Failed to load crime data")
        return False
    
    print("✅ Safety analyzer initialized successfully")
    
    # Validate system
    print("\n2. Validating system...")
    if not analyzer.validate_system():
        print("❌ System validation failed")
        return False
    
    print("✅ System validation passed")
    
    # Test different NYC areas
    test_areas = [
        {
            'name': 'Manhattan - Upper East Side',
            'zip_code': '10021',
            'borough': 'MANHATTAN'
        },
        {
            'name': 'Brooklyn - Williamsburg',
            'zip_code': '11211',
            'borough': 'BROOKLYN'
        },
        {
            'name': 'Queens - Astoria',
            'zip_code': '11106',
            'borough': 'QUEENS'
        },
        {
            'name': 'Bronx - Fordham',
            'zip_code': '10458',
            'borough': 'BRONX'
        },
        {
            'name': 'Staten Island',
            'borough': 'STATEN ISLAND'
        }
    ]
    
    print("\n3. Testing Safety Analysis for Different Areas...")
    
    for area in test_areas:
        print(f"\n{'='*50}")
        print(f"🏙️  AREA: {area['name']}")
        print(f"{'='*50}")
        
        # Get safety rating
        safety_analysis = analyzer.get_area_safety_rating(
            zip_code=area.get('zip_code'),
            borough=area.get('borough')
        )
        
        # Display results
        print_safety_summary(safety_analysis)
    
    # Test borough comparison
    print(f"\n{'='*60}")
    print("🏆 BOROUGH SAFETY COMPARISON")
    print(f"{'='*60}")
    
    borough_comparison = analyzer.get_borough_comparison()
    
    if borough_comparison:
        # Sort by safety score (descending)
        sorted_boroughs = sorted(
            borough_comparison.items(),
            key=lambda x: x[1]['safety_score'],
            reverse=True
        )
        
        print("\nBoroughs ranked by safety score (highest to lowest):")
        print("-" * 55)
        
        for i, (borough, stats) in enumerate(sorted_boroughs, 1):
            print(f"{i}. {borough:<15} | Grade: {stats['grade']} | Score: {stats['safety_score']:.2f}/5.0 | Complaints: {stats['total_complaints']:,}")
    
    print(f"\n{'='*60}")
    print("✅ Safety Analysis Testing Complete!")
    print(f"{'='*60}")
    
    return True

def print_safety_summary(analysis):
    """Print formatted safety analysis summary"""
    
    area_info = analysis.get('area_info', {})
    rating = analysis.get('safety_rating', {})
    metrics = analysis.get('safety_metrics', {})
    summary = analysis.get('safety_summary', '')
    recommendations = analysis.get('recommendations', [])
    recent_activity = analysis.get('recent_activity', {})
    
    # Area information
    if area_info.get('zip_code'):
        print(f"📍 ZIP Code: {area_info['zip_code']}")
    if area_info.get('borough'):
        print(f"🏛️  Borough: {area_info['borough']}")
    
    print(f"📊 Data Points: {area_info.get('data_points', 0)}")
    
    # Safety rating
    grade = rating.get('grade', 'N/A')
    score = rating.get('score', 0)
    description = rating.get('description', 'Unknown')
    
    # Use emoji based on grade
    grade_emoji = {
        'A': '🟢',
        'B': '🟡', 
        'C': '🟠',
        'D': '🔴',
        'F': '⚫'
    }.get(grade, '⚪')
    
    print(f"\n{grade_emoji} SAFETY RATING: Grade {grade} - {description}")
    print(f"📈 Safety Score: {score:.2f}/5.0")
    
    # Key metrics
    total_complaints = metrics.get('total_complaints', 0)
    high_concern_ratio = metrics.get('high_concern_ratio', 0)
    
    print(f"🚨 Total Complaints: {total_complaints}")
    if high_concern_ratio > 0:
        print(f"⚠️  High Concern Issues: {high_concern_ratio:.1%}")
    
    # Recent activity
    recent_complaints = recent_activity.get('recent_complaints', 0)
    trend = recent_activity.get('trend', 'stable')
    
    trend_emoji = {
        'increasing': '📈',
        'decreasing': '📉',
        'stable': '➡️'
    }.get(trend, '➡️')
    
    print(f"{trend_emoji} Recent Activity: {recent_complaints} complaints (trend: {trend})")
    
    # Summary
    print(f"\n💬 SUMMARY:")
    print(f"   {summary}")
    
    # Top recommendations
    if recommendations:
        print(f"\n💡 KEY RECOMMENDATIONS:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"   {i}. {rec}")
    
    print()

def main():
    """Main test function"""
    try:
        success = test_safety_analyzer()
        if success:
            print("\n🎉 All tests completed successfully!")
            print("\nThe safety analyzer is ready to help apartment hunters make informed decisions!")
        else:
            print("\n❌ Tests failed. Please check the error messages above.")
            
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main() 