from typing import Dict
import math

class RateCalculator:
    """NYC utility rate calculator"""
    
    def __init__(self):
        # ConEd Residential Rates (2024 - Service Classification No. 1)
        self.coned_residential = {
            'utility_name': 'Con Edison',
            'rate_schedule': 'Residential Service Classification No. 1',
            'base_charge': 18.05,  # Monthly customer charge
            'delivery_rate_tier1': 0.1891,  # First 250 kWh
            'delivery_rate_tier2': 0.2140,  # Above 250 kWh
            'supply_rate': 0.1120,  # Supply charge (variable)
            'tier_threshold': 250,
            'demand_charge': 0.0,  # No demand charge for residential
            'taxes_and_fees_rate': 0.035  # Approx 3.5% for various taxes and fees
        }
        
        # National Grid Rates (for parts of Brooklyn, Queens, Staten Island)
        self.national_grid_residential = {
            'utility_name': 'National Grid',
            'rate_schedule': 'Residential Service Classification No. 1',
            'base_charge': 16.50,
            'delivery_rate_tier1': 0.1756,  # First 300 kWh
            'delivery_rate_tier2': 0.1989,  # Above 300 kWh
            'supply_rate': 0.1089,
            'tier_threshold': 300,
            'demand_charge': 0.0,
            'taxes_and_fees_rate': 0.032
        }
        
        # Commercial rates (simplified)
        self.coned_commercial = {
            'utility_name': 'Con Edison',
            'rate_schedule': 'General Service Small',
            'base_charge': 25.80,
            'delivery_rate': 0.1654,
            'supply_rate': 0.1089,
            'demand_charge': 18.75,  # Per kW
            'demand_threshold': 10,  # kW minimum for demand charges
            'taxes_and_fees_rate': 0.045
        }
        
        self.national_grid_commercial = {
            'utility_name': 'National Grid',
            'rate_schedule': 'General Service Small',
            'base_charge': 23.45,
            'delivery_rate': 0.1587,
            'supply_rate': 0.1035,
            'demand_charge': 17.25,
            'demand_threshold': 10,
            'taxes_and_fees_rate': 0.042
        }
    
    def calculate_monthly_bill(self, kwh_usage: float, utility: str = 'coned', 
                             include_demand_charges: bool = False, 
                             peak_demand_kw: float = 0) -> Dict:
        """Calculate monthly electricity bill"""
        
        if kwh_usage <= 0:
            return self._empty_bill()
        
        # Select appropriate rate structure
        if include_demand_charges:
            rates = self._get_commercial_rates(utility)
        else:
            rates = self._get_residential_rates(utility)
        
        # Calculate base components
        base_charge = rates['base_charge']
        
        # Calculate usage charges
        if include_demand_charges:
            # Commercial rates (single rate)
            delivery_charge = kwh_usage * rates['delivery_rate']
            supply_charge = kwh_usage * rates['supply_rate']
            usage_charge = delivery_charge + supply_charge
        else:
            # Residential tiered rates
            usage_charge = self._calculate_tiered_usage_charge(kwh_usage, rates)
        
        # Calculate demand charges
        demand_charge = 0.0
        if include_demand_charges and peak_demand_kw > rates.get('demand_threshold', 10):
            demand_charge = peak_demand_kw * rates['demand_charge']
        
        # Calculate subtotal
        subtotal = base_charge + usage_charge + demand_charge
        
        # Calculate taxes and fees
        taxes_and_fees = subtotal * rates['taxes_and_fees_rate']
        
        # Total bill
        total_bill = subtotal + taxes_and_fees
        
        return {
            'base_charge': round(base_charge, 2),
            'usage_charge': round(usage_charge, 2),
            'demand_charge': round(demand_charge, 2),
            'taxes_and_fees': round(taxes_and_fees, 2),
            'subtotal': round(subtotal, 2),
            'total_bill': round(total_bill, 2),
            'effective_rate': round(total_bill / kwh_usage, 4) if kwh_usage > 0 else 0,
            'utility': rates['utility_name'],
            'rate_schedule': rates['rate_schedule']
        }
    
    def _calculate_tiered_usage_charge(self, kwh_usage: float, rates: Dict) -> float:
        """Calculate usage charge with tiered rates"""
        tier_threshold = rates['tier_threshold']
        
        if kwh_usage <= tier_threshold:
            # All usage in first tier
            delivery_charge = kwh_usage * rates['delivery_rate_tier1']
        else:
            # Split between tiers
            tier1_usage = tier_threshold
            tier2_usage = kwh_usage - tier_threshold
            
            delivery_charge = (tier1_usage * rates['delivery_rate_tier1'] + 
                             tier2_usage * rates['delivery_rate_tier2'])
        
        # Add supply charge
        supply_charge = kwh_usage * rates['supply_rate']
        
        return delivery_charge + supply_charge
    
    def _get_residential_rates(self, utility: str) -> Dict:
        """Get residential rate structure"""
        if utility.lower() in ['national_grid', 'nationalgrid', 'ng']:
            return self.national_grid_residential
        else:
            return self.coned_residential  # Default to ConEd
    
    def _get_commercial_rates(self, utility: str) -> Dict:
        """Get commercial rate structure"""
        if utility.lower() in ['national_grid', 'nationalgrid', 'ng']:
            return self.national_grid_commercial
        else:
            return self.coned_commercial  # Default to ConEd
    
    def _empty_bill(self) -> Dict:
        """Return empty bill structure"""
        return {
            'base_charge': 0.0,
            'usage_charge': 0.0,
            'demand_charge': 0.0,
            'taxes_and_fees': 0.0,
            'subtotal': 0.0,
            'total_bill': 0.0,
            'effective_rate': 0.0,
            'utility': 'Unknown',
            'rate_schedule': 'Unknown'
        }
    
    def get_rate_info(self, utility: str = 'coned') -> Dict:
        """Get rate structure information"""
        rates = self._get_residential_rates(utility)
        
        return {
            'utility': rates['utility_name'],
            'rate_schedule': rates['rate_schedule'],
            'base_charge': rates['base_charge'],
            'first_tier_rate': rates['delivery_rate_tier1'] + rates['supply_rate'],
            'second_tier_rate': rates.get('delivery_rate_tier2', rates['delivery_rate_tier1']) + rates['supply_rate'],
            'tier_threshold': rates['tier_threshold'],
            'supply_rate': rates['supply_rate'],
            'taxes_and_fees_rate': rates['taxes_and_fees_rate']
        }
    
    def estimate_peak_demand(self, monthly_kwh: float, property_type: str = 'residential') -> float:
        """Estimate peak demand (kW) from monthly consumption"""
        if monthly_kwh <= 0:
            return 0.0
        
        # Load factor estimates by property type
        load_factors = {
            'residential': 0.25,    # Typical residential load factor
            'office': 0.55,         # Office buildings
            'retail': 0.45,         # Retail stores
            'warehouse': 0.65,      # Industrial/warehouse
            'mixed': 0.35          # Mixed use
        }
        
        load_factor = load_factors.get(property_type.lower(), 0.30)
        
        # Calculate average demand
        hours_in_month = 730  # Approximate
        avg_demand_kw = monthly_kwh / hours_in_month
        
        # Estimate peak demand using load factor
        peak_demand_kw = avg_demand_kw / load_factor
        
        return round(peak_demand_kw, 1)
    
    def calculate_annual_cost_comparison(self, annual_kwh: float) -> Dict:
        """Compare annual costs between utilities"""
        monthly_kwh = annual_kwh / 12
        
        # Calculate with both utilities
        coned_monthly = self.calculate_monthly_bill(monthly_kwh, 'coned')
        ng_monthly = self.calculate_monthly_bill(monthly_kwh, 'national_grid')
        
        return {
            'annual_kwh': annual_kwh,
            'coned_annual_cost': coned_monthly['total_bill'] * 12,
            'national_grid_annual_cost': ng_monthly['total_bill'] * 12,
            'savings_with_cheaper': abs(coned_monthly['total_bill'] - ng_monthly['total_bill']) * 12,
            'cheaper_utility': 'Con Edison' if coned_monthly['total_bill'] < ng_monthly['total_bill'] else 'National Grid'
        }
    
    def get_conservation_savings(self, current_kwh: float, reduction_percent: float, 
                               utility: str = 'coned') -> Dict:
        """Calculate potential savings from energy conservation"""
        if reduction_percent <= 0 or reduction_percent >= 100:
            return {}
        
        current_bill = self.calculate_monthly_bill(current_kwh, utility)
        reduced_kwh = current_kwh * (1 - reduction_percent / 100)
        reduced_bill = self.calculate_monthly_bill(reduced_kwh, utility)
        
        monthly_savings = current_bill['total_bill'] - reduced_bill['total_bill']
        annual_savings = monthly_savings * 12
        
        return {
            'current_monthly_kwh': current_kwh,
            'reduced_monthly_kwh': reduced_kwh,
            'kwh_reduction': current_kwh - reduced_kwh,
            'current_monthly_bill': current_bill['total_bill'],
            'reduced_monthly_bill': reduced_bill['total_bill'],
            'monthly_savings': monthly_savings,
            'annual_savings': annual_savings,
            'reduction_percent': reduction_percent
        }
