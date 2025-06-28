# NYC Electricity Bill Estimation Backend

Frontend: A React + TypeScript + Tailwind CSS Chrome extension that calculates monthly energy costs for StreetEasy listings.

Backend: A Flask-based backend API for estimating monthly electricity bills for NYC residential apartments using building energy data. 

Original frontend repo [here](https://github.com/snow-kang/wattsup-ui).

## 🏗️ System Architecture

```
├── app.py                    # Main Flask application
├── data_processor.py         # CSV data loading and processing
├── address_matcher.py        # Fuzzy address matching
├── bill_estimator.py         # Core estimation algorithms
├── seasonality_factors.py    # Monthly usage patterns
├── rate_calculator.py        # NYC utility rate calculations
├── test_system.py           # System validation tests
├── requirements.txt         # Python dependencies
└── NYC_Building_Energy_Filtered_Clean.csv  # Building energy data
```

## 🚀 Quick Start

### Backend Installation (root level)

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Ensure the filtered CSV file is present:**
```bash
ls -la NYC_Building_Energy_Filtered_Clean.csv
```

3. **Test the system:**
```bash
python test_system.py
```

4. **Start the Flask application:**
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## 📦 Frontend Installation (within the frontend copy folder)

1. **Install dependencies:**

   ```bash
   npm install
   ```

2. **Start development server:**

   ```bash
   npm run dev
   ```

3. **Build the extension:**
   ```bash
   npm run build:extension
   ```

## 🔧 Loading the Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `dist` folder (created after building)
5. The extension will appear in your Chrome toolbar

## 📡 API Endpoints

### Health Check
```bash
GET /health
```

### Estimate Electricity Bill
```bash
POST /api/estimate
Content-Type: application/json

{
  "address": "1870 Pelham Parkway South, Bronx",
  "num_rooms": 2,
  "apartment_type": "1br",
  "building_type": "residential",
  "include_demand_charges": false
}
```

### Search Buildings
```bash
GET /api/search?q=Pelham&limit=5
```

### Get Building Details
```bash
GET /api/building/<property_id>
```

## 🧮 Estimation Algorithm

### Core Components

1. **Base Consumption**: Uses building's weather-normalized electricity intensity (kWh/ft²)
2. **Apartment Sizing**: Estimates apartment size based on room count
3. **Building Efficiency**: Adjusts for building age and type
4. **Seasonality**: Applies NYC-specific monthly usage patterns
5. **Rate Calculation**: Uses current ConEd/National Grid rate structures

### Key Factors

```python
# Building efficiency by age
if year_built >= 2010: efficiency_factor = 0.85  # More efficient
elif year_built >= 1980: efficiency_factor = 1.00  # Average
else: efficiency_factor = 1.10  # Less efficient

# Apartment size estimates
apartment_sizes = {
    0: 400,   # Studio
    1: 650,   # 1BR  
    2: 850,   # 2BR
    3: 1100,  # 3BR
    4: 1400   # 4BR+
}

# Seasonal factors (example for Multifamily Housing)
seasonal_factors = {
    1: 1.30,   # January (high heating)
    7: 1.15,   # July (peak cooling)
    5: 0.80    # May (mild weather)
}
```

## 💡 Example Usage

### cURL Examples

```bash
# Estimate bill for 2BR apartment
curl -X POST http://localhost:5000/api/estimate \
  -H "Content-Type: application/json" \
  -d '{
    "address": "1870 Pelham Parkway South, Bronx",
    "num_rooms": 2,
    "apartment_type": "1br"
  }'

# Search for buildings
curl "http://localhost:5000/api/search?q=Pelham&limit=5"
```

### Python Example

```python
import requests

# Estimate electricity bill
response = requests.post('http://localhost:5000/api/estimate', json={
    'address': '1870 Pelham Parkway South, Bronx',
    'num_rooms': 2,
    'apartment_type': '1br',
    'building_type': 'residential'
})

if response.status_code == 200:
    data = response.json()
    print(f"Annual total: ${data['annual_summary']['total_bill']}")
    print(f"Average monthly: ${data['annual_summary']['average_monthly_bill']}")
```

## 📊 Sample Response

```json
{
  "building_info": {
    "property_name": "1870 Pelham Parkway South",
    "address": "1870 Pelham Parkway South",
    "city": "Bronx",
    "borough": "BRONX",
    "property_type": "Multifamily Housing",
    "year_built": "1960",
    "building_efficiency": "average"
  },
  "estimation_parameters": {
    "num_rooms": 2,
    "estimated_apartment_sqft": 850,
    "building_intensity_kwh_per_sqft": 30.1,
    "efficiency_factor": 0.92
  },
  "monthly_estimates": [
    {
      "month": "January",
      "kwh_estimate": 485,
      "estimated_bill": 90.35,
      "seasonal_factor": 1.30
    }
  ],
  "annual_summary": {
    "total_kwh": 4680,
    "total_bill": 987.50,
    "average_monthly_bill": 82.29,
    "peak_month": "August",
    "peak_bill": 125.40
  },
  "rate_structure": {
    "utility": "Con Edison",
    "base_charge": 18.05,
    "first_tier_rate": 0.3011,
    "tier_threshold": 250
  }
}
```

## 🔧 Configuration

### Utility Rates
Update rates in `rate_calculator.py`:

```python
self.coned_residential = {
    'base_charge': 18.05,
    'delivery_rate_tier1': 0.1891,
    'supply_rate': 0.1120,
    'tier_threshold': 250
}
```

### Seasonality Factors
Modify patterns in `seasonality_factors.py`:

```python
'Multifamily Housing': {
    1: 1.30,  # January
    7: 1.15,  # July
    # ... other months
}
```

## 📈 Data Sources

- **Building Data**: NYC Building Energy and Water Data Disclosure (Local Law 84)
- **Utility Rates**: Con Edison and National Grid 2024 rate schedules
- **Seasonality**: NYC energy usage patterns and climate data

## ⚠️ Limitations

1. **Annual Data Only**: Building data is annual; monthly breakdowns are estimated
2. **Rate Accuracy**: Utility rates change periodically and may not reflect current tariffs
3. **Building Match**: Address matching may not be perfect for all addresses
4. **Apartment Assumptions**: Size estimates are approximations based on room count

## 🧪 Testing

Run comprehensive tests:
```bash
python test_system.py
```

Test individual components:
```python
from data_processor import DataProcessor
from bill_estimator import BillEstimator

# Test data loading
dp = DataProcessor('NYC_Building_Energy_Filtered_Clean.csv')
dp.load_data()

# Test estimation
be = BillEstimator(dp)
# ... estimation tests
```

## 📝 Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (missing fields, invalid data)
- `404`: Building not found
- `500`: Internal server error

## 🔮 Future Enhancements

1. **Real-time Rates**: Integration with utility APIs for current rates
2. **Weather Data**: Historical weather data for better seasonality
3. **Machine Learning**: Improve estimates with ML models
4. **Time-of-Use**: Support for time-of-use rate plans
5. **Solar Integration**: Account for rooftop solar generation

## 📞 Support

For issues or questions:
1. Check the test script output: `python test_system.py`
2. Review log files for error details
3. Verify CSV data integrity and column mappings

## 📄 License

This project uses NYC open data and is intended for educational/research purposes.
