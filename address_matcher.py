import pandas as pd
import re
from typing import Dict, List, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger(__name__)

class AddressMatcher:
    """Handles fuzzy address matching for building lookup"""
    
    def __init__(self, building_data: pd.DataFrame):
        self.building_data = building_data
        self.normalized_addresses = self._normalize_addresses()
        
    def _normalize_addresses(self) -> Dict:
        """Normalize addresses for better matching"""
        normalized = {}
        
        for idx, row in self.building_data.iterrows():
            address = str(row.get('Address 1', '')).strip()
            city = str(row.get('City', '')).strip()
            borough = str(row.get('Borough', '')).strip()
            
            # Create normalized address string
            full_address = f"{address}, {city}, {borough}".lower()
            
            # Clean the address
            normalized_addr = self._clean_address(full_address)
            
            normalized[idx] = {
                'original': full_address,
                'normalized': normalized_addr,
                'data': row.to_dict()
            }
        
        return normalized
    
    def _clean_address(self, address: str) -> str:
        """Clean and normalize address string"""
        # Convert to lowercase
        cleaned = address.lower()
        
        # Remove common prefixes/suffixes
        cleaned = re.sub(r'\b(apt|apartment|unit|suite|ste|#)\s*\w*\b', '', cleaned)
        
        # Standardize street types
        street_types = {
            'street': ['st', 'str'],
            'avenue': ['ave', 'av'],
            'boulevard': ['blvd', 'boul'],
            'parkway': ['pkwy', 'pky'],
            'place': ['pl'],
            'road': ['rd'],
            'drive': ['dr'],
            'lane': ['ln'],
            'court': ['ct']
        }
        
        for standard, variants in street_types.items():
            for variant in variants:
                cleaned = re.sub(rf'\b{variant}\b', standard, cleaned)
        
        # Remove extra whitespace and punctuation
        cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def find_building(self, address: str) -> Optional[Dict]:
        """Find the best matching building for given address"""
        if not address:
            return None
        
        normalized_query = self._clean_address(address.lower())
        best_match = None
        best_score = 0.0
        
        for idx, addr_data in self.normalized_addresses.items():
            # Calculate similarity score
            score = self._calculate_similarity(normalized_query, addr_data['normalized'])
            
            # Also check against original address for exact matches
            original_score = self._calculate_similarity(address.lower(), addr_data['original'])
            final_score = max(score, original_score)
            
            if final_score > best_score:
                best_score = final_score
                best_match = addr_data['data']
        
        # Only return matches with reasonable confidence
        if best_score >= 0.6:
            logger.info(f"Found building match with score {best_score:.2f}")
            return best_match
        else:
            logger.warning(f"No good address match found. Best score: {best_score:.2f}")
            return None
    
    def search_buildings(self, query: str, limit: int = 10) -> List[Dict]:
        """Search for buildings with fuzzy matching"""
        if not query:
            return []
        
        normalized_query = self._clean_address(query.lower())
        matches = []
        
        for idx, addr_data in self.normalized_addresses.items():
            # Calculate similarity scores
            score = self._calculate_similarity(normalized_query, addr_data['normalized'])
            original_score = self._calculate_similarity(query.lower(), addr_data['original'])
            
            # Also check property name
            property_name = str(addr_data['data'].get('Property Name', '')).lower()
            name_score = self._calculate_similarity(query.lower(), property_name)
            
            final_score = max(score, original_score, name_score)
            
            if final_score >= 0.3:  # Lower threshold for search
                building_data = addr_data['data']
                match = {
                    'property_id': building_data.get('Property ID'),
                    'property_name': building_data.get('Property Name'),
                    'address': building_data.get('Address 1'),
                    'city': building_data.get('City'),
                    'borough': building_data.get('Borough'),
                    'property_type': building_data.get('Primary Property Type - Self Selected'),
                    'year_built': building_data.get('Year Built'),
                    'gfa': building_data.get('Property GFA - Calculated (Buildings) (ft²)'),
                    'match_score': round(final_score, 3),
                    'full_address': f"{building_data.get('Address 1', '')}, {building_data.get('City', '')}, {building_data.get('Borough', '')}"
                }
                matches.append(match)
        
        # Sort by match score and return top results
        matches.sort(key=lambda x: x['match_score'], reverse=True)
        return matches[:limit]
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings"""
        if not str1 or not str2:
            return 0.0
        
        # Use SequenceMatcher for basic similarity
        base_score = SequenceMatcher(None, str1, str2).ratio()
        
        # Boost score for exact word matches
        words1 = set(str1.split())
        words2 = set(str2.split())
        
        if words1 and words2:
            word_overlap = len(words1.intersection(words2)) / len(words1.union(words2))
            # Combine base score with word overlap
            final_score = (base_score * 0.6) + (word_overlap * 0.4)
        else:
            final_score = base_score
        
        return final_score
    
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
