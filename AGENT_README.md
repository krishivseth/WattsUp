# PropertyAnalysisAgent System

## Overview

The PropertyAnalysisAgent converts the original electricity estimation functionality into a modular, agent-based system with specialized tools. Instead of a single monolithic function, the system now uses multiple focused tools that can be combined to provide comprehensive property analysis.

## Key Benefits

- **Modular Design**: Each tool has a specific purpose and can be used independently
- **Scalable**: Easy to add new tools and capabilities
- **Consistent Interface**: All tools follow the same standardized API pattern
- **Memory**: Agent maintains conversation history for context
- **Comprehensive Analysis**: Can combine multiple tools for complete property assessment

## Available Tools

### 1. Address Search Tool (`address_search`)
**Purpose**: Find and match building addresses in the NYC database

**Capabilities**:
- Exact address matching
- Fuzzy search for similar addresses
- Partial address matching
- Confidence scoring

**Example Usage**:
```json
POST /api/agent/tool/address_search
{
    "address": "123 Main St, Queens, NY",
    "search_type": "exact_match"
}
```

### 2. Building Info Tool (`building_info`)
**Purpose**: Retrieve detailed building information and statistics

**Capabilities**:
- Basic building details (address, type, year built)
- Energy consumption data
- Property characteristics
- Statistical comparisons with similar buildings
- Efficiency percentile rankings

**Example Usage**:
```json
POST /api/agent/tool/building_info
{
    "property_id": "NYC123456",
    "include_statistics": true,
    "include_comparisons": true
}
```

### 3. Electricity Estimation Tool (`electricity_estimation`)
**Purpose**: Calculate detailed electricity consumption and bill estimates

**Capabilities**:
- Monthly electricity bill projections
- Annual cost summaries
- Seasonal variation analysis
- Cost breakdown (base charges, usage, demand)
- Energy efficiency recommendations
- Building efficiency analysis

**Example Usage**:
```json
POST /api/agent/tool/electricity_estimation
{
    "building_data": {...},
    "num_rooms": 3,
    "apartment_type": "2br",
    "building_type": "residential"
}
```

### 4. Safety Analysis Tool (`safety_analysis`)
**Purpose**: Analyze area safety based on crime data

**Capabilities**:
- Safety ratings and grades
- Crime pattern analysis
- Risk assessments
- Safety recommendations
- Comparative context with other areas

**Example Usage**:
```json
POST /api/agent/tool/safety_analysis
{
    "address": "123 Main St, Queens, NY",
    "borough": "QUEENS",
    "radius_miles": 0.5
}
```

### 5. Route Analysis Tool (`route_analysis`)
**Purpose**: Analyze safe routes between locations

**Capabilities**:
- Multiple route options
- Safety scoring for each route
- Transportation mode support (driving, walking, transit)
- Route comparisons and recommendations
- Transportation-specific advice

**Example Usage**:
```json
POST /api/agent/tool/route_analysis
{
    "origin": "123 Main St, Queens, NY",
    "destination": "Times Square, New York, NY",
    "mode": "driving"
}
```

### 6. OpenAI Summary Tool (`openai_summary`) ✨
**Purpose**: Generate intelligent, natural language summaries using OpenAI's GPT models

**Capabilities**:
- Natural language summary generation
- Multiple summary types (comprehensive, electricity, safety, financial, brief)
- Contextual analysis and insights
- Structured and unstructured output formats
- Token usage tracking

**Setup Requirements**:
- Install OpenAI library: `pip install openai`
- Set environment variable: `OPENAI_API_KEY=your_api_key_here`

**Example Usage**:
```json
POST /api/agent/tool/openai_summary
{
    "data": {...}, // Analysis data from other tools
    "summary_type": "comprehensive",
    "max_tokens": 600,
    "temperature": 0.7
}
```

**Summary Types**:
- `comprehensive`: Complete analysis with all aspects
- `electricity`: Focus on energy costs and efficiency
- `safety`: Focus on neighborhood safety
- `financial`: Focus on costs and budgeting
- `brief`: Short bullet-point summary

## API Endpoints

### Agent Management

#### Get Available Tools
```http
GET /api/agent/tools
```
Returns list of all available tools with descriptions.

#### Get Tool Help
```http
GET /api/agent/tool/{tool_name}/help
```
Returns detailed documentation for a specific tool.

#### Execute Individual Tool
```http
POST /api/agent/tool/{tool_name}
Content-Type: application/json

{tool-specific parameters}
```

### Comprehensive Analysis

#### Full Property Analysis
```http
POST /api/agent/analyze
Content-Type: application/json

{
    "address": "123 Main St, Queens, NY",
    "num_rooms": 3,
    "apartment_type": "2br",
    "include_safety": true,
    "include_routes": false,
    "destination": "Times Square, NY",
    "use_ai_summary": true,
    "summary_type": "comprehensive"
}
```

This endpoint orchestrates multiple tools to provide:
- Building search and validation
- Detailed building information
- Electricity cost estimation
- Safety analysis (optional)
- Route analysis (optional)
- Comprehensive summary with recommendations

### Conversation Management

#### Get Conversation History
```http
GET /api/agent/conversation
```

#### Clear Conversation History
```http
DELETE /api/agent/conversation
```

### AI Summary Management

#### Generate AI Summary from Existing Data
```http
POST /api/agent/summary/generate
Content-Type: application/json

{
    "analysis_data": {...}, // Previous analysis results
    "summary_type": "comprehensive" // optional
}
```

#### Set AI Summary Preference
```http
POST /api/agent/summary/preference
Content-Type: application/json

{
    "use_ai": true
}
```

#### Get AI Summary Status
```http
GET /api/agent/summary/preference
```

Returns information about OpenAI configuration and current preferences.

## Example Workflows

### Basic Electricity Estimation
```python
import requests

# 1. Search for building
search_response = requests.post(
    "http://localhost:61188/api/agent/tool/address_search",
    json={"address": "123 Main St, Queens, NY", "search_type": "exact_match"}
)
building_data = search_response.json()['data']['building_data']

# 2. Estimate electricity costs
estimation_response = requests.post(
    "http://localhost:61188/api/agent/tool/electricity_estimation",
    json={
        "building_data": building_data,
        "num_rooms": 3,
        "apartment_type": "2br"
    }
)
electricity_analysis = estimation_response.json()['data']
```

### Comprehensive Property Analysis
```python
# Single call for complete analysis
response = requests.post(
    "http://localhost:61188/api/agent/analyze",
    json={
        "address": "123 Main St, Queens, NY",
        "num_rooms": 3,
        "apartment_type": "2br",
        "include_safety": True,
        "include_routes": True,
        "destination": "Times Square, New York, NY"
    }
)
complete_analysis = response.json()
```

### AI-Enhanced Property Analysis
```python
# Set up OpenAI API key first
import os
os.environ['OPENAI_API_KEY'] = 'your_api_key_here'

# Enable AI summaries globally
requests.post("http://localhost:61188/api/agent/summary/preference", 
              json={"use_ai": True})

# Run analysis with AI summary
response = requests.post("http://localhost:61188/api/agent/analyze", json={
    "address": "123 Main St, Queens, NY",
    "num_rooms": 3,
    "apartment_type": "2br",
    "include_safety": True,
    "use_ai_summary": True,
    "summary_type": "comprehensive"
})

analysis = response.json()
if 'ai_summary' in analysis:
    ai_summary = analysis['ai_summary']['summary']
    print("AI Generated Summary:")
    print(ai_summary['full_text'])
```

### Generate AI Summary from Existing Data
```python
# First run analysis without AI summary
analysis = requests.post("http://localhost:61188/api/agent/analyze", json={
    "address": "123 Main St, Queens, NY",
    "num_rooms": 3,
    "use_ai_summary": False
}).json()

# Then generate different types of AI summaries
for summary_type in ['brief', 'electricity', 'financial']:
    summary_response = requests.post(
        "http://localhost:61188/api/agent/summary/generate",
        json={
            "analysis_data": analysis,
            "summary_type": summary_type
        }
    )
    summary = summary_response.json()
    print(f"{summary_type.title()} Summary:")
    print(summary['data']['summary']['full_text'])
```

## Migration from Original System

### Before (Original System)
```python
# Single endpoint approach
response = requests.post("/api/estimate", json={
    "address": "123 Main St, Queens, NY",
    "num_rooms": 3,
    "apartment_type": "2br"
})
```

### After (Agent System)
```python
# Option 1: Use comprehensive analysis (similar to original)
response = requests.post("/api/agent/analyze", json={
    "address": "123 Main St, Queens, NY",
    "num_rooms": 3,
    "apartment_type": "2br"
})

# Option 2: Use individual tools for more control
tools = requests.get("/api/agent/tools").json()
search_result = requests.post("/api/agent/tool/address_search", json={...})
estimation_result = requests.post("/api/agent/tool/electricity_estimation", json={...})
```

## Error Handling

All agent tools return standardized responses:

### Success Response
```json
{
    "success": true,
    "tool_name": "address_search",
    "data": {...},
    "message": "Found exact match for address: 123 Main St"
}
```

### Error Response
```json
{
    "success": false,
    "tool_name": "address_search",
    "error": "No exact match found for address: 123 Main St",
    "details": {...}
}
```

## Setup and Installation

### Basic Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python app.py
```

### Enable AI Summaries (Optional)
```bash
# Install OpenAI library
pip install openai

# Set your OpenAI API key
export OPENAI_API_KEY="your_api_key_here"

# Or add to your environment file
echo "OPENAI_API_KEY=your_api_key_here" >> .env
```

## Testing

Run the test script to verify the agent system:

```bash
python test_agent_system.py
```

This will test:
- Server connectivity
- Available tools
- Individual tool functionality
- Comprehensive analysis
- AI summary generation (if OpenAI is configured)
- Error handling

## Development

### Adding New Tools

1. Create a new tool class in `tools/` directory:
```python
from .base_tool import BaseTool

class NewTool(BaseTool):
    def __init__(self, dependencies):
        super().__init__("new_tool")
        self.dependencies = dependencies
        
    def execute(self, parameters):
        # Tool implementation
        pass
        
    def get_description(self):
        return "Description of what this tool does"
        
    def get_parameters(self):
        return {...}
```

2. Register the tool in `agent.py`:
```python
self.tools['new_tool'] = NewTool(dependencies)
```

### Tool Development Guidelines

- Inherit from `BaseTool`
- Use standardized response formats
- Validate input parameters
- Provide clear error messages
- Include comprehensive documentation
- Add examples and help text

## Performance Considerations

- Tools can be used independently to minimize processing time
- Comprehensive analysis chains multiple tools but provides complete results
- Conversation memory is maintained in-memory (consider persistent storage for production)
- Individual tools can be cached for frequently accessed data

## Backwards Compatibility

The original API endpoints (`/api/estimate`, `/api/search`, etc.) remain fully functional. The agent system provides additional capabilities without breaking existing integrations.

## Support

For questions or issues with the agent system:
1. Check tool help: `GET /api/agent/tool/{tool_name}/help`
2. Run test script: `python test_agent_system.py`
3. Review conversation history: `GET /api/agent/conversation`
4. Check server logs for detailed error information 