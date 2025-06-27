import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime

from seasonality_factors import SeasonalityFactors
from rate_calculator import RateCalculator

logger = logging.getLogger(__name__)

class BillEstimator:
    """Core electricity bill estimation logic"""
    
    def __init__(self, data_processor):
        self.data_processor = data_processor
        self.seasonality = SeasonalityFactors()
        self.rate_calculator = RateCalculator()
        
        # Apartment size estimates (sq ft) by room count
        self.apartment_sizes = {
            'studio': {0: 400, 1: 450},
            '1br': {1: 650, 2: 750},
            '2br': {2: 850, 3: 950}, 
            '3br': {3: 1100, 4: 1250},
            '4br+': {4: 1400, 5: 1600, 6: 1800}
        }
        
        # Default apartment sizes by room count
        self.default_apartment_sizes = {
            0: 400,   # Studio
            1: 650,   # 1BR
            2: 850,   # 2BR
            3: 1100,  # 3BR
            4: 1400,  # 4BR
            5: 1600,  # 5BR
            6: 1800   # 6BR+
        }
    
    def estimate_monthly_bills(self, building_data: Dict, num_rooms: int, 
                             apartment_type: str = None, building_type: str = 'residential',
                             include_demand_charges: bool = False) -> List[Dict]:
        """Generate monthly electricity bill estimates"""
        
        # Validate building data
        if not self.data_processor.validate_building_data(building_data):
            raise ValueError("Building data insufficient for estimation")
        
        # Get base consumption data
        base_intensity = self._get_base_intensity(building_data)
        apartment_sqft = self.estimate_apartment_size(num_rooms, building_type, apartment_type)
        
        # Calculate adjustments
        efficiency_factor = self.calculate_efficiency_factor(building_data.get('Year Built', 2000))
        occupancy_factor = self._get_occupancy_factor(building_data)
        property_type_factor = self._get_property_type_factor(building_data.get('Primary Property Type - Self Selected', ''))
        
        # Calculate annual base consumption for the apartment
        annual_kwh_base = (base_intensity * apartment_sqft * efficiency_factor * 
                          occupancy_factor * property_type_factor)
        
        if annual_kwh_base <= 0:
            raise ValueError("Unable to calculate base consumption")
        
        # Generate monthly estimates
        monthly_estimates = []
        property_type = building_data.get('Primary Property Type - Self Selected', 'Multifamily Housing')
        
        for month in range(1, 13):
            # Get seasonal factor
            seasonal_factor = self.seasonality.get_monthly_factor(month, property_type)
            
            # Calculate monthly consumption
            monthly_kwh = (annual_kwh_base / 12) * seasonal_factor
            
            # Get utility information
            utility = self._determine_utility(building_data)
            
            # Calculate bill components
            bill_components = self.rate_calculator.calculate_monthly_bill(
                monthly_kwh, utility, include_demand_charges
            )
            
            month_name = datetime(2024, month, 1).strftime('%B')
            
            estimate = {
                'month': month_name,
                'month_num': month,
                'kwh_estimate': round(monthly_kwh, 0),
                'base_charge': bill_components['base_charge'],
                'usage_charge': bill_components['usage_charge'],
                'demand_charge': bill_components['demand_charge'],
                'estimated_bill': bill_components['total_bill'],
                'seasonal_factor': round(seasonal_factor, 2),
                'temperature_adjusted': True
            }
            
            monthly_estimates.append(estimate)
        
        return monthly_estimates
    
    def _get_base_intensity(self, building_data: Dict) -> float:
        """Get base electricity intensity (kWh/sq ft) from building data"""
        # Try weather-normalized intensity first
        intensity = building_data.get('Electricity - Weather Normalized Site Electricity Intensity (Grid and Onsite Renewables) (kWh/ft²)')
        
        if pd.isna(intensity) or intensity == 0:
            # Fallback to calculating from total consumption and GFA
            total_kwh = building_data.get('Electricity - Weather Normalized Site Electricity Use (Grid and Onsite Renewables) (kWh)')
            total_gfa = building_data.get('Property GFA - Calculated (Buildings) (ft²)')
            
            if total_kwh and total_gfa and not pd.isna(total_kwh) and not pd.isna(total_gfa):
                intensity = total_kwh / total_gfa
            else:
                # Use default based on property type
                property_type = building_data.get('Primary Property Type - Self Selected', '')
                intensity = self._get_default_intensity(property_type)
        
        return float(intensity) if intensity and not pd.isna(intensity) else 15.0  # Default fallback
    
    def _get_default_intensity(self, property_type: str) -> float:
        """Get default electricity intensity based on property type"""
        defaults = {
            'Multifamily Housing': 12.0,
            'Office': 18.0,
            'Retail Store': 25.0,
            'Mixed Use Property': 15.0,
            'Warehouse': 8.0,
            'Hotel': 20.0
        }
        
        # Handle NaN/None property_type
        if not property_type or pd.isna(property_type):
            return 15.0
        
        property_type_str = str(property_type)
        for ptype, intensity in defaults.items():
            if ptype.lower() in property_type_str.lower():
                return intensity
        
        return 15.0  # General default
    
    def estimate_apartment_size(self, num_rooms: int, building_type: str = 'residential', 
                               apartment_type: str = None) -> float:
        """Estimate apartment size in square feet"""
        
        # Cap room count at 6 for estimation purposes
        room_count = min(num_rooms, 6)
        
        # If apartment type is specified, use more precise estimate
        if apartment_type:
            apartment_type = apartment_type.lower()
            for size_category, room_mapping in self.apartment_sizes.items():
                if apartment_type in size_category or size_category in apartment_type:
                    return room_mapping.get(room_count, self.default_apartment_sizes.get(room_count, 850))
        
        # Use default mapping
        return self.default_apartment_sizes.get(room_count, 850)
    
    def calculate_efficiency_factor(self, year_built) -> float:
        """Calculate building efficiency factor based on age"""
        if pd.isna(year_built) or year_built == 0:
            return 1.0  # Neutral if unknown
        
        current_year = datetime.now().year
        building_age = current_year - int(year_built)
        
        # More efficient buildings built after energy codes improved
        if year_built >= 2010:
            base_efficiency = 0.85  # More efficient
        elif year_built >= 2000:
            base_efficiency = 0.90
        elif year_built >= 1990:
            base_efficiency = 0.95
        elif year_built >= 1980:
            base_efficiency = 1.00
        elif year_built >= 1970:
            base_efficiency = 1.05
        else:
            base_efficiency = 1.10  # Older, less efficient
        
        # Additional age penalty (0.1% per year for buildings over 20 years)
        if building_age > 20:
            age_penalty = (building_age - 20) * 0.001
            base_efficiency += age_penalty
        
        return base_efficiency
    
    def _get_occupancy_factor(self, building_data: Dict) -> float:
        """Get occupancy adjustment factor"""
        occupancy = building_data.get('Occupancy')
        
        if pd.isna(occupancy) or occupancy == 0:
            return 1.0  # Assume full occupancy if unknown
        
        # Convert occupancy percentage to factor
        occupancy_rate = float(occupancy) / 100.0
        
        # Partially occupied buildings may have lower per-unit consumption
        # due to shared systems running at lower efficiency
        if occupancy_rate < 0.5:
            return 1.1  # Higher per-unit consumption
        elif occupancy_rate < 0.8:
            return 1.05
        else:
            return 1.0
    
    def _get_property_type_factor(self, property_type) -> float:
        """Get adjustment factor based on property type"""
        # Handle NaN/None property_type
        if not property_type or pd.isna(property_type):
            return 1.0
        
        property_type_str = str(property_type).lower()
        
        # Residential units in different building types have different consumption patterns
        factors = {
            'multifamily housing': 1.0,
            'mixed use': 0.95,  # Often more efficient
            'office': 0.8,  # Residential space in office building
            'retail': 0.9,
            'hotel': 0.85,
            'warehouse': 0.75
        }
        
        for ptype, factor in factors.items():
            if ptype in property_type_str:
                return factor
        
        return 1.0
    
    def _determine_utility(self, building_data: Dict) -> str:
        """Determine the electric utility for the building"""
        utility = building_data.get('Electric Distribution Utility', '')
        borough = building_data.get('Borough', '')
        
        # Handle NaN values for utility
        if pd.isna(utility):
            utility = ''
        else:
            utility = str(utility)
        
        # Handle NaN values for borough
        if pd.isna(borough):
            borough = ''
        else:
            borough = str(borough)
        
        if 'con' in utility.lower() or 'coned' in utility.lower():
            return 'coned'
        elif 'national' in utility.lower() or 'grid' in utility.lower():
            return 'national_grid'
        else:
            # Default based on borough
            if borough and 'brooklyn' in borough.lower():
                return 'national_grid'
            else:
                return 'coned'  # Default to ConEd
    
    def get_building_efficiency_rating(self, building_data: Dict) -> str:
        """Get a building efficiency rating"""
        year_built = building_data.get('Year Built')
        intensity = self._get_base_intensity(building_data)
        
        if pd.isna(year_built) or pd.isna(intensity):
            return 'unknown'
        
        # Rate efficiency based on intensity and age
        if year_built >= 2010 and intensity < 10:
            return 'very_efficient'
        elif year_built >= 2000 and intensity < 15:
            return 'efficient'
        elif year_built >= 1990 and intensity < 20:
            return 'average'
        elif intensity < 25:
            return 'below_average'
        else:
            return 'inefficient'
    
    def get_rate_structure(self, building_data: Dict) -> Dict:
        """Get the rate structure information for the building"""
        utility = self._determine_utility(building_data)
        return self.rate_calculator.get_rate_info(utility)
