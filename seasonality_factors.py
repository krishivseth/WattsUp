from typing import Dict

class SeasonalityFactors:
    """NYC-specific seasonality factors for electricity consumption"""
    
    def __init__(self):
        # Monthly factors based on NYC energy usage patterns
        # Values represent multipliers for average monthly consumption
        self.seasonal_factors = {
            'Multifamily Housing': {
                1: 1.30,   # January - high heating
                2: 1.25,   # February - cold
                3: 1.10,   # March - transitional
                4: 0.90,   # April - mild
                5: 0.80,   # May - pleasant
                6: 0.95,   # June - AC starts
                7: 1.15,   # July - peak cooling
                8: 1.20,   # August - peak cooling
                9: 1.00,   # September - moderate
                10: 0.85,  # October - mild
                11: 1.00,  # November - heating starts
                12: 1.25   # December - high heating
            },
            'Office': {
                1: 1.25,   # January - high heating, full occupancy
                2: 1.20,   # February - cold, full occupancy
                3: 1.05,   # March - transitional
                4: 0.95,   # April - mild
                5: 0.85,   # May - pleasant
                6: 1.00,   # June - AC starts
                7: 1.20,   # July - peak cooling
                8: 1.25,   # August - peak cooling
                9: 1.10,   # September - back to work
                10: 0.90,  # October - mild
                11: 1.05,  # November - heating starts
                12: 1.15   # December - holiday season
            },
            'Mixed Use Property': {
                1: 1.28,   # January - mixed residential/commercial load
                2: 1.23,   # February
                3: 1.08,   # March
                4: 0.92,   # April
                5: 0.83,   # May
                6: 0.98,   # June
                7: 1.18,   # July
                8: 1.23,   # August
                9: 1.05,   # September
                10: 0.88,  # October
                11: 1.03,  # November
                12: 1.20   # December
            },
            'Retail Store': {
                1: 1.35,   # January - post-holiday, high heating
                2: 1.20,   # February - lower traffic, heating
                3: 1.10,   # March - spring shopping
                4: 0.95,   # April - moderate
                5: 0.85,   # May - mild weather
                6: 1.05,   # June - summer shopping starts
                7: 1.25,   # July - peak cooling, high traffic
                8: 1.30,   # August - peak summer
                9: 1.10,   # September - back to school
                10: 0.90,  # October - mild
                11: 1.15,  # November - holiday prep
                12: 1.40   # December - holiday peak
            },
            'Warehouse': {
                1: 1.20,   # January - heating needs
                2: 1.15,   # February - cold
                3: 1.05,   # March - transitional
                4: 0.95,   # April - mild
                5: 0.90,   # May - pleasant
                6: 1.00,   # June - moderate
                7: 1.10,   # July - some cooling
                8: 1.15,   # August - peak heat
                9: 1.05,   # September - moderate
                10: 0.95,  # October - mild
                11: 1.00,  # November - heating starts
                12: 1.15   # December - heating
            },
            'Hotel': {
                1: 1.25,   # January - fewer guests, high heating
                2: 1.20,   # February - low season, heating
                3: 1.10,   # March - season pickup
                4: 1.00,   # April - moderate season
                5: 0.95,   # May - pleasant weather
                6: 1.05,   # June - summer season starts
                7: 1.20,   # July - peak tourism, AC
                8: 1.25,   # August - peak summer
                9: 1.15,   # September - conference season
                10: 1.00,  # October - moderate
                11: 1.10,  # November - holiday season
                12: 1.30   # December - holiday peak
            }
        }
        
        # Default factors for unknown property types
        self.default_factors = {
            1: 1.25, 2: 1.20, 3: 1.05, 4: 0.95, 5: 0.85, 6: 1.00,
            7: 1.15, 8: 1.20, 9: 1.05, 10: 0.90, 11: 1.05, 12: 1.20
        }
        
        # Heating and cooling degree day correlations for NYC
        self.hdd_factors = {  # Heating Degree Days influence
            1: 1.25, 2: 1.20, 3: 1.10, 4: 0.95, 5: 0.85, 6: 0.90,
            7: 0.85, 8: 0.85, 9: 0.90, 10: 0.95, 11: 1.10, 12: 1.20
        }
        
        self.cdd_factors = {  # Cooling Degree Days influence
            1: 0.90, 2: 0.90, 3: 0.95, 4: 1.00, 5: 1.05, 6: 1.10,
            7: 1.20, 8: 1.25, 9: 1.15, 10: 1.05, 11: 0.95, 12: 0.90
        }
    
    def get_monthly_factor(self, month: int, property_type: str = None) -> float:
        """Get the seasonal factor for a specific month and property type"""
        if not property_type:
            return self.default_factors.get(month, 1.0)
        
        # Find matching property type
        for ptype, factors in self.seasonal_factors.items():
            if ptype.lower() in property_type.lower():
                return factors.get(month, 1.0)
        
        # Fallback to default if no match
        return self.default_factors.get(month, 1.0)
    
    def get_seasonal_pattern(self, property_type: str = None) -> Dict[int, float]:
        """Get the full year seasonal pattern for a property type"""
        if not property_type:
            return self.default_factors.copy()
        
        for ptype, factors in self.seasonal_factors.items():
            if ptype.lower() in property_type.lower():
                return factors.copy()
        
        return self.default_factors.copy()
    
    def get_peak_months(self, property_type: str = None) -> Dict[str, int]:
        """Get the peak consumption months for a property type"""
        pattern = self.get_seasonal_pattern(property_type)
        
        # Find highest and lowest consumption months
        max_month = max(pattern, key=pattern.get)
        min_month = min(pattern, key=pattern.get)
        
        return {
            'peak_month': max_month,
            'peak_factor': pattern[max_month],
            'low_month': min_month,
            'low_factor': pattern[min_month]
        }
    
    def adjust_for_climate_change(self, month: int, property_type: str = None, 
                                 year: int = 2024) -> float:
        """Adjust factors for climate change trends (hotter summers, milder winters)"""
        base_factor = self.get_monthly_factor(month, property_type)
        
        # Climate change adjustments (based on NYC climate trends)
        # Summers getting hotter (more cooling needed)
        if month in [6, 7, 8]:
            climate_adjustment = 1.05  # 5% increase for summer cooling
        # Winters getting milder (less heating needed)
        elif month in [12, 1, 2]:
            climate_adjustment = 0.98  # 2% decrease for winter heating
        else:
            climate_adjustment = 1.0
        
        return base_factor * climate_adjustment
    
    def get_weekday_weekend_factors(self) -> Dict[str, float]:
        """Get weekday vs weekend consumption factors"""
        return {
            'weekday': 1.05,    # Slightly higher weekday consumption
            'weekend': 0.95,    # Lower weekend consumption
            'holiday': 0.85     # Even lower on holidays
        }
    
    def get_time_of_day_factors(self) -> Dict[str, float]:
        """Get time-of-day consumption factors for residential"""
        return {
            'morning': 1.15,    # 6 AM - 10 AM
            'midday': 0.85,     # 10 AM - 4 PM
            'evening': 1.25,    # 4 PM - 10 PM
            'night': 0.75       # 10 PM - 6 AM
        }
    
    def calculate_annual_factor_check(self, property_type: str = None) -> float:
        """Verify that annual factors average to 1.0"""
        pattern = self.get_seasonal_pattern(property_type)
        annual_average = sum(pattern.values()) / len(pattern)
        return annual_average
    
    def get_extreme_weather_adjustments(self) -> Dict[str, float]:
        """Get adjustments for extreme weather events"""
        return {
            'heat_wave': 1.35,      # During heat waves (>95°F)
            'cold_snap': 1.30,      # During cold snaps (<20°F)
            'normal': 1.0,          # Normal weather
            'mild_summer': 0.90,    # Unusually mild summer
            'mild_winter': 0.85     # Unusually mild winter
        }
