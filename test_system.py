#!/usr/bin/env python3
"""
Test script for the electricity bill estimation system
"""

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_system():
    """Test the complete system functionality"""
    try:
        logger.info("Starting system test...")
        
        # Initialize data processor
        csv_file = 'NYC_Building_Energy_Filtered_Clean.csv'
        data_processor = DataProcessor(csv_file)
        
        if not data_processor.load_data():
            logger.error("Failed to load data")
            return False
        
        logger.info("✓ Data processor initialized successfully")
        
        # Initialize address matcher
        address_matcher = AddressMatcher(data_processor.get_building_data())
        logger.info("✓ Address matcher initialized successfully")
        
        # Initialize bill estimator
        bill_estimator = BillEstimator(data_processor)
        logger.info("✓ Bill estimator initialized successfully")
        
        # Test address search
        test_address = "Pelham"
        search_results = address_matcher.search_buildings(test_address, limit=3)
        logger.info(f"✓ Address search test: Found {len(search_results)} results for '{test_address}'")
        
        if search_results:
            # Test bill estimation with first result
            building = address_matcher.find_building(search_results[0]['full_address'])
            
            if building:
                logger.info(f"✓ Found building: {building.get('Property Name', 'Unknown')}")
                
                # Test bill estimation
                monthly_estimates = bill_estimator.estimate_monthly_bills(
                    building_data=building,
                    num_rooms=2,
                    apartment_type='1br',
                    building_type='residential'
                )
                
                if monthly_estimates:
                    logger.info(f"✓ Bill estimation successful: {len(monthly_estimates)} monthly estimates generated")
                    
                    # Show sample results
                    jan_estimate = monthly_estimates[0]
                    logger.info(f"✓ January estimate: {jan_estimate['kwh_estimate']} kWh, ${jan_estimate['estimated_bill']}")
                    
                    annual_total = sum(est['estimated_bill'] for est in monthly_estimates)
                    logger.info(f"✓ Annual total: ${annual_total:.2f}")
                    
                else:
                    logger.error("Bill estimation failed")
                    return False
            else:
                logger.error("Building lookup failed")
                return False
        else:
            logger.error("No search results found")
            return False
        
        logger.info("🎉 All system tests passed!")
        return True
        
    except Exception as e:
        logger.error(f"System test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_system()
    exit(0 if success else 1)
