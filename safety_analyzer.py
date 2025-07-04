import json
import pandas as pd
import numpy as np
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import time

logger = logging.getLogger(__name__)

def _haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points on Earth in miles"""
    R = 3958.8  # Earth radius in miles
    
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)
    
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    
    a = np.sin(dlat / 2)**2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    
    return R * c

class SafetyAnalyzer:
    """Analyzes NYC crime data to provide safety ratings and summaries for specific areas"""
    
    def __init__(self, crime_data_file: str = None, google_api_key: str = None):
        # NYC Open Data API endpoint for 311 service requests
        self.api_base_url = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
        self.crime_data = None
        self.data_cache = None
        self.cache_timestamp = None
        self.cache_duration = 3600  # Cache for 1 hour
        self.safety_categories = self._define_safety_categories()
        self.google_api_key = google_api_key
        
    def _geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """Geocode an address to get latitude and longitude using Google Maps API"""
        if not self.google_api_key:
            logger.warning("Google API key not configured for geocoding")
            return None
        
        try:
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params={'address': address, 'key': self.google_api_key}
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return location['lat'], location['lng']
            else:
                logger.warning(f"Geocoding failed for '{address}': {data['status']}")
                return None
        except requests.RequestException as e:
            logger.error(f"Geocoding request failed: {e}")
            return None

    def _define_safety_categories(self) -> Dict[str, Dict]:
        """Define safety categories and their severity weights"""
        return {
            'HIGH_CONCERN': {
                'weight': 3.0,
                'types': [
                    'Drug Activity',
                    'Non-Emergency Police Matter',
                    'Criminal Mischief',
                    'Harassment',
                    'Assault',
                    'Robbery',
                    'Burglary',
                    'Theft',
                    'Vandalism',
                    'Weapon'
                ],
                'description': 'Serious safety concerns requiring immediate attention'
            },
            'MEDIUM_CONCERN': {
                'weight': 2.0,
                'types': [
                    'Panhandling',
                    'Homeless Person Assistance',
                    'Abandoned Vehicle',
                    'Illegal Fireworks',
                    'Illegal Dumping',
                    'Public Urination',
                    'Disorderly Conduct'
                ],
                'description': 'Moderate safety and quality-of-life concerns'
            },
            'LOW_CONCERN': {
                'weight': 1.0,
                'types': [
                    'Noise - Residential',
                    'Noise - Street/Sidewalk',
                    'Noise - Commercial',
                    'Noise - Vehicle',
                    'Noise - Helicopter',
                    'Noise - Park',
                    'Noise',
                    'Illegal Parking',
                    'Blocked Driveway',
                    'Traffic',
                    'For Hire Vehicle Complaint',
                    'Taxi Complaint'
                ],
                'description': 'Minor quality-of-life issues with minimal safety impact'
            },
            'INFRASTRUCTURE': {
                'weight': 0.5,
                'types': [
                    'Street Condition',
                    'Sidewalk Condition',
                    'Traffic Signal Condition',
                    'Street Light Condition',
                    'Street Sign - Damaged',
                    'Damaged Tree',
                    'Water System',
                    'Sewer',
                    'Standing Water',
                    'Dirty Condition',
                    'Rodent',
                    'Maintenance or Facility',
                    'Residential Disposal Complaint'
                ],
                'description': 'Infrastructure and maintenance issues'
            }
        }
    
    def load_data(self, borough: str = None) -> bool:
        """Load and process crime data from NYC Open Data API"""
        try:
            # Check if we have cached data that's still fresh and for the same borough
            if self._is_cache_valid(borough):
                logger.info(f"Using cached crime data{' for ' + borough if borough else ''}")
                self.crime_data = self.data_cache.copy()
                return True
            
            logger.info(f"Fetching fresh crime data from NYC Open Data API{' for ' + borough if borough else ''}...")
            
            # Fetch data from API
            raw_data = self._fetch_from_api(borough=borough)
            if not raw_data:
                logger.error("Failed to fetch data from API")
                return False
            
            # Convert to DataFrame for easier analysis
            self.crime_data = pd.DataFrame(raw_data)
            
            # Clean and process data
            self._clean_data()
            
            # Cache the processed data with borough info
            self.data_cache = self.crime_data.copy()
            self.cache_timestamp = time.time()
            self.cached_borough = borough
            
            logger.info(f"Loaded {len(self.crime_data)} crime reports from API{' for ' + borough if borough else ''}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load crime data: {e}")
            # If API fails, create a minimal fallback dataset
            logger.info("Creating fallback safety data...")
            self._create_fallback_data()
            return True
    
    def _is_cache_valid(self, borough: str = None) -> bool:
        """Check if cached data is still valid for the requested borough"""
        if self.data_cache is None or self.cache_timestamp is None:
            return False
        
        # Check if time is still valid
        if (time.time() - self.cache_timestamp) >= self.cache_duration:
            return False
        
        # Check if borough matches (None means all boroughs)
        cached_borough = getattr(self, 'cached_borough', None)
        if borough != cached_borough:
            return False
        
        return True
    
    def _fetch_from_api(self, months_back: int = 6, borough: str = None) -> Optional[List[Dict]]:
        """Fetch crime data from NYC Open Data API"""
        try:
            # Calculate date range (last 6 months by default)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            
            # Format dates for the API
            start_date_str = start_date.strftime("%Y-%m-%dT00:00:00")
            end_date_str = end_date.strftime("%Y-%m-%dT23:59:59")
            
            # Build the WHERE clause
            where_clauses = [
                f'`created_date` BETWEEN "{start_date_str}" :: floating_timestamp AND "{end_date_str}" :: floating_timestamp'
            ]
            
            # Add borough filter if specified
            if borough:
                # Normalize borough name for API query
                borough_normalized = self._normalize_borough_name(borough)
                where_clauses.append(f"UPPER(`borough`) = '{borough_normalized}'")
            
            where_clause = ' AND '.join(where_clauses)
            
            # Build the SQL query for the API
            query = f"""SELECT
                `unique_key`,
                `created_date`,
                `closed_date`,
                `agency`,
                `agency_name`,
                `complaint_type`,
                `descriptor`,
                `location_type`,
                `incident_zip`,
                `incident_address`,
                `street_name`,
                `borough`,
                `latitude`,
                `longitude`,
                `status`,
                `resolution_description`
            WHERE
                {where_clause}
            ORDER BY `created_date` DESC"""
            
            # Make API request
            params = {
                '$query': query,
            }
            
            logger.info(f"Fetching data from {start_date_str} to {end_date_str}{' for ' + borough if borough else ''}")
            response = requests.get(self.api_base_url, params=params, timeout=60)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched {len(data)} records from API{' for ' + borough if borough else ''}")
            
            return data
            
        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error processing API response: {e}")
            return None
    
    def refresh_data(self, borough: str = None) -> bool:
        """Force refresh of crime data from API (ignores cache)"""
        logger.info(f"Force refreshing crime data from API{' for ' + borough if borough else ''}...")
        self.data_cache = None
        self.cache_timestamp = None
        if hasattr(self, 'cached_borough'):
            delattr(self, 'cached_borough')
        return self.load_data(borough=borough)
    
    def _normalize_borough_name(self, borough: str) -> str:
        """Normalize borough name for consistent API queries"""
        if not borough:
            return ""
        
        # Convert to uppercase and strip whitespace
        borough_upper = borough.upper().strip()
        
        # Handle various borough name formats
        borough_mapping = {
            'MANHATTAN': 'MANHATTAN',
            'NEW YORK': 'MANHATTAN',
            'NY': 'MANHATTAN',
            'BROOKLYN': 'BROOKLYN',
            'KINGS': 'BROOKLYN',
            'QUEENS': 'QUEENS',
            'BRONX': 'BRONX',
            'THE BRONX': 'BRONX',
            'STATEN ISLAND': 'STATEN ISLAND',
            'RICHMOND': 'STATEN ISLAND',
            'SI': 'STATEN ISLAND'
        }
        
        return borough_mapping.get(borough_upper, borough_upper)
    
    def _create_fallback_data(self):
        """Create minimal fallback data when API is unavailable"""
        # Create empty DataFrame with required columns
        columns = [
            'unique_key', 'created_date', 'complaint_type', 'borough', 
            'incident_zip', 'latitude', 'longitude', 'safety_category', 'safety_weight'
        ]
        self.crime_data = pd.DataFrame(columns=columns)
        logger.info("Created fallback safety data (empty dataset)")
    
    def _clean_data(self):
        """Clean and normalize the crime data"""
        # Convert date columns
        date_columns = ['created_date', 'closed_date', 'resolution_action_updated_date']
        for col in date_columns:
            if col in self.crime_data.columns:
                self.crime_data[col] = pd.to_datetime(self.crime_data[col], errors='coerce')
        
        # Clean string columns
        string_columns = ['complaint_type', 'borough', 'incident_zip', 'city']
        for col in string_columns:
            if col in self.crime_data.columns:
                self.crime_data[col] = self.crime_data[col].astype(str).str.strip()
        
        # Convert coordinates to numeric
        if 'latitude' in self.crime_data.columns:
            self.crime_data['latitude'] = pd.to_numeric(self.crime_data['latitude'], errors='coerce')
        if 'longitude' in self.crime_data.columns:
            self.crime_data['longitude'] = pd.to_numeric(self.crime_data['longitude'], errors='coerce')
        
        # Categorize complaints by safety level
        self.crime_data['safety_category'] = self.crime_data['complaint_type'].apply(self._categorize_complaint)
        self.crime_data['safety_weight'] = self.crime_data['safety_category'].apply(
            lambda x: self.safety_categories[x]['weight'] if x in self.safety_categories else 0.5
        )
    
    def _categorize_complaint(self, complaint_type: str) -> str:
        """Categorize complaint type by safety severity"""
        if pd.isna(complaint_type):
            return 'INFRASTRUCTURE'
        
        for category, info in self.safety_categories.items():
            if complaint_type in info['types']:
                return category
        
        # Default category for uncategorized complaints
        return 'INFRASTRUCTURE'
    
    def get_area_safety_rating(self, zip_code: str = None, borough: str = None, 
                              address: str = None, radius_miles: float = 0.5) -> Dict:
        """Get comprehensive safety rating for a specific area"""
        try:
            # Load data for the specific borough if not already loaded
            if not hasattr(self, 'crime_data') or self.crime_data is None:
                self.load_data(borough=borough)
            elif borough and hasattr(self, 'cached_borough') and self.cached_borough != borough:
                # If we have data for a different borough, refresh for the requested borough
                self.load_data(borough=borough)
            
            # Filter data based on area criteria
            area_data = self._filter_area_data(zip_code, borough, address, radius_miles)
            
            if area_data.empty:
                # If no data, try to provide a basic rating based on borough/zip
                if self.crime_data.empty:  # Fallback mode - API was unavailable
                    return self._create_fallback_rating(zip_code, borough, address)
                else:
                    return self._create_default_rating("No crime data available for this area")
            
            # Calculate safety metrics
            safety_metrics = self._calculate_safety_metrics(area_data)
            
            # Generate safety rating
            safety_rating = self._generate_safety_rating(safety_metrics)
            
            # Create safety summary
            safety_summary = self._create_safety_summary(area_data, safety_metrics, safety_rating)
            
            return {
                'area_info': {
                    'zip_code': zip_code,
                    'borough': borough,
                    'address': address,
                    'radius_miles': radius_miles,
                    'data_points': len(area_data)
                },
                'safety_rating': safety_rating,
                'safety_metrics': safety_metrics,
                'safety_summary': safety_summary,
                'complaint_breakdown': self._get_complaint_breakdown(area_data),
                'recent_activity': self._get_recent_activity(area_data),
                'recommendations': self._generate_recommendations(safety_rating, safety_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating safety rating: {e}")
            return self._create_default_rating("Error calculating safety rating")
    
    def _filter_area_data(self, zip_code: str, borough: str, address: str, radius_miles: float) -> pd.DataFrame:
        """Filter crime data for specific area"""
        filtered_data = self.crime_data.copy()
        
        # If an address is provided, use geocoding for precise filtering
        if address and self.google_api_key:
            coords = self._geocode_address(address)
            if coords:
                lat, lon = coords
                # Calculate distances and filter by radius
                distances = _haversine_distance(
                    lat, lon,
                    filtered_data['latitude'], filtered_data['longitude']
                )
                return filtered_data[distances <= radius_miles].copy()

        # Fallback to broader filters if geocoding fails or is not used
        if zip_code:
            filtered_data = filtered_data[filtered_data['incident_zip'] == str(zip_code)]
        
        if borough:
            borough_upper = borough.upper()
            filtered_data = filtered_data[filtered_data['borough'].str.upper() == borough_upper]
        
        return filtered_data
    
    def _calculate_safety_metrics(self, area_data: pd.DataFrame) -> Dict:
        """Calculate various safety metrics for the area"""
        total_complaints = len(area_data)
        
        if total_complaints == 0:
            return {
                'total_complaints': 0,
                'weighted_safety_score': 5.0,
                'complaints_per_day': 0,
                'high_concern_ratio': 0,
                'category_distribution': {}
            }
        
        # Calculate weighted safety score (lower is better)
        weighted_score = area_data['safety_weight'].sum() / total_complaints
        
        # Convert to 1-5 scale (5 being safest)
        safety_score = max(1.0, 5.0 - (weighted_score * 1.5))
        
        # Calculate time-based metrics
        if 'created_date' in area_data.columns:
            date_range = (area_data['created_date'].max() - area_data['created_date'].min()).days or 1
            complaints_per_day = total_complaints / max(date_range, 1)
        else:
            complaints_per_day = 0
        
        # Calculate high concern ratio
        high_concern_count = len(area_data[area_data['safety_category'] == 'HIGH_CONCERN'])
        high_concern_ratio = high_concern_count / total_complaints if total_complaints > 0 else 0
        
        # Category distribution
        category_dist = area_data['safety_category'].value_counts(normalize=True).to_dict()
        
        return {
            'total_complaints': total_complaints,
            'weighted_safety_score': round(safety_score, 2),
            'complaints_per_day': round(complaints_per_day, 3),
            'high_concern_ratio': round(high_concern_ratio, 3),
            'category_distribution': category_dist
        }
    
    def _generate_safety_rating(self, metrics: Dict) -> Dict:
        """Generate overall safety rating and grade"""
        score = metrics['weighted_safety_score']
        high_concern_ratio = metrics['high_concern_ratio']
        complaints_per_day = metrics['complaints_per_day']
        
        # Adjust score based on high concern ratio
        if high_concern_ratio > 0.2:  # More than 20% high concern
            score -= 1.0
        elif high_concern_ratio > 0.1:  # More than 10% high concern
            score -= 0.5
        
        # Adjust score based on complaint frequency
        if complaints_per_day > 2.0:  # Very high activity
            score -= 0.5
        elif complaints_per_day > 1.0:  # High activity
            score -= 0.25
        
        # Ensure score stays within bounds
        score = max(1.0, min(5.0, score))
        
        # Convert to letter grade
        if score >= 4.5:
            grade = 'A'
            description = 'Very Safe'
            color = 'green'
        elif score >= 3.5:
            grade = 'B'
            description = 'Generally Safe'
            color = 'lightgreen'
        elif score >= 2.5:
            grade = 'C'
            description = 'Moderately Safe'
            color = 'yellow'
        elif score >= 1.5:
            grade = 'D'
            description = 'Some Safety Concerns'
            color = 'orange'
        else:
            grade = 'F'
            description = 'Significant Safety Concerns'
            color = 'red'
        
        return {
            'score': round(score, 2),
            'grade': grade,
            'description': description,
            'color': color
        }
    
    def _create_safety_summary(self, area_data: pd.DataFrame, metrics: Dict, rating: Dict) -> str:
        """Create human-readable safety summary"""
        total = metrics['total_complaints']
        score = rating['score']
        description = rating['description']
        
        if total == 0:
            return "This area has no reported incidents in our database, suggesting it's a quiet, low-activity area."
        
        # Get top complaint types
        top_complaints = area_data['complaint_type'].value_counts().head(3)
        complaint_list = [f"{count} {complaint.lower()} complaints" for complaint, count in top_complaints.items()]
        
        summary = f"This area is rated as {description} (Grade {rating['grade']}) with a safety score of {score}/5.0. "
        
        if total == 1:
            summary += f"There has been 1 reported incident"
        else:
            summary += f"There have been {total} reported incidents"
        
        if len(complaint_list) > 0:
            if len(complaint_list) == 1:
                summary += f", primarily {complaint_list[0]}."
            elif len(complaint_list) == 2:
                summary += f", mainly {complaint_list[0]} and {complaint_list[1]}."
            else:
                summary += f", mainly {complaint_list[0]}, {complaint_list[1]}, and {complaint_list[2]}."
        
        # Add context about high concern incidents
        high_concern = metrics['high_concern_ratio']
        if high_concern > 0.1:
            summary += f" {high_concern:.1%} of incidents are high-concern safety issues."
        else:
            summary += " Most incidents are minor quality-of-life issues."
        
        return summary
    
    def _get_complaint_breakdown(self, area_data: pd.DataFrame) -> Dict:
        """Get detailed breakdown of complaint types"""
        if area_data.empty:
            return {}
        
        # Breakdown by safety category
        category_breakdown = {}
        for category, info in self.safety_categories.items():
            category_data = area_data[area_data['safety_category'] == category]
            if not category_data.empty:
                category_breakdown[category] = {
                    'count': len(category_data),
                    'percentage': len(category_data) / len(area_data) * 100,
                    'description': info['description'],
                    'top_complaints': category_data['complaint_type'].value_counts().head(3).to_dict()
                }
        
        return category_breakdown
    
    def _get_recent_activity(self, area_data: pd.DataFrame, days: int = 30) -> Dict:
        """Get recent activity summary"""
        if area_data.empty or 'created_date' not in area_data.columns:
            return {'recent_complaints': 0, 'trend': 'stable'}
        
        # Filter recent data
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_data = area_data[area_data['created_date'] >= cutoff_date]
        
        # Compare with previous period
        prev_cutoff = cutoff_date - timedelta(days=days)
        prev_data = area_data[
            (area_data['created_date'] >= prev_cutoff) & 
            (area_data['created_date'] < cutoff_date)
        ]
        
        recent_count = len(recent_data)
        prev_count = len(prev_data)
        
        if prev_count == 0:
            trend = 'stable'
        elif recent_count > prev_count * 1.2:
            trend = 'increasing'
        elif recent_count < prev_count * 0.8:
            trend = 'decreasing'
        else:
            trend = 'stable'
        
        return {
            'recent_complaints': recent_count,
            'previous_period_complaints': prev_count,
            'trend': trend,
            'days_analyzed': days
        }
    
    def _generate_recommendations(self, rating: Dict, metrics: Dict) -> List[str]:
        """Generate safety recommendations based on analysis"""
        recommendations = []
        
        score = rating['score']
        high_concern_ratio = metrics['high_concern_ratio']
        
        if score >= 4.0:
            recommendations.append("This is a safe area with minimal safety concerns.")
            recommendations.append("Continue normal safety precautions for urban living.")
        elif score >= 3.0:
            recommendations.append("This is generally a safe area with some minor issues.")
            recommendations.append("Be aware of your surroundings, especially at night.")
        elif score >= 2.0:
            recommendations.append("Exercise increased caution in this area.")
            recommendations.append("Consider avoiding late-night activities alone.")
        else:
            recommendations.append("This area has notable safety concerns.")
            recommendations.append("Take extra precautions and consider alternative locations.")
        
        if high_concern_ratio > 0.1:
            recommendations.append("There have been serious safety incidents reported recently.")
            recommendations.append("Stay alert and report any suspicious activity to authorities.")
        
        recommendations.append("Always trust your instincts and prioritize personal safety.")
        recommendations.append("Consider checking local community boards for recent updates.")
        
        return recommendations
    
    def _create_default_rating(self, message: str) -> Dict:
        """Create default rating response when no data is available"""
        return {
            'area_info': {'data_points': 0},
            'safety_rating': {
                'score': 3.0,
                'grade': 'C',
                'description': 'Insufficient Data',
                'color': 'gray'
            },
            'safety_metrics': {
                'total_complaints': 0,
                'weighted_safety_score': 3.0,
                'complaints_per_day': 0,
                'high_concern_ratio': 0,
                'category_distribution': {}
            },
            'safety_summary': message,
            'complaint_breakdown': {},
            'recent_activity': {'recent_complaints': 0, 'trend': 'stable'},
            'recommendations': [
                "No recent data available for safety analysis.",
                "Consider checking with local authorities or community resources.",
                "Use general urban safety precautions."
            ]
        }
    
    def get_borough_comparison(self) -> Dict:
        """Get safety comparison across NYC boroughs"""
        if self.crime_data is None or self.crime_data.empty:
            return {}
        
        borough_stats = {}
        
        for borough in self.crime_data['borough'].unique():
            if pd.isna(borough) or borough == 'nan':
                continue
                
            borough_data = self.crime_data[self.crime_data['borough'] == borough]
            metrics = self._calculate_safety_metrics(borough_data)
            rating = self._generate_safety_rating(metrics)
            
            borough_stats[borough] = {
                'safety_score': rating['score'],
                'grade': rating['grade'],
                'total_complaints': metrics['total_complaints'],
                'high_concern_ratio': metrics['high_concern_ratio']
            }
        
        return borough_stats
    
    def _create_fallback_rating(self, zip_code: str = None, borough: str = None, address: str = None) -> Dict:
        """Create basic safety rating when API data is unavailable"""
        
        # Basic borough safety ratings (general NYC knowledge)
        borough_ratings = {
            'Manhattan': {'score': 3.8, 'grade': 'B+', 'description': 'Generally safe with heavy foot traffic and police presence'},
            'Brooklyn': {'score': 3.5, 'grade': 'B', 'description': 'Safety varies by neighborhood, generally improving'},
            'Queens': {'score': 3.6, 'grade': 'B', 'description': 'Diverse borough with generally good safety record'},
            'Bronx': {'score': 3.2, 'grade': 'B-', 'description': 'Improving safety conditions, varies by area'},
            'Staten Island': {'score': 4.0, 'grade': 'A-', 'description': 'Generally the safest NYC borough'}
        }
        
        # Try to get borough-specific rating
        if borough and borough in borough_ratings:
            rating_info = borough_ratings[borough]
        else:
            # Default rating
            rating_info = {'score': 3.5, 'grade': 'B', 'description': 'General NYC area safety rating'}
        
        return {
            'safety_rating': {
                'score': rating_info['score'],
                'grade': rating_info['grade'],
                'description': rating_info['description']
            },
            'safety_metrics': {
                'total_complaints': 0,
                'high_concern_count': 0,
                'medium_concern_count': 0,
                'low_concern_count': 0,
                'avg_complaints_per_month': 0
            },
            'complaint_breakdown': {},
            'recent_activity': {
                'trend': 'stable',
                'recent_incidents': 0,
                'comparison_text': 'No recent data available'
            },
            'area_info': {
                'zip_code': zip_code,
                'borough': borough,
                'address': address,
                'radius_miles': 0.5,
                'data_points': 0
            },
            'safety_summary': f"Basic safety information for {borough or 'this area'}. {rating_info['description']} Live crime data temporarily unavailable - showing general area assessment.",
            'recommendations': [
                "Stay aware of your surroundings",
                "Use well-lit streets when walking at night",
                "Keep valuables secure",
                "Trust your instincts about situations"
            ],
            'llm_summary': f"Safety assessment for {borough or 'this area'}: {rating_info['description']} Please note that live crime data is temporarily unavailable, so this is a general assessment.",
            'llm_recommendations': [
                "Follow general urban safety practices",
                "Check local news for recent developments",
                "Consider using ride-sharing for late night travel",
                "Stay connected with friends when out"
            ],
            'data_source': 'Fallback rating (API unavailable)',
            'analysis_timestamp': datetime.now().isoformat()
        }

    def validate_system(self) -> bool:
        """Validate that the safety analysis system is working correctly"""
        if self.crime_data is None:
            logger.error("Crime data not loaded")
            return False
        
        if self.crime_data.empty:
            logger.error("Crime data is empty")
            return False
        
        required_columns = ['complaint_type', 'incident_zip', 'borough']
        missing_columns = [col for col in required_columns if col not in self.crime_data.columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        logger.info("Safety analysis system validation passed")
        return True 