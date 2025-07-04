#!/usr/bin/env python3
"""
Test script for the updated electricity estimation system
- Default AC cost: 40
- Rooms multiplier: num_rooms + 1
"""

import os
import sys
import json
import logging

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bill_estimator import BillEstimator
from data_processor import DataProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_updated_electricity_estimation():
    """Test the updated electricity estimation logic"""
    
    print("Testing Updated Electricity Estimation System")
    print("=" * 60)
    
    try:
        # Initialize system
        csv_file = 'NYC_Building_Energy_Filtered_Clean.csv'
        data_processor = DataProcessor(csv_file)
        data_processor.load_data()
        
        bill_estimator = BillEstimator(data_processor)
        
        # Test 1: Check default AC cost
        print(f"✓ Default AC cost: ${bill_estimator.default_ac_cost}")
        assert bill_estimator.default_ac_cost == 40, f"Expected 40, got {bill_estimator.default_ac_cost}"
        
        # Test 2: Check zip code AC costs (should be based on 40 as default)
        print(f"✓ Sample zip code costs:")
        print(f"  Manhattan (10001): ${bill_estimator.zip_ac_costs['10001']}")
        print(f"  Brooklyn (11201): ${bill_estimator.zip_ac_costs['11201']}")
        print(f"  Queens (11101): ${bill_estimator.zip_ac_costs['11101']}")
        print(f"  Bronx (10451): ${bill_estimator.zip_ac_costs['10451']}")
        print(f"  Staten Island (10301): ${bill_estimator.zip_ac_costs['10301']}")
        
        # Test 3: Create mock building data
        building_data = {
            'Property Name': 'Test Building',
            'Address 1': '123 Test St',
            'Borough': 'Manhattan',
            'Postal Code': '10001',
            'Year Built': 2010,
            'Property GFA - Calculated (Buildings) (ft²)': 50000,
            'Primary Property Type - Self Selected': 'Multifamily Housing',
            'ENERGY STAR Score': 75
        }
        
        # Test 4: Test the formula calculation
        print("\n" + "=" * 60)
        print("Testing Formula Calculation")
        print("=" * 60)
        
        test_cases = [
            {'rooms': 1, 'bathrooms': 1, 'description': '1-bedroom apartment'},
            {'rooms': 2, 'bathrooms': 1, 'description': '2-bedroom apartment'},
            {'rooms': 3, 'bathrooms': 2, 'description': '3-bedroom apartment'},
            {'rooms': 4, 'bathrooms': 2, 'description': '4-bedroom apartment'}
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['description']}")
            print(f"Rooms: {test_case['rooms']}, Bathrooms: {test_case['bathrooms']}")
            
            # Get monthly estimates
            monthly_estimates = bill_estimator.estimate_monthly_bills(
                building_data=building_data,
                num_rooms=test_case['rooms'],
                num_bathrooms=test_case['bathrooms']
            )
            
            # Check the first month (January) for detailed breakdown
            jan_estimate = monthly_estimates[0]
            
            print(f"Monthly AC Cost (Jan): ${jan_estimate['per_ac_cost']}")
            print(f"Rooms Multiplier: {jan_estimate['rooms_multiplier']} (should be {test_case['rooms']} + 1)")
            print(f"Base Extra Cost: ${jan_estimate['base_extra_cost']}")
            print(f"Energy Rating Cost: ${jan_estimate['energy_rating_cost']}")
            print(f"Total Bill (Jan): ${jan_estimate['estimated_bill']}")
            
            # Verify that rooms multiplier is indeed num_rooms + 1
            expected_multiplier = test_case['rooms'] + 1
            assert jan_estimate['rooms_multiplier'] == expected_multiplier, f"Expected {expected_multiplier}, got {jan_estimate['rooms_multiplier']}"
            
            # Calculate expected total manually
            zip_code = '10001'
            per_ac_cost = bill_estimator.zip_ac_costs[zip_code]
            seasonal_factor = bill_estimator._get_ac_seasonal_factor(1)  # January
            monthly_ac_cost = per_ac_cost * seasonal_factor
            energy_rating_factor = bill_estimator._calculate_energy_rating_factor(building_data, zip_code)
            
            expected_total = (monthly_ac_cost * (test_case['rooms'] + 1)) + 15 + (10 * energy_rating_factor)
            
            print(f"Expected calculation:")
            print(f"  Per AC cost: ${per_ac_cost}")
            print(f"  Seasonal factor: {seasonal_factor}")
            print(f"  Monthly AC cost: ${monthly_ac_cost}")
            print(f"  Formula: (${monthly_ac_cost} * {test_case['rooms'] + 1}) + $15 + ($10 * {energy_rating_factor:.2f})")
            print(f"  Expected total: ${expected_total:.2f}")
            
            # Check if calculated total matches expected (with small tolerance for rounding)
            assert abs(jan_estimate['estimated_bill'] - expected_total) < 0.01, f"Expected {expected_total:.2f}, got {jan_estimate['estimated_bill']}"
            
            print(f"✓ Formula calculation verified!")
            print("-" * 40)
        
        # Test 5: Test cost tiers
        print("\n" + "=" * 60)
        print("Testing Cost Tiers")
        print("=" * 60)
        
        zip_test_cases = [
            {'zip': '10075', 'expected_tier': 'High'},  # 80 - should be High (>= 55)
            {'zip': '10001', 'expected_tier': 'Medium'},  # 50 - should be Medium (35-54)
            {'zip': '10451', 'expected_tier': 'Low'},   # 25 - should be Low (< 35)
        ]
        
        for zip_case in zip_test_cases:
            zip_info = bill_estimator.get_zip_ac_estimate(zip_case['zip'])
            print(f"Zip {zip_case['zip']}: ${zip_info['per_ac_monthly_cost']} - {zip_info['cost_tier']}")
            assert zip_info['cost_tier'] == zip_case['expected_tier'], f"Expected {zip_case['expected_tier']}, got {zip_info['cost_tier']}"
        
        print("\n✅ All tests passed successfully!")
        print("Updated electricity estimation system is working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_api_integration():
    """Test API integration with updated system"""
    import requests
    
    print("\n" + "=" * 60)
    print("Testing API Integration")
    print("=" * 60)
    
    # Test payload
    test_payload = {
        "address": "123 Main St, Manhattan, NY",
        "num_rooms": 2,
        "num_bathrooms": 1
    }
    
    try:
        # Try to call the API
        response = requests.post(
            'http://localhost:62031/api/estimate',
            json=test_payload,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            result = response.json()
            print("✅ API Test Successful!")
            
            # Check key fields
            est_params = result.get('estimation_parameters', {})
            print(f"Rooms: {est_params.get('num_rooms')}")
            print(f"Bathrooms: {est_params.get('num_bathrooms')}")
            print(f"Per AC Cost: ${est_params.get('per_ac_monthly_cost')}")
            
            # Check methodology
            methodology = result.get('methodology', {})
            print(f"Formula: {methodology.get('formula')}")
            
            # Check first month estimate
            monthly_est = result.get('monthly_estimates', [])
            if monthly_est:
                first_month = monthly_est[0]
                print(f"January estimate: ${first_month.get('estimated_bill')}")
                print(f"Rooms multiplier: {first_month.get('rooms_multiplier')}")
                
        else:
            print(f"❌ API Test Failed: Status {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("⚠️  Could not connect to API server - make sure the server is running")
    except Exception as e:
        print(f"❌ API test error: {e}")

if __name__ == "__main__":
    print("Updated Electricity Estimation System Test")
    print("Changes:")
    print("1. Default AC cost: 40 (previously 75)")
    print("2. ZIP AC costs adjusted based on 40 as default")  
    print("3. Formula: Per AC bill * (# rooms + 1) + $15 + $10 * energy rating")
    print("4. Cost tiers: High (>=55), Medium (35-54), Low (<35)")
    print()
    
    # Test the estimator
    if test_updated_electricity_estimation():
        print("\n🎉 Core system tests completed successfully!")
    else:
        print("\n💥 Core system tests failed!")
        sys.exit(1)
    
    # Test API integration
    try:
        test_api_integration()
    except Exception as e:
        print(f"API integration test error: {e}")
    
    print("\n✨ All tests completed!") 