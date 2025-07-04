import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime

from seasonality_factors import SeasonalityFactors
from rate_calculator import RateCalculator

logger = logging.getLogger(__name__)

class BillEstimator:
    """AC-based electricity bill estimation logic"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.seasonality = SeasonalityFactors()
        self.rate_calculator = RateCalculator()
        
        # ZIP CODE BASED AC COSTS PER UNIT (Monthly estimates in NYC)
        self.zip_ac_costs = {
            # Manhattan (Premium areas)
            '10001': 85, '10002': 80, '10003': 90, '10004': 95, '10005': 100,
            '10006': 95, '10007': 90, '10009': 85, '10010': 90, '10011': 95,
            '10012': 85, '10013': 80, '10014': 90, '10016': 95, '10017': 100,
            '10018': 90, '10019': 95, '10020': 100, '10021': 110, '10022': 105,
            '10023': 100, '10024': 105, '10025': 95, '10026': 85, '10027': 80,
            '10028': 105, '10029': 85, '10030': 80, '10031': 75, '10032': 75,
            '10033': 75, '10034': 70, '10035': 75, '10036': 100, '10037': 75,
            '10038': 90, '10039': 75, '10040': 70, '10044': 100, '10065': 110,
            '10075': 115, '10128': 105, '10280': 95, '10282': 90,
            
            # Brooklyn
            '11201': 75, '11202': 80, '11203': 65, '11204': 70, '11205': 75,
            '11206': 65, '11207': 60, '11208': 60, '11209': 75, '11210': 70,
            '11211': 80, '11212': 60, '11213': 65, '11214': 70, '11215': 85,
            '11216': 70, '11217': 80, '11218': 70, '11219': 75, '11220': 70,
            '11221': 65, '11222': 75, '11223': 70, '11224': 65, '11225': 70,
            '11226': 65, '11228': 70, '11229': 75, '11230': 70, '11231': 80,
            '11232': 70, '11233': 60, '11234': 65, '11235': 70, '11236': 65,
            '11237': 60, '11238': 80, '11239': 60, '11241': 65, '11242': 70,
            '11243': 65, '11249': 75, '11251': 70, '11252': 70,
            
            # Queens
            '11101': 75, '11102': 80, '11103': 75, '11104': 70, '11105': 75,
            '11106': 70, '11109': 75, '11120': 70, '11354': 70, '11355': 65,
            '11356': 70, '11357': 75, '11358': 70, '11359': 75, '11360': 70,
            '11361': 75, '11362': 70, '11363': 65, '11364': 70, '11365': 65,
            '11366': 60, '11367': 60, '11368': 60, '11369': 60, '11370': 65,
            '11371': 65, '11372': 65, '11373': 65, '11374': 70, '11375': 70,
            '11377': 65, '11378': 60, '11379': 65, '11385': 65, '11411': 70,
            '11412': 65, '11413': 60, '11414': 60, '11415': 65, '11416': 60,
            '11417': 65, '11418': 65, '11419': 65, '11420': 70, '11421': 65,
            '11422': 70, '11423': 65, '11426': 70, '11427': 75, '11428': 70,
            '11429': 65, '11430': 60, '11432': 60, '11433': 60, '11434': 60,
            '11435': 60, '11436': 65, '11691': 60, '11692': 60, '11693': 60,
            '11694': 60, '11697': 65,
            
            # Bronx
            '10451': 60, '10452': 60, '10453': 60, '10454': 60, '10455': 60,
            '10456': 60, '10457': 60, '10458': 60, '10459': 60, '10460': 60,
            '10461': 65, '10462': 60, '10463': 65, '10464': 65, '10465': 65,
            '10466': 60, '10467': 60, '10468': 60, '10469': 60, '10470': 60,
            '10471': 70, '10472': 60, '10473': 60, '10474': 60, '10475': 60,
            
            # Staten Island
            '10301': 65, '10302': 65, '10303': 65, '10304': 65, '10305': 65,
            '10306': 65, '10307': 65, '10308': 65, '10309': 65, '10310': 65,
            '10311': 65, '10312': 65, '10313': 65, '10314': 65
        }
        
        # Default bathroom estimates by room count
        self.bathroom_estimates = {
            0: 1,    # Studio - 1 bathroom
            1: 1,    # 1BR - 1 bathroom
            2: 1,    # 2BR - 1 bathroom
            3: 2,    # 3BR - 2 bathrooms
            4: 2,    # 4BR - 2 bathrooms
            5: 3,    # 5BR - 3 bathrooms
            6: 3     # 6BR+ - 3 bathrooms
        }
        
        # Default AC cost per unit if zip code not found
        self.default_ac_cost = 75
        
        # Fixed costs
        self.base_extra_cost = 15  # $15 extra as specified
        self.energy_rating_multiplier = 10  # $10 * energy rating factor
    
    def estimate_monthly_bills(self, building_data: Dict, num_rooms: int, 
                             apartment_type: str = None, building_type: str = 'residential',
                             include_demand_charges: bool = False, num_bathrooms: int = None) -> List[Dict]:
        """Generate monthly AC-based electricity bill estimates using new formula"""
        
        # Get zip code from building data
        zip_code = self._extract_zip_code(building_data)
        
        # Estimate number of bathrooms if not provided
        if num_bathrooms is None:
            num_bathrooms = self.bathroom_estimates.get(min(num_rooms, 6), 1)
        
        # Calculate number of AC units: AC = (# of rooms - # of bath)
        num_ac_units = max(1, num_rooms - num_bathrooms)  # Minimum 1 AC unit
        
        # Get per-AC cost for this zip code
        per_ac_cost = self.zip_ac_costs.get(zip_code, self.default_ac_cost)
        
        # Calculate energy rating factor
        energy_rating_factor = self._calculate_energy_rating_factor(building_data, zip_code)
        
        # Generate monthly estimates
        monthly_estimates = []
        
        for month in range(1, 13):
            # Get seasonal factor for AC usage
            seasonal_factor = self._get_ac_seasonal_factor(month)
            
            # Apply new formula: Total bill = Per AC bill * (# rooms) + 15$ extra + 10 * (energy rating factor)
            # Note: Using num_rooms as specified in the formula, not num_ac_units
            monthly_ac_cost = per_ac_cost * seasonal_factor
            total_bill = (monthly_ac_cost * num_rooms) + self.base_extra_cost + (self.energy_rating_multiplier * energy_rating_factor)
            
            month_name = datetime(2024, month, 1).strftime('%B')
            
            estimate = {
                'month': month_name,
                'month_num': month,
                'estimated_bill': round(total_bill, 2),
                'ac_units': num_ac_units,
                'per_ac_cost': round(monthly_ac_cost, 2),
                'rooms_multiplier': num_rooms,
                'base_extra_cost': self.base_extra_cost,
                'energy_rating_cost': round(self.energy_rating_multiplier * energy_rating_factor, 2),
                'seasonal_factor': round(seasonal_factor, 2),
                'zip_code': zip_code,
                'energy_rating_factor': round(energy_rating_factor, 2)
            }
            
            monthly_estimates.append(estimate)
        
        return monthly_estimates
    
    def _extract_zip_code(self, building_data: Dict) -> str:
        """Extract zip code from building data"""
        zip_code = building_data.get('Postal Code', '')
        if not zip_code or pd.isna(zip_code):
            # Try to extract from address
            address = building_data.get('Address 1', '')
            if address:
                # Simple regex to find 5-digit zip code
                import re
                zip_match = re.search(r'\b\d{5}\b', str(address))
                if zip_match:
                    zip_code = zip_match.group()
        
        return str(zip_code) if zip_code else '10001'  # Default to Manhattan zip
    
    def _calculate_energy_rating_factor(self, building_data: Dict, zip_code: str) -> float:
        """Calculate energy rating factor based on building efficiency and neighborhood"""
        
        # Building efficiency component (0-3 scale)
        year_built = building_data.get('Year Built', 0)
        if pd.isna(year_built) or year_built == 0:
            building_efficiency = 2.0  # Default
        elif year_built >= 2015:
            building_efficiency = 1.0  # Very efficient
        elif year_built >= 2005:
            building_efficiency = 1.5  # Efficient
        elif year_built >= 1995:
            building_efficiency = 2.0  # Average
        elif year_built >= 1980:
            building_efficiency = 2.5  # Below average
        else:
            building_efficiency = 3.0  # Inefficient
        
        # Neighborhood factor based on zip code (0-2 scale)
        neighborhood_factor = self._get_neighborhood_factor(zip_code)
        
        # Energy Star Score bonus (if available)
        energy_star_score = building_data.get('ENERGY STAR Score', 0)
        if energy_star_score and not pd.isna(energy_star_score) and energy_star_score > 0:
            # Higher scores = lower factor (more efficient)
            energy_star_bonus = -0.5 * (energy_star_score - 50) / 50  # Normalize around 50
            energy_star_bonus = max(-1.0, min(1.0, energy_star_bonus))  # Cap at +/-1
        else:
            energy_star_bonus = 0
        
        # Combined factor
        total_factor = building_efficiency + neighborhood_factor + energy_star_bonus
        
        # Ensure factor is reasonable (0.5 to 4.0)
        return max(0.5, min(4.0, total_factor))
    
    def _get_neighborhood_factor(self, zip_code: str) -> float:
        """Get neighborhood efficiency factor based on zip code"""
        # Manhattan premium neighborhoods (higher utility costs)
        if zip_code in ['10021', '10022', '10028', '10065', '10075', '10128']:
            return 2.0
        # Manhattan midtown/downtown
        elif zip_code.startswith('100') and zip_code in ['10001', '10017', '10019', '10020', '10036']:
            return 1.8
        # Brooklyn gentrified areas
        elif zip_code in ['11201', '11202', '11215', '11217', '11231', '11238']:
            return 1.5
        # Queens middle-class areas
        elif zip_code in ['11101', '11102', '11103', '11357', '11361', '11427']:
            return 1.2
        # More affordable areas
        elif zip_code.startswith('104') or zip_code.startswith('116') or zip_code.startswith('117'):
            return 1.0
        else:
            return 1.3  # Default
    
    def _get_ac_seasonal_factor(self, month: int) -> float:
        """Get seasonal factor for AC usage (focused on cooling season)"""
        ac_seasonal_factors = {
            1: 0.3,   # January - minimal AC use
            2: 0.3,   # February - minimal AC use
            3: 0.4,   # March - some warming
            4: 0.6,   # April - moderate temperatures
            5: 0.8,   # May - AC starts being used
            6: 1.1,   # June - AC use increases
            7: 1.4,   # July - peak cooling
            8: 1.5,   # August - peak cooling
            9: 1.2,   # September - still warm
            10: 0.7,  # October - cooling down
            11: 0.4,  # November - minimal AC
            12: 0.3   # December - minimal AC
        }
        
        return ac_seasonal_factors.get(month, 1.0)
    
    def get_building_efficiency_rating(self, building_data: Dict) -> str:
        """Get a building efficiency rating for display"""
        factor = self._calculate_energy_rating_factor(building_data, self._extract_zip_code(building_data))
        
        if factor <= 1.5:
            return 'very_efficient'
        elif factor <= 2.0:
            return 'efficient'
        elif factor <= 2.5:
            return 'average'
        elif factor <= 3.0:
            return 'below_average'
        else:
            return 'inefficient'
    
    def get_zip_ac_estimate(self, zip_code: str) -> Dict:
        """Get AC cost estimate for a specific zip code"""
        ac_cost = self.zip_ac_costs.get(zip_code, self.default_ac_cost)
        
        # Determine borough from zip code
        if zip_code.startswith('100') or zip_code.startswith('101'):
            borough = 'Manhattan'
        elif zip_code.startswith('112'):
            borough = 'Brooklyn'
        elif zip_code.startswith('113') or zip_code.startswith('114') or zip_code.startswith('116'):
            borough = 'Queens'
        elif zip_code.startswith('104'):
            borough = 'Bronx'
        elif zip_code.startswith('103'):
            borough = 'Staten Island'
        else:
            borough = 'Unknown'
        
        return {
            'zip_code': zip_code,
            'borough': borough,
            'per_ac_monthly_cost': ac_cost,
            'cost_tier': 'High' if ac_cost >= 90 else 'Medium' if ac_cost >= 70 else 'Low'
        }
    
    def estimate_bathroom_count(self, num_rooms: int, apartment_type: str = None) -> int:
        """Estimate number of bathrooms based on room count and apartment type"""
        if apartment_type:
            # Try to extract bathroom count from apartment type
            import re
            bath_match = re.search(r'(\d+)ba', apartment_type.lower())
            if bath_match:
                return int(bath_match.group(1))
        
        # Use default estimates
        return self.bathroom_estimates.get(min(num_rooms, 6), 1)
    
    def calculate_efficiency_factor(self, year_built) -> float:
        """Legacy method for compatibility - returns energy rating factor"""
        building_data = {'Year Built': year_built}
        return self._calculate_energy_rating_factor(building_data, '10001')
    
    def get_rate_structure(self, building_data: Dict) -> Dict:
        """Get rate structure information (simplified for AC model)"""
        zip_code = self._extract_zip_code(building_data)
        ac_info = self.get_zip_ac_estimate(zip_code)
        
        return {
            'model': 'AC-based estimation',
            'zip_code': zip_code,
            'borough': ac_info['borough'],
            'per_ac_cost': ac_info['per_ac_monthly_cost'],
            'cost_tier': ac_info['cost_tier'],
            'base_extra_cost': self.base_extra_cost,
            'energy_rating_multiplier': self.energy_rating_multiplier
        }
