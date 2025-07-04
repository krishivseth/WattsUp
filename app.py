from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
from datetime import datetime
import os
import socket

from data_processor import DataProcessor
from bill_estimator import BillEstimator
from address_matcher import AddressMatcher
from safety_analyzer import SafetyAnalyzer
from route_analyzer import RouteAnalyzer
from reviews_analyzer import ReviewsAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=['*'], allow_headers=['Content-Type'], methods=['GET', 'POST', 'OPTIONS'])  # Enable CORS for web extension

# Initialize components
data_processor = None
bill_estimator = None
address_matcher = None
safety_analyzer = None
route_analyzer = None
reviews_analyzer = None

def initialize_system():
    """Initialize all system components"""
    global data_processor, bill_estimator, address_matcher, safety_analyzer, route_analyzer, reviews_analyzer
    
    try:
        logger.info("Initializing backend system...")
        
        # Define Google API Key
        google_api_key = "AIzaSyALD1d2zJpPqOE0e_E5rrx7JiMdAUUmfds"
        
        # Load and process CSV data
        csv_file = 'NYC_Building_Energy_Filtered_Clean.csv'
        data_processor = DataProcessor(csv_file)
        data_processor.load_data()
        
        # Initialize address matcher
        address_matcher = AddressMatcher(data_processor.get_building_data())
        
        # Initialize bill estimator
        bill_estimator = BillEstimator(data_processor)
        
        # Initialize safety analyzer with API key (no local file needed - uses NYC Open Data API)
        # Data will be loaded on-demand per borough when safety analysis is requested
        safety_analyzer = SafetyAnalyzer(google_api_key=google_api_key)
        
        # Initialize route analyzer with the safety analyzer instance
        route_analyzer = RouteAnalyzer(safety_analyzer, google_api_key)
        
        # Initialize reviews analyzer with Google API key and OpenAI key
        openai_api_key = os.getenv('OPENAI_API_KEY')  # Get from environment variables
        reviews_analyzer = ReviewsAnalyzer(google_api_key, openai_api_key)
        
        logger.info("Backend system initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        return False

def find_free_port():
    """Find an available port on the host."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

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
    Main endpoint for AC-based electricity bill estimation
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY",
        "num_rooms": 3,
        "num_bathrooms": 1, // optional - will be estimated if not provided
        "apartment_type": "2br", // optional
        "building_type": "residential", // optional
        "include_demand_charges": true // optional (legacy parameter)
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
        num_bathrooms = data.get('num_bathrooms', None)
        apartment_type = data.get('apartment_type', None)
        building_type = data.get('building_type', 'residential')
        include_demand_charges = data.get('include_demand_charges', False)  # Legacy parameter
        
        # Find matching building
        building_match = address_matcher.find_building(address)
        if not building_match:
            return jsonify({'error': 'Building not found in database'}), 404
        
        # Estimate bathrooms if not provided
        if num_bathrooms is None:
            num_bathrooms = bill_estimator.estimate_bathroom_count(num_rooms, apartment_type)
        
        # Generate monthly estimates using new AC-based logic
        monthly_estimates = bill_estimator.estimate_monthly_bills(
            building_data=building_match,
            num_rooms=num_rooms,
            apartment_type=apartment_type,
            building_type=building_type,
            include_demand_charges=include_demand_charges,
            num_bathrooms=num_bathrooms
        )
        
        # Calculate annual summary
        annual_bill = sum(est['estimated_bill'] for est in monthly_estimates)
        
        peak_month_data = max(monthly_estimates, key=lambda x: x['estimated_bill'])
        lowest_month_data = min(monthly_estimates, key=lambda x: x['estimated_bill'])
        
        # Get zip code and AC info
        zip_code = bill_estimator._extract_zip_code(building_match)
        ac_info = bill_estimator.get_zip_ac_estimate(zip_code)
        
        # Calculate AC units for display
        num_ac_units = max(1, num_rooms - num_bathrooms)
        
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
                'building_efficiency': bill_estimator.get_building_efficiency_rating(building_match),
                'zip_code': zip_code
            },
            'estimation_parameters': {
                'num_rooms': num_rooms,
                'num_bathrooms': num_bathrooms,
                'num_ac_units': num_ac_units,
                'per_ac_monthly_cost': ac_info['per_ac_monthly_cost'],
                'cost_tier': ac_info['cost_tier'],
                'energy_rating_factor': bill_estimator._calculate_energy_rating_factor(building_match, zip_code),
                'base_extra_cost': bill_estimator.base_extra_cost,
                'energy_rating_multiplier': bill_estimator.energy_rating_multiplier
            },
            'monthly_estimates': monthly_estimates,
            'annual_summary': {
                'total_bill': round(annual_bill, 2),
                'average_monthly_bill': round(annual_bill / 12, 2),
                'peak_month': peak_month_data['month'],
                'peak_bill': peak_month_data['estimated_bill'],
                'lowest_month': lowest_month_data['month'],
                'lowest_bill': lowest_month_data['estimated_bill']
            },
            'rate_structure': bill_estimator.get_rate_structure(building_match),
            'methodology': {
                'model': 'AC-based estimation',
                'formula': 'Total bill = Per AC bill * (# rooms + 1) + $15 extra + $10 * (energy rating factor)',
                'data_source': 'NYC Building Energy Data + Zip-level AC cost estimates',
                'year': '2024',
                'seasonal_adjustment': True,
                'building_efficiency_considered': True,
                'neighborhood_factor_included': True
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

@app.route('/api/safety', methods=['POST'])
def get_safety_rating():
    """
    Get safety rating for a specific area
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY", // optional
        "zip_code": "10001", // optional
        "borough": "Manhattan", // optional
        "radius_miles": 0.5 // optional, default 0.5
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Extract parameters
        address = data.get('address')
        zip_code = data.get('zip_code')
        borough = data.get('borough')
        radius_miles = float(data.get('radius_miles', 0.5))
        
        # Validate that at least one location parameter is provided
        if not any([address, zip_code, borough]):
            return jsonify({'error': 'At least one location parameter (address, zip_code, or borough) is required'}), 400
        
        # Get safety rating
        safety_analysis = safety_analyzer.get_area_safety_rating(
            zip_code=zip_code,
            borough=borough,
            address=address,
            radius_miles=radius_miles
        )
        
        return jsonify(safety_analysis)
        
    except ValueError as e:
        return jsonify({'error': f'Invalid input: {e}'}), 400
    except Exception as e:
        logger.error(f"Safety analysis error: {e}")
        return jsonify({'error': 'Safety analysis failed'}), 500

@app.route('/api/safety/borough-comparison', methods=['GET'])
def get_borough_safety_comparison():
    """Get safety comparison across all NYC boroughs"""
    try:
        comparison = safety_analyzer.get_borough_comparison()
        
        return jsonify({
            'borough_comparison': comparison,
            'data_source': 'NYC 311 Service Requests',
            'methodology': 'Complaints categorized by safety severity and weighted scoring'
        })
        
    except Exception as e:
        logger.error(f"Borough comparison error: {e}")
        return jsonify({'error': 'Borough comparison failed'}), 500

@app.route('/api/safety/refresh', methods=['POST'])
def refresh_safety_data():
    """Force refresh of safety data from NYC Open Data API"""
    try:
        data = request.get_json() or {}
        borough = data.get('borough')  # Optional borough filter
        
        success = safety_analyzer.refresh_data(borough=borough)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': f'Safety data refreshed successfully{" for " + borough if borough else ""}',
                'borough': borough,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'status': 'error', 
                'message': 'Failed to refresh safety data'
            }), 500
            
    except Exception as e:
        logger.error(f"Safety data refresh error: {e}")
        return jsonify({'error': 'Safety data refresh failed'}), 500

@app.route('/api/safe-routes', methods=['POST'])
def analyze_safe_routes():
    """
    Analyze safe routes between two locations
    
    Expected JSON payload:
    {
        "origin": "123 Main St, Queens, NY",
        "destination": "456 Broadway, Manhattan, NY",
        "mode": "driving", // optional: driving, walking, transit
        "alternatives": true // optional: get multiple route options
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['origin', 'destination']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        origin = data['origin']
        destination = data['destination']
        mode = data.get('mode', 'driving')
        
        # Analyze safe routes
        route_analysis = route_analyzer.analyze_safe_routes(
            origin=origin,
            destination=destination,
            mode=mode
        )
        
        # Check for errors
        if 'error' in route_analysis:
            return jsonify(route_analysis), 500
        
        return jsonify(route_analysis)
        
    except Exception as e:
        logger.error(f"Safe route analysis error: {e}")
        return jsonify({'error': 'Route analysis failed'}), 500

@app.route('/api/reviews', methods=['POST'])
def get_building_reviews():
    """
    Analyze Google Reviews for an apartment building
    
    Expected JSON payload:
    {
        "address": "123 Main St, Queens, NY",
        "building_name": "Optional Building Name"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'address' not in data:
            return jsonify({'error': 'Address is required'}), 400
        
        address = data['address']
        building_name = data.get('building_name', None)
        
        # Analyze building reviews
        result = reviews_analyzer.analyze_building_reviews(address, building_name)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Reviews analysis error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    if initialize_system():
        port = 62031
        try:
            # Check if port is in use
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
        except OSError:
            logger.warning(f"Port {port} is in use, finding an available port...")
            port = find_free_port()
            
        logger.info(f"Starting Flask application on port {port}...")
        app.run(debug=False, host='0.0.0.0', port=port)
    else:
        logger.error("Failed to start application - initialization failed")
