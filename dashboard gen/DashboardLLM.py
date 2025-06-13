import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm import LLM
from PowerBiTools import query_powerbi, select_ui_component, assemble_dashboard
from typing import Dict, List, Any, Optional


class DashboardLLM(LLM):
    """
    Enhanced LLM class specifically for dashboard generation.
    Inherits from the main LLM class and adds PowerBI dashboard tools.
    """
    
    def __init__(self):
        super().__init__()
        self.dashboard_components = []  # Track components for current dashboard
        self.register_dashboard_tools()
        
    def register_dashboard_tools(self):
        """
        Register PowerBI dashboard tools.
        """
        try:
            self.register_tool("query_powerbi", query_powerbi)
            self.register_tool("select_ui_component", select_ui_component) 
            self.register_tool("assemble_dashboard", assemble_dashboard)
            
            print("[DEBUG] PowerBI dashboard tools registered successfully")
            
        except Exception as e:
            print(f"[DEBUG] Failed to register PowerBI tools: {str(e)}")
    
    def get_dashboard_system_prompt(self) -> str:
        """
        Enhanced system prompt for dashboard generation following ReAct pattern.
        """
        return """
You are a specialized assistant for generating interactive dashboards from natural language prompts.

DASHBOARD GENERATION WORKFLOW (ReAct Pattern):

When a user asks for a dashboard, follow this exact sequence:

1. ANALYZE the user request to identify what data they want to visualize
2. CALL query_powerbi for each data requirement with appropriate measures:
   - revenue_monthly: Monthly revenue timeseries
   - top_products: Top products by production  
   - availability_kpi: Availability KPI metric
   - production_by_type: Production distribution by steel type
   
3. For each query result, CALL select_ui_component to choose the right visualization
4. ACCUMULATE all components in your reasoning
5. When you have all needed components, CALL assemble_dashboard with the complete list

EXAMPLE FLOW:
User: "Show me monthly revenue and top 5 products"

Step 1: Query monthly revenue data
```json
{"tool_call": {"name": "query_powerbi", "arguments": {"measure": "revenue_monthly"}}}
```

Step 2: Select component for timeseries data  
```json
{"tool_call": {"name": "select_ui_component", "arguments": {"data_shape": "timeseries"}}}
```

Step 3: Query top products data
```json
{"tool_call": {"name": "query_powerbi", "arguments": {"measure": "top_products"}}}
```

Step 4: Select component for products data
```json
{"tool_call": {"name": "select_ui_component", "arguments": {"data_shape": "table"}}}
```

Step 5: Assemble complete dashboard
```json
{"tool_call": {"name": "assemble_dashboard", "arguments": {"components": [
    {"component": "LineChartComponent", "props": {...}},
    {"component": "TableComponent", "props": {...}}
]}}}
```

AVAILABLE MEASURES:
- revenue_monthly: Monthly revenue over time
- top_products: Top products by production volume
- availability_kpi: Equipment availability percentage
- production_by_type: Steel production by type/category

COMPONENT TYPES:
- LineChartComponent: For timeseries data
- PieChartComponent: For categorical distributions
- KPIBoxComponent: For single metrics
- TableComponent: For detailed data
- BarChartComponent: For comparisons

Remember: Your final response should be the complete HTML dashboard from assemble_dashboard.
"""

    def get_completion_dashboard(self, prompt: str, max_tool_calls: int = 10) -> str:
        """
        Enhanced completion method specifically for dashboard generation.
        """
        # Reset dashboard components for new request
        self.dashboard_components = []
        
        # Use enhanced system prompt for dashboard generation
        dashboard_system_prompt = self.get_dashboard_system_prompt()
        
        return self.get_completion(
            prompt=prompt, 
            system_prompt_override=dashboard_system_prompt,
            max_tool_calls=max_tool_calls
        )
    
    def save_dashboard(self, html_content: str, filename: str = None) -> str:
        """
        Save the generated dashboard HTML to a file.
        
        Args:
            html_content (str): The HTML content to save
            filename (str): Optional filename, auto-generated if not provided
            
        Returns:
            str: The filepath where the dashboard was saved
        """
        if not filename:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"dashboard_{timestamp}.html"
        
        # Ensure we're saving in the dashboard gen folder
        filepath = os.path.join("dashboard gen", "generated_dashboards", filename)
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"[DEBUG] Dashboard saved to: {filepath}")
            return filepath
        except Exception as e:
            print(f"[DEBUG] Error saving dashboard: {str(e)}")
            return None
    
    def generate_dashboard_from_prompt(self, user_prompt: str, save_file: bool = True) -> Dict[str, Any]:
        """
        Complete workflow: Generate dashboard from user prompt and optionally save it.
        
        Args:
            user_prompt (str): User's natural language request
            save_file (bool): Whether to save the generated HTML file
            
        Returns:
            Dict: Contains 'html_content', 'filepath' (if saved), and 'components_used'
        """
        print(f"[DEBUG] Generating dashboard from prompt: {user_prompt}")
        
        # Generate the dashboard HTML
        html_content = self.get_completion_dashboard(user_prompt)
        
        result = {
            'html_content': html_content,
            'components_used': len(self.dashboard_components),
            'filepath': None
        }
        
        # Save if requested
        if save_file and html_content and '<html>' in html_content:
            filepath = self.save_dashboard(html_content)
            result['filepath'] = filepath
            
        return result 