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
        # Based on $40 default with neighborhood adjustments
        self.zip_ac_costs = {
            # Manhattan (Premium areas)
            '10001': 50, '10002': 45, '10003': 55, '10004': 60, '10005': 65,
            '10006': 60, '10007': 55, '10009': 50, '10010': 55, '10011': 60,
            '10012': 50, '10013': 45, '10014': 55, '10016': 60, '10017': 65,
            '10018': 55, '10019': 60, '10020': 65, '10021': 75, '10022': 70,
            '10023': 65, '10024': 70, '10025': 60, '10026': 50, '10027': 45,
            '10028': 70, '10029': 50, '10030': 45, '10031': 40, '10032': 40,
            '10033': 40, '10034': 35, '10035': 40, '10036': 65, '10037': 40,
            '10038': 55, '10039': 40, '10040': 35, '10044': 65, '10065': 75,
            '10075': 80, '10128': 70, '10280': 60, '10282': 55,
            
            # Brooklyn
            '11201': 40, '11202': 45, '11203': 30, '11204': 35, '11205': 40,
            '11206': 30, '11207': 25, '11208': 25, '11209': 40, '11210': 35,
            '11211': 45, '11212': 25, '11213': 30, '11214': 35, '11215': 50,
            '11216': 35, '11217': 45, '11218': 35, '11219': 40, '11220': 35,
            '11221': 30, '11222': 40, '11223': 35, '11224': 30, '11225': 35,
            '11226': 30, '11228': 35, '11229': 40, '11230': 35, '11231': 45,
            '11232': 35, '11233': 25, '11234': 30, '11235': 35, '11236': 30,
            '11237': 25, '11238': 45, '11239': 25, '11241': 30, '11242': 35,
            '11243': 30, '11249': 40, '11251': 35, '11252': 35,
            
            # Queens
            '11101': 40, '11102': 45, '11103': 40, '11104': 35, '11105': 40,
            '11106': 35, '11109': 40, '11120': 35, '11354': 35, '11355': 30,
            '11356': 35, '11357': 40, '11358': 35, '11359': 40, '11360': 35,
            '11361': 40, '11362': 35, '11363': 30, '11364': 35, '11365': 30,
            '11366': 25, '11367': 25, '11368': 25, '11369': 25, '11370': 30,
            '11371': 30, '11372': 30, '11373': 30, '11374': 35, '11375': 35,
            '11377': 30, '11378': 25, '11379': 30, '11385': 30, '11411': 35,
            '11412': 30, '11413': 25, '11414': 25, '11415': 30, '11416': 25,
            '11417': 30, '11418': 30, '11419': 30, '11420': 35, '11421': 30,
            '11422': 35, '11423': 30, '11426': 35, '11427': 40, '11428': 35,
            '11429': 30, '11430': 25, '11432': 25, '11433': 25, '11434': 25,
            '11435': 25, '11436': 30, '11691': 25, '11692': 25, '11693': 25,
            '11694': 25, '11697': 30,
            
            # Bronx
            '10451': 25, '10452': 25, '10453': 25, '10454': 25, '10455': 25,
            '10456': 25, '10457': 25, '10458': 25, '10459': 25, '10460': 25,
            '10461': 30, '10462': 25, '10463': 30, '10464': 30, '10465': 30,
            '10466': 25, '10467': 25, '10468': 25, '10469': 25, '10470': 25,
            '10471': 35, '10472': 25, '10473': 25, '10474': 25, '10475': 25,
            
            # Staten Island
            '10301': 30, '10302': 30, '10303': 30, '10304': 30, '10305': 30,
            '10306': 30, '10307': 30, '10308': 30, '10309': 30, '10310': 30,
            '10311': 30, '10312': 30, '10313': 30, '10314': 30
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
        self.default_ac_cost = 40
        
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
            
            # Apply new formula: Total bill = Per AC bill * (# rooms + 1) + 15$ extra + 10 * (energy rating factor)
            # Note: Using num_rooms + 1 as specified in the updated formula
            monthly_ac_cost = per_ac_cost * seasonal_factor
            total_bill = (monthly_ac_cost * (num_rooms + 1)) + self.base_extra_cost + (self.energy_rating_multiplier * energy_rating_factor)
            
            month_name = datetime(2024, month, 1).strftime('%B')
            
            estimate = {
                'month': month_name,
                'month_num': month,
                'estimated_bill': round(total_bill, 2),
                'ac_units': num_ac_units,
                'per_ac_cost': round(monthly_ac_cost, 2),
                'rooms_multiplier': num_rooms + 1,
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
            'cost_tier': 'High' if ac_cost >= 55 else 'Medium' if ac_cost >= 35 else 'Low'
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
