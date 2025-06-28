import requests
import logging
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class RouteAnalyzer:
    """Analyzes routes for safety by combining Google Directions API with safety data"""
    
    def __init__(self, safety_analyzer, google_maps_api_key: str = None):
        self.safety_analyzer = safety_analyzer
        self.google_maps_api_key = google_maps_api_key or "YOUR_GOOGLE_MAPS_API_KEY"
        self.directions_url = "https://maps.googleapis.com/maps/api/directions/json"
        
    def analyze_safe_routes(self, origin: str, destination: str, mode: str = 'driving') -> Dict:
        """Analyze multiple routes and rate them by safety"""
        try:
            # Get route alternatives from Google Directions API
            routes = self._get_route_alternatives(origin, destination, mode)
            
            if not routes:
                return self._create_error_response("No routes found")
            
            # Analyze safety for each route
            analyzed_routes = []
            for i, route in enumerate(routes):
                analyzed_route = self._analyze_route_safety(route, i)
                analyzed_routes.append(analyzed_route)
            
            # Sort routes by type preference
            sorted_routes = self._categorize_and_sort_routes(analyzed_routes)
            
            # Generate recommendation
            recommendation = self._generate_recommendation(sorted_routes)
            
            return {
                'origin_address': origin,
                'destination_address': destination,
                'routes': sorted_routes,
                'analysis_timestamp': datetime.now().isoformat(),
                'total_routes_analyzed': len(sorted_routes),
                'recommendation': recommendation
            }
            
        except Exception as e:
            logger.error(f"Route analysis failed: {e}")
            return self._create_error_response(f"Route analysis failed: {str(e)}")
    
    def _get_route_alternatives(self, origin: str, destination: str, mode: str) -> List[Dict]:
        """Get route alternatives from Google Directions API"""
        try:
            params = {
                'origin': origin,
                'destination': destination,
                'mode': mode,
                'alternatives': 'true',
                'key': self.google_maps_api_key
            }
            
            response = requests.get(self.directions_url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Google Directions API error: {response.status_code}")
                return []
            
            data = response.json()
            
            if data['status'] != 'OK':
                logger.error(f"Google Directions API status: {data['status']}")
                return []
            
            return data.get('routes', [])
            
        except Exception as e:
            logger.error(f"Failed to get route alternatives: {e}")
            return []
    
    def _analyze_route_safety(self, google_route: Dict, route_index: int) -> Dict:
        """Analyze safety for a single route"""
        try:
            legs = google_route.get('legs', [])
            if not legs:
                return None
            
            # Extract route segments and analyze safety
            segments = []
            total_safety_score = 0
            total_distance = 0
            
            for leg in legs:
                steps = leg.get('steps', [])
                for step in steps:
                    segment = self._create_route_segment(step)
                    if segment:
                        segments.append(segment)
                        # Weight safety score by distance
                        distance_weight = segment['distance']['value']
                        total_safety_score += segment['safety_score'] * distance_weight
                        total_distance += distance_weight
            
            # Calculate overall safety score
            overall_safety_score = total_safety_score / total_distance if total_distance > 0 else 3.0
            overall_safety_grade = self._score_to_grade(overall_safety_score)
            
            # Extract route summary
            route_summary = google_route.get('summary', f'Route {route_index + 1}')
            total_duration = legs[0].get('duration', {})
            route_distance = legs[0].get('distance', {})
            
            # Generate route description
            safety_description = self._generate_safety_description(overall_safety_score, len(segments))
            
            return {
                'route_id': f'route_{route_index}',
                'summary': route_summary,
                'total_duration': total_duration,
                'total_distance': route_distance,
                'overall_safety_score': round(overall_safety_score, 2),
                'overall_safety_grade': overall_safety_grade,
                'safety_description': safety_description,
                'segments': segments,
                'polyline': google_route.get('overview_polyline', {}).get('points', ''),
                'route_type': 'analyzed',  # Will be categorized later
                'warnings': self._generate_warnings(overall_safety_score)
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze route safety: {e}")
            return None
    
    def _create_route_segment(self, step: Dict) -> Optional[Dict]:
        """Create a route segment with safety analysis"""
        try:
            start_location = step.get('start_location', {})
            end_location = step.get('end_location', {})
            
            # Get approximate ZIP code or borough for this segment
            # For simplicity, we'll use a basic approach
            lat = (start_location.get('lat', 0) + end_location.get('lat', 0)) / 2
            lng = (start_location.get('lng', 0) + end_location.get('lng', 0)) / 2
            
            # Estimate safety based on coordinates (simplified)
            borough = self._estimate_borough_from_coords(lat, lng)
            safety_score = self._estimate_safety_from_coords(lat, lng, borough)
            
            return {
                'start_location': start_location,
                'end_location': end_location,
                'duration': step.get('duration', {}),
                'distance': step.get('distance', {}),
                'safety_score': safety_score,
                'safety_grade': self._score_to_grade(safety_score),
                'neighborhood_info': {
                    'borough': borough,
                    'complaint_count': 0  # Simplified
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to create route segment: {e}")
            return None
    
    def _estimate_borough_from_coords(self, lat: float, lng: float) -> str:
        """Estimate NYC borough from coordinates (simplified)"""
        # Very rough borough boundaries for NYC
        if lat > 40.8 and lng > -73.9:
            return 'BRONX'
        elif lat < 40.7 and lng < -74.0:
            return 'STATEN ISLAND'
        elif lat < 40.7 and lng > -73.9:
            return 'BROOKLYN'
        elif lng < -73.9:
            return 'QUEENS'
        else:
            return 'MANHATTAN'
    
    def _estimate_safety_from_coords(self, lat: float, lng: float, borough: str) -> float:
        """Estimate safety score based on coordinates and borough"""
        # Get borough-level safety data if available
        if hasattr(self.safety_analyzer, 'get_borough_comparison'):
            borough_data = self.safety_analyzer.get_borough_comparison()
            if borough in borough_data:
                return borough_data[borough]['safety_score']
        
        # Default safety scores by borough (based on general knowledge)
        borough_safety = {
            'MANHATTAN': 4.0,
            'BROOKLYN': 3.5,
            'QUEENS': 3.8,
            'BRONX': 3.2,
            'STATEN ISLAND': 4.2
        }
        
        return borough_safety.get(borough, 3.5)
    
    def _categorize_and_sort_routes(self, routes: List[Dict]) -> List[Dict]:
        """Categorize routes as safest, balanced, or fastest"""
        if not routes:
            return []
        
        # Sort by safety score (descending)
        routes_by_safety = sorted(routes, key=lambda r: r['overall_safety_score'], reverse=True)
        
        # Sort by duration (ascending)
        routes_by_speed = sorted(routes, key=lambda r: r['total_duration']['value'])
        
        # Assign route types
        categorized_routes = []
        
        # Safest route
        if routes_by_safety:
            safest = routes_by_safety[0].copy()
            safest['route_type'] = 'safest'
            categorized_routes.append(safest)
        
        # Fastest route (if different from safest)
        if routes_by_speed and routes_by_speed[0]['route_id'] != routes_by_safety[0]['route_id']:
            fastest = routes_by_speed[0].copy()
            fastest['route_type'] = 'fastest'
            categorized_routes.append(fastest)
        
        # Balanced route (if we have 3+ routes)
        if len(routes) >= 3:
            # Find a route that's neither the safest nor fastest
            for route in routes:
                if (route['route_id'] != routes_by_safety[0]['route_id'] and 
                    route['route_id'] != routes_by_speed[0]['route_id']):
                    balanced = route.copy()
                    balanced['route_type'] = 'balanced'
                    categorized_routes.append(balanced)
                    break
        
        return categorized_routes
    
    def _generate_recommendation(self, routes: List[Dict]) -> Dict:
        """Generate route recommendation"""
        if not routes:
            return {'recommended_route_id': '', 'reason': 'No routes available'}
        
        # Find the best balanced option
        safest_route = next((r for r in routes if r['route_type'] == 'safest'), None)
        fastest_route = next((r for r in routes if r['route_type'] == 'fastest'), None)
        balanced_route = next((r for r in routes if r['route_type'] == 'balanced'), None)
        
        # Recommendation logic
        if safest_route and safest_route['overall_safety_score'] >= 4.0:
            return {
                'recommended_route_id': safest_route['route_id'],
                'reason': f"Recommended for excellent safety (Grade {safest_route['overall_safety_grade']}) with only a small time difference."
            }
        elif balanced_route:
            return {
                'recommended_route_id': balanced_route['route_id'],
                'reason': "Recommended for the best balance of safety and travel time."
            }
        elif fastest_route:
            return {
                'recommended_route_id': fastest_route['route_id'],
                'reason': "Fastest available option. Consider safety precautions during travel."
            }
        else:
            return {
                'recommended_route_id': routes[0]['route_id'],
                'reason': "Default route option."
            }
    
    def _generate_safety_description(self, safety_score: float, segment_count: int) -> str:
        """Generate human-readable safety description"""
        if safety_score >= 4.5:
            return f"Excellent safety route through {segment_count} low-risk areas"
        elif safety_score >= 3.5:
            return f"Generally safe route with good neighborhood ratings"
        elif safety_score >= 2.5:
            return f"Moderate safety route - stay alert during travel"
        elif safety_score >= 1.5:
            return f"Some safety concerns along this route"
        else:
            return f"Higher risk route - consider alternatives if possible"
    
    def _generate_warnings(self, safety_score: float) -> List[str]:
        """Generate safety warnings for low-score routes"""
        warnings = []
        
        if safety_score < 3.0:
            warnings.append("This route passes through areas with higher crime reports")
        
        if safety_score < 2.0:
            warnings.append("Consider traveling during daylight hours")
            warnings.append("Stay aware of your surroundings")
        
        return warnings
    
    def _score_to_grade(self, score: float) -> str:
        """Convert numerical safety score to letter grade"""
        if score >= 4.5:
            return 'A'
        elif score >= 3.5:
            return 'B'
        elif score >= 2.5:
            return 'C'
        elif score >= 1.5:
            return 'D'
        else:
            return 'F'
    
    def _create_error_response(self, message: str) -> Dict:
        """Create error response"""
        return {
            'error': message,
            'origin_address': '',
            'destination_address': '',
            'routes': [],
            'analysis_timestamp': datetime.now().isoformat(),
            'total_routes_analyzed': 0,
            'recommendation': {
                'recommended_route_id': '',
                'reason': 'No routes available due to error'
            }
        } 