from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import os

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for web extension

# Initialize components
data_processor = None
bill_estimator = None
address_matcher = None

def initialize_system():
    """Initialize all system components"""
    global data_processor, bill_estimator, address_matcher
    
    try:
        logger.info("Initializing backend system...")
        
        # Load and process CSV data
        csv_file = 'NYC_Building_Energy_Filtered_Clean.csv'
        data_processor = DataProcessor(csv_file)
        data_processor.load_data()
        
        # Initialize address matcher
        address_matcher = AddressMatcher(data_processor.get_building_data())
        
        # Initialize bill estimator
        bill_estimator = BillEstimator(data_processor)
        
        logger.info("Backend system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        return False

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

@app.route('/api/estimate', methods=['POST'])
def estimate_bill():
    """
    Main endpoint for electricity bill estimation
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY",
        "num_rooms": 3,
        "apartment_type": "2br", // optional
        "building_type": "residential", // optional
        "include_demand_charges": true // optional
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['address', 'num_rooms']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        address = data['address']
        num_rooms = int(data['num_rooms'])
        apartment_type = data.get('apartment_type', None)
        building_type = data.get('building_type', 'residential')
        include_demand_charges = data.get('include_demand_charges', False)
        
        # Find matching building
        building_match = address_matcher.find_building(address)
        if not building_match:
            return jsonify({'error': 'Building not found in database'}), 404
        
        # Generate monthly estimates
        monthly_estimates = bill_estimator.estimate_monthly_bills(
            building_data=building_match,
            num_rooms=num_rooms,
            apartment_type=apartment_type,
            building_type=building_type,
            include_demand_charges=include_demand_charges
        )
        
        # Calculate annual summary
        annual_kwh = sum(est['kwh_estimate'] for est in monthly_estimates)
        annual_bill = sum(est['estimated_bill'] for est in monthly_estimates)
        
        peak_month_data = max(monthly_estimates, key=lambda x: x['estimated_bill'])
        lowest_month_data = min(monthly_estimates, key=lambda x: x['estimated_bill'])
        
        # Prepare response
        response = {
            'building_info': {
                'property_name': building_match.get('Property Name', ''),
                'address': building_match.get('Address 1', ''),
                'city': building_match.get('City', ''),
                'borough': building_match.get('Borough', ''),
                'property_type': building_match.get('Primary Property Type - Self Selected', ''),
                'year_built': building_match.get('Year Built', ''),
                'total_gfa': building_match.get('Property GFA - Calculated (Buildings) (ft²)', ''),
                'occupancy_rate': building_match.get('Occupancy', ''),
                'building_efficiency': bill_estimator.get_building_efficiency_rating(building_match)
            },
            'estimation_parameters': {
                'num_rooms': num_rooms,
                'estimated_apartment_sqft': bill_estimator.estimate_apartment_size(num_rooms, building_type),
                'building_intensity_kwh_per_sqft': building_match.get('Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)', 0),
                'efficiency_factor': bill_estimator.calculate_efficiency_factor(building_match.get('Year Built', 2000)),
                'occupancy_factor': float(building_match.get('Occupancy', 100)) / 100.0 if building_match.get('Occupancy') else 1.0
            },
            'monthly_estimates': monthly_estimates,
            'annual_summary': {
                'total_kwh': round(annual_kwh, 0),
                'total_bill': round(annual_bill, 2),
                'average_monthly_bill': round(annual_bill / 12, 2),
                'peak_month': peak_month_data['month'],
                'peak_bill': peak_month_data['estimated_bill'],
                'lowest_month': lowest_month_data['month'],
                'lowest_bill': lowest_month_data['estimated_bill']
            },
            'rate_structure': bill_estimator.get_rate_structure(building_match),
            'methodology': {
                'data_source': 'NYC Building Energy and Water Data Disclosure',
                'year': '2022',
                'weather_normalized': True,
                'building_efficiency_considered': True,
                'occupancy_adjusted': True,
                'includes_seasonality': True
            }
        }
        
        return jsonify(response)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        logger.error(f"Estimation error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/search', methods=['GET'])
def search_buildings():
    """
    Search for buildings by partial address
    
    Query parameters:
    - q: search query (address fragment)
    - limit: maximum results (default 10)
    """
    try:
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
        
        if not query:
            return jsonify({'error': 'Search query required'}), 400
        
        # Search for matching buildings
        matches = address_matcher.search_buildings(query, limit)
        
        return jsonify({
            'query': query,
            'results': matches,
            'count': len(matches)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({'error': 'Search failed'}), 500

@app.route('/api/building/<property_id>', methods=['GET'])
def get_building_details(property_id):
    """Get detailed information about a specific building"""
    try:
        building = data_processor.get_building_by_id(property_id)
        if not building:
            return jsonify({'error': 'Building not found'}), 404
        
        return jsonify(building)
        
    except Exception as e:
        logger.error(f"Building lookup error: {e}")
        return jsonify({'error': 'Building lookup failed'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    if initialize_system():
        logger.info("Starting Flask application...")
        app.run(debug=True, host='0.0.0.0', port=5002)
    else:
        logger.error("Failed to start application - initialization failed")
