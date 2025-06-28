import pandas as pd
import re
from typing import Dict, List, Optional
from thefuzz import process, fuzz
import logging

logger = logging.getLogger(__name__)

class AddressMatcher:
    """Handles fuzzy address matching for building lookup"""
    
    def __init__(self, building_data: pd.DataFrame):
        self.building_data = building_data
        # Create a dictionary of normalized address to original index
        self.address_map, self.choices = self._create_address_map()
        
    def _create_address_map(self):
        """Create a mapping from normalized addresses to original data index."""
        address_map = {}
        # Pre-cleaning addresses for thefuzz
        for idx, row in self.building_data.iterrows():
            address = str(row.get('Address 1', '')).strip().lower()
            # A simple normalization is enough for thefuzz
            cleaned = re.sub(r'[^\w\s]', '', address)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            if cleaned:
                address_map[cleaned] = idx
        return address_map, list(address_map.keys())
    
    def find_building(self, address: str) -> Optional[Dict]:
        """Find the best matching building for a given address using thefuzz."""
        if not address:
            return None
        
        # Clean the input query in the same way
        cleaned_query = re.sub(r'[^\w\s]', '', address.lower())
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # Use process.extractOne to find the best match, it's highly optimized
        match_result = process.extractOne(cleaned_query, self.choices, scorer=fuzz.WRatio)
        if not match_result:
            return None
        
        best_match, score = match_result

        if score >= 85:  # Use a higher threshold for better accuracy
            logger.info(f"Found building match '{best_match}' with score {score}")
            original_idx = self.address_map[best_match]
            building_info = self.building_data.loc[original_idx].to_dict()
            building_info['confidence_score'] = score
            return building_info
        else:
            logger.warning(f"No good address match found for '{address}'. Best score: {score} for '{best_match}'")
            return None
    
    def search_buildings(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for buildings with fuzzy matching using thefuzz."""
        if not query:
            return []
        
        cleaned_query = re.sub(r'[^\w\s]', '', query.lower())
        cleaned_query = re.sub(r'\s+', ' ', cleaned_query).strip()
        
        # process.extract provides a list of matches
        matches = process.extract(cleaned_query, self.choices, scorer=fuzz.WRatio, limit=limit*2) # Get more to filter
        
        results = []
        for best_match, score in matches:
            if score >= 60: # Lower threshold for search
                original_idx = self.address_map[best_match]
                building_data = self.building_data.loc[original_idx].to_dict()
                match = {
                    'property_id': building_data.get('Property ID'),
                    'property_name': building_data.get('Property Name'),
                    'address': building_data.get('Address 1'),
                    'borough': building_data.get('Borough'),
                    'match_score': score,
                }
                results.append(match)
        
        return results[:limit]
    
    def find_by_partial_address(self, partial_address: str) -> List[Dict]:
        """Find buildings by partial address match"""
        if not partial_address:
            return []
        
        partial_lower = partial_address.lower()
        matches = []
        
        for idx, addr_data in self.normalized_addresses.items():
            building_data = addr_data['data']
            
            # Check if partial address is contained in full address
            full_addr = addr_data['original']
            if partial_lower in full_addr:
                match = {
                    'property_id': building_data.get('Property ID'),
                    'property_name': building_data.get('Property Name'),
                    'address': building_data.get('Address 1'),
                    'city': building_data.get('City'),
                    'borough': building_data.get('Borough'),
                    'property_type': building_data.get('Primary Property Type - Self Selected'),
                    'full_address': f"{building_data.get('Address 1', '')}, {building_data.get('City', '')}, {building_data.get('Borough', '')}"
                }
                matches.append(match)
        
        return matches[:20]  # Limit partial matches
    
    def find_by_borough(self, borough: str) -> List[Dict]:
        """Find buildings in a specific borough"""
        if not borough:
            return []
        
        borough_lower = borough.lower()
        matches = []
        
        for idx, addr_data in self.normalized_addresses.items():
            building_data = addr_data['data']
            building_borough = str(building_data.get('Borough', '')).lower()
            
            if borough_lower in building_borough:
                match = {
                    'property_id': building_data.get('Property ID'),
                    'property_name': building_data.get('Property Name'),
                    'address': building_data.get('Address 1'),
                    'city': building_data.get('City'),
                    'borough': building_data.get('Borough'),
                    'property_type': building_data.get('Primary Property Type - Self Selected')
                }
                matches.append(match)
        
        return matches
