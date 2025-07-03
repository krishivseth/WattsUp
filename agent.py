import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os

from tools.address_search_tool import AddressSearchTool
from tools.building_info_tool import BuildingInfoTool  
from tools.electricity_estimation_tool import ElectricityEstimationTool
from tools.safety_analysis_tool import SafetyAnalysisTool
from tools.route_analysis_tool import RouteAnalysisTool
from tools.openai_summary_tool import OpenAISummaryTool

logger = logging.getLogger(__name__)

class PropertyAnalysisAgent:
    """
    Intelligent agent for property analysis with multiple specialized tools
    """
    
    def __init__(self, data_processor, bill_estimator, address_matcher, 
                 safety_analyzer, route_analyzer, openai_api_key: Optional[str] = None):
        """Initialize the agent with required components"""
        self.data_processor = data_processor
        self.bill_estimator = bill_estimator
        self.address_matcher = address_matcher
        self.safety_analyzer = safety_analyzer
        self.route_analyzer = route_analyzer
        
        # Initialize tools
        self.tools = {
            'address_search': AddressSearchTool(address_matcher),
            'building_info': BuildingInfoTool(data_processor),
            'electricity_estimation': ElectricityEstimationTool(bill_estimator),
            'safety_analysis': SafetyAnalysisTool(safety_analyzer),
            'route_analysis': RouteAnalysisTool(route_analyzer),
            'openai_summary': OpenAISummaryTool(openai_api_key)
        }
        
        # Conversation memory for context
        self.conversation_memory = []
        
        # Configuration for summary generation
        self.use_ai_summaries = self.tools['openai_summary'].available if 'openai_summary' in self.tools else False
        
    def get_available_tools(self) -> Dict[str, str]:
        """Get list of available tools with descriptions"""
        return {
            name: tool.get_description() 
            for name, tool in self.tools.items()
        }
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with parameters"""
        try:
            if tool_name not in self.tools:
                return {
                    'success': False,
                    'error': f'Tool "{tool_name}" not found. Available tools: {list(self.tools.keys())}'
                }
            
            tool = self.tools[tool_name]
            result = tool.execute(parameters)
            
            # Add to conversation memory
            self.conversation_memory.append({
                'timestamp': datetime.now().isoformat(),
                'tool': tool_name,
                'parameters': parameters,
                'result': result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Tool execution failed for {tool_name}: {e}")
            return {
                'success': False,
                'error': f'Tool execution failed: {str(e)}'
            }
    
    def analyze_property(self, address: str, num_rooms: int, 
                        apartment_type: str = None, 
                        include_safety: bool = True,
                        include_routes: bool = False,
                        destination: str = None,
                        use_ai_summary: bool = None,
                        summary_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Comprehensive property analysis using multiple tools
        """
        try:
            analysis_start = datetime.now()
            results = {
                'query': {
                    'address': address,
                    'num_rooms': num_rooms,
                    'apartment_type': apartment_type,
                    'include_safety': include_safety,
                    'include_routes': include_routes,
                    'destination': destination,
                    'use_ai_summary': use_ai_summary,
                    'summary_type': summary_type
                },
                'analysis_timestamp': analysis_start.isoformat(),
                'tools_used': [],
                'success': True
            }
            
            # Step 1: Search for address
            logger.info(f"Searching for address: {address}")
            address_result = self.execute_tool('address_search', {
                'address': address,
                'search_type': 'exact_match'
            })
            
            if not address_result.get('success'):
                return {
                    'success': False,
                    'error': 'Could not find building for the specified address',
                    'address_search_result': address_result
                }
            
            building_data = address_result.get('data', {}).get('building_data')
            results['tools_used'].append('address_search')
            results['building_search'] = address_result
            
            # Step 2: Get detailed building information
            logger.info("Getting detailed building information")
            building_info_result = self.execute_tool('building_info', {
                'property_id': building_data.get('Property ID'),
                'include_statistics': True
            })
            
            if building_info_result.get('success'):
                results['tools_used'].append('building_info')
                results['building_details'] = building_info_result
            
            # Step 3: Calculate electricity estimation
            logger.info("Calculating electricity estimation")
            electricity_result = self.execute_tool('electricity_estimation', {
                'building_data': building_data,
                'num_rooms': num_rooms,
                'apartment_type': apartment_type,
                'building_type': 'residential',
                'include_demand_charges': False
            })
            
            if electricity_result.get('success'):
                results['tools_used'].append('electricity_estimation')
                results['electricity_analysis'] = electricity_result
            else:
                results['electricity_analysis'] = {
                    'success': False,
                    'error': 'Could not calculate electricity estimates',
                    'details': electricity_result
                }
            
            # Step 4: Safety analysis (if requested)
            if include_safety:
                logger.info("Performing safety analysis")
                # Extract location information for safety analysis
                borough = building_data.get('Borough')
                zip_code = building_data.get('incident_zip')  # if available
                
                safety_result = self.execute_tool('safety_analysis', {
                    'address': address,
                    'borough': borough,
                    'zip_code': zip_code,
                    'radius_miles': 0.5
                })
                
                if safety_result.get('success'):
                    results['tools_used'].append('safety_analysis')
                    results['safety_analysis'] = safety_result
            
            # Step 5: Route analysis (if requested)
            if include_routes and destination:
                logger.info(f"Analyzing routes from {address} to {destination}")
                route_result = self.execute_tool('route_analysis', {
                    'origin': address,
                    'destination': destination,
                    'mode': 'driving'
                })
                
                if route_result.get('success'):
                    results['tools_used'].append('route_analysis')
                    results['route_analysis'] = route_result
            
            # Step 6: Generate summary (AI or manual)
            use_ai = use_ai_summary if use_ai_summary is not None else self.use_ai_summaries
            
            if use_ai and self.tools['openai_summary'].available:
                logger.info(f"Generating AI summary (type: {summary_type})")
                ai_summary_result = self.execute_tool('openai_summary', {
                    'data': results,
                    'summary_type': summary_type,
                    'max_tokens': 600,
                    'temperature': 0.7
                })
                
                if ai_summary_result.get('success'):
                    results['tools_used'].append('openai_summary')
                    results['ai_summary'] = ai_summary_result.get('data', {})
                    results['summary_method'] = 'ai_generated'
                else:
                    # Fallback to manual summary if AI fails
                    results['summary'] = self._generate_analysis_summary(results)
                    results['summary_method'] = 'manual_fallback'
                    results['ai_summary_error'] = ai_summary_result.get('error')
            else:
                # Use manual summary generation
                results['summary'] = self._generate_analysis_summary(results)
                results['summary_method'] = 'manual'
            
            results['analysis_duration'] = (datetime.now() - analysis_start).total_seconds()
            
            return results
            
        except Exception as e:
            logger.error(f"Property analysis failed: {e}")
            return {
                'success': False,
                'error': f'Property analysis failed: {str(e)}',
                'timestamp': datetime.now().isoformat()
            }
    
    def generate_ai_summary(self, analysis_data: Dict[str, Any], 
                           summary_type: str = 'comprehensive') -> Dict[str, Any]:
        """
        Generate an AI summary from existing analysis data
        """
        try:
            if not self.tools['openai_summary'].available:
                return {
                    'success': False,
                    'error': 'OpenAI summary tool not available'
                }
            
            result = self.execute_tool('openai_summary', {
                'data': analysis_data,
                'summary_type': summary_type
            })
            
            return result
            
        except Exception as e:
            logger.error(f"AI summary generation failed: {e}")
            return {
                'success': False,
                'error': f'AI summary generation failed: {str(e)}'
            }
    
    def _generate_analysis_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a manual summary of the analysis results (fallback method)"""
        summary = {
            'property_found': results.get('building_search', {}).get('success', False),
            'electricity_estimated': results.get('electricity_analysis', {}).get('success', False),
            'safety_analyzed': 'safety_analysis' in results,
            'routes_analyzed': 'route_analysis' in results,
            'tools_used_count': len(results.get('tools_used', [])),
            'recommendations': []
        }
        
        # Add key insights
        if results.get('electricity_analysis', {}).get('success'):
            electricity_data = results['electricity_analysis']
            annual_summary = electricity_data.get('data', {}).get('annual_summary', {})
            if annual_summary:
                summary['estimated_annual_bill'] = annual_summary.get('total_bill')
                summary['estimated_monthly_average'] = annual_summary.get('average_monthly_bill')
        
        if results.get('safety_analysis', {}).get('success'):
            safety_data = results['safety_analysis'].get('data', {})
            summary['safety_grade'] = safety_data.get('overall_grade')
            summary['safety_score'] = safety_data.get('overall_score')
        
        # Generate recommendations
        recommendations = []
        
        if summary.get('estimated_annual_bill'):
            annual_bill = summary['estimated_annual_bill']
            if annual_bill > 2000:
                recommendations.append("Consider energy efficiency upgrades to reduce high electricity costs")
            elif annual_bill < 800:
                recommendations.append("Electricity costs appear reasonable for this property size")
        
        if summary.get('safety_grade'):
            safety_grade = summary['safety_grade']
            if safety_grade in ['D', 'F']:
                recommendations.append("Consider additional safety precautions due to lower area safety rating")
            elif safety_grade in ['A', 'B']:
                recommendations.append("Area has good safety ratings")
        
        summary['recommendations'] = recommendations
        summary['generation_method'] = 'manual'
        return summary
    
    def set_ai_summary_preference(self, use_ai: bool):
        """Set preference for AI vs manual summary generation"""
        self.use_ai_summaries = use_ai and self.tools['openai_summary'].available
        logger.info(f"AI summary preference set to: {self.use_ai_summaries}")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation memory/history"""
        return self.conversation_memory
    
    def clear_conversation_history(self):
        """Clear the conversation memory"""
        self.conversation_memory = []
    
    def get_tool_help(self, tool_name: str) -> Dict[str, Any]:
        """Get detailed help for a specific tool"""
        if tool_name not in self.tools:
            return {
                'error': f'Tool "{tool_name}" not found',
                'available_tools': list(self.tools.keys())
            }
        
        tool = self.tools[tool_name]
        return {
            'name': tool_name,
            'description': tool.get_description(),
            'parameters': tool.get_parameters(),
            'examples': tool.get_examples() if hasattr(tool, 'get_examples') else []
        } 