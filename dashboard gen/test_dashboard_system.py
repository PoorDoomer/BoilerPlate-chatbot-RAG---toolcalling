#!/usr/bin/env python3
"""
Unit tests for the Dashboard Generation System.
Tests all components including PowerBiTools and DashboardLLM.
"""

import unittest
import os
import sys
import json
import tempfile
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PowerBiTools import query_powerbi, select_ui_component, assemble_dashboard
from DashboardLLM import DashboardLLM


class TestPowerBiTools(unittest.TestCase):
    """Test PowerBI tools functionality."""
    
    def test_query_powerbi_revenue_monthly(self):
        """Test query_powerbi with revenue_monthly measure."""
        result = query_powerbi(measure="revenue_monthly")
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
        # Should be timeseries data
        if result["type"] == "timeseries":
            self.assertIn("labels", result["data"])
            self.assertIn("series", result["data"])
        
    def test_query_powerbi_top_products(self):
        """Test query_powerbi with top_products measure."""
        result = query_powerbi(measure="top_products")
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
    def test_query_powerbi_availability_kpi(self):
        """Test query_powerbi with availability_kpi measure."""
        result = query_powerbi(measure="availability_kpi")
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
        # Should be KPI data
        if result["type"] == "kpi":
            self.assertIn("title", result["data"])
            self.assertIn("value", result["data"])
            
    def test_query_powerbi_production_by_type(self):
        """Test query_powerbi with production_by_type measure."""
        result = query_powerbi(measure="production_by_type")
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
    def test_query_powerbi_custom_expression(self):
        """Test query_powerbi with custom SQL expression."""
        custom_query = "SELECT COUNT(*) as total FROM Production LIMIT 1"
        result = query_powerbi(expression=custom_query)
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
    def test_query_powerbi_with_top_n(self):
        """Test query_powerbi with top_n parameter."""
        result = query_powerbi(measure="top_products", top_n=3)
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)


class TestUIComponentSelection(unittest.TestCase):
    """Test UI component selection functionality."""
    
    def test_select_ui_component_timeseries(self):
        """Test selecting component for timeseries data."""
        result = select_ui_component("timeseries")
        self.assertEqual(result, "LineChartComponent")
        
    def test_select_ui_component_kpi(self):
        """Test selecting component for KPI data."""
        result = select_ui_component("kpi")
        self.assertEqual(result, "KPIBoxComponent")
        
    def test_select_ui_component_table(self):
        """Test selecting component for table data."""
        result = select_ui_component("table")
        self.assertEqual(result, "TableComponent")
        
    def test_select_ui_component_pie(self):
        """Test selecting component for pie chart data."""
        result = select_ui_component("pie")
        self.assertEqual(result, "PieChartComponent")
        
    def test_select_ui_component_bar(self):
        """Test selecting component for bar chart data."""
        result = select_ui_component("bar")
        self.assertEqual(result, "BarChartComponent")
        
    def test_select_ui_component_unknown(self):
        """Test selecting component for unknown data type."""
        result = select_ui_component("unknown_type")
        self.assertEqual(result, "TableComponent")  # Should default to table


class TestDashboardAssembly(unittest.TestCase):
    """Test dashboard assembly functionality."""
    
    def test_assemble_dashboard_single_component(self):
        """Test assembling dashboard with single component."""
        components = [
            {
                "component": "KPIBoxComponent",
                "props": {
                    "title": "Test KPI",
                    "value": 95.5,
                    "delta": 2.3
                }
            }
        ]
        
        result = assemble_dashboard(components)
        
        self.assertIsInstance(result, str)
        self.assertIn("<html>", result)
        self.assertIn("Test KPI", result)
        self.assertIn("95.5", result)
        
    def test_assemble_dashboard_multiple_components(self):
        """Test assembling dashboard with multiple components."""
        components = [
            {
                "component": "KPIBoxComponent",
                "props": {
                    "title": "Availability",
                    "value": 95.5,
                    "delta": None
                }
            },
            {
                "component": "LineChartComponent",
                "props": {
                    "labels": ["Jan", "Feb", "Mar"],
                    "series": [{
                        "name": "Revenue",
                        "data": [100, 150, 200]
                    }]
                }
            }
        ]
        
        result = assemble_dashboard(components)
        
        self.assertIsInstance(result, str)
        self.assertIn("<html>", result)
        self.assertIn("Availability", result)
        self.assertIn("Revenue", result)
        
    def test_assemble_dashboard_empty_components(self):
        """Test assembling dashboard with empty components list."""
        result = assemble_dashboard([])
        
        self.assertIsInstance(result, str)
        self.assertIn("<html>", result)
        
    def test_assemble_dashboard_table_component(self):
        """Test assembling dashboard with table component."""
        components = [
            {
                "component": "TableComponent",
                "props": {
                    "headers": ["Product", "Volume"],
                    "rows": [
                        ["Steel A", "1000"],
                        ["Steel B", "1500"]
                    ]
                }
            }
        ]
        
        result = assemble_dashboard(components)
        
        self.assertIsInstance(result, str)
        self.assertIn("<html>", result)
        self.assertIn("Steel A", result)


class TestDashboardLLM(unittest.TestCase):
    """Test DashboardLLM class functionality."""
    
    def setUp(self):
        """Set up test environment."""
        self.dashboard_llm = DashboardLLM()
        
    def test_dashboard_llm_initialization(self):
        """Test DashboardLLM initialization."""
        self.assertIsInstance(self.dashboard_llm, DashboardLLM)
        self.assertIn("query_powerbi", self.dashboard_llm.tools)
        self.assertIn("select_ui_component", self.dashboard_llm.tools)
        self.assertIn("assemble_dashboard", self.dashboard_llm.tools)
        
    def test_dashboard_system_prompt(self):
        """Test dashboard system prompt generation."""
        prompt = self.dashboard_llm.get_dashboard_system_prompt()
        
        self.assertIsInstance(prompt, str)
        self.assertIn("DASHBOARD GENERATION WORKFLOW", prompt)
        self.assertIn("ReAct Pattern", prompt)
        self.assertIn("query_powerbi", prompt)
        
    def test_execute_query_powerbi_tool(self):
        """Test executing query_powerbi tool through DashboardLLM."""
        result = self.dashboard_llm.execute_tool("query_powerbi", {"measure": "availability_kpi"})
        
        self.assertIsInstance(result, dict)
        self.assertIn("type", result)
        self.assertIn("data", result)
        
    def test_execute_select_ui_component_tool(self):
        """Test executing select_ui_component tool through DashboardLLM."""
        result = self.dashboard_llm.execute_tool("select_ui_component", {"data_shape": "kpi"})
        
        self.assertEqual(result, "KPIBoxComponent")
        
    def test_execute_assemble_dashboard_tool(self):
        """Test executing assemble_dashboard tool through DashboardLLM."""
        test_components = [
            {
                "component": "KPIBoxComponent",
                "props": {
                    "title": "Test",
                    "value": 100,
                    "delta": None
                }
            }
        ]
        
        result = self.dashboard_llm.execute_tool("assemble_dashboard", {"components": test_components})
        
        self.assertIsInstance(result, str)
        self.assertIn("<html>", result)
        
    def test_save_dashboard(self):
        """Test saving dashboard to file."""
        html_content = "<html><body><h1>Test Dashboard</h1></body></html>"
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock the dashboard gen directory
            with patch.object(os.path, 'join', return_value=os.path.join(temp_dir, "test_dashboard.html")):
                with patch('os.makedirs'):
                    filepath = self.dashboard_llm.save_dashboard(html_content, "test_dashboard.html")
                    
                    self.assertIsNotNone(filepath)
                    
    def test_dashboard_tools_registration(self):
        """Test that all dashboard tools are properly registered."""
        tool_names = list(self.dashboard_llm.tools.keys())
        
        self.assertIn("query_powerbi", tool_names)
        self.assertIn("select_ui_component", tool_names)
        self.assertIn("assemble_dashboard", tool_names)
        
        # Verify tools have proper structure
        for tool_name in ["query_powerbi", "select_ui_component", "assemble_dashboard"]:
            tool = self.dashboard_llm.tools[tool_name]
            self.assertIn("function", tool)
            self.assertIn("description", tool)
            self.assertIn("parameters", tool)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete dashboard system."""
    
    def setUp(self):
        """Set up integration test environment."""
        self.dashboard_llm = DashboardLLM()
        
    def test_full_workflow_simulation(self):
        """Test full workflow simulation without LLM calls."""
        # Step 1: Query data
        data_result = query_powerbi(measure="availability_kpi")
        self.assertIsInstance(data_result, dict)
        
        # Step 2: Select component
        component_name = select_ui_component(data_result["type"])
        self.assertIsInstance(component_name, str)
        
        # Step 3: Assemble dashboard
        components = [
            {
                "component": component_name,
                "props": data_result["data"]
            }
        ]
        
        html_result = assemble_dashboard(components)
        self.assertIsInstance(html_result, str)
        self.assertIn("<html>", html_result)
        
    def test_multiple_data_sources_workflow(self):
        """Test workflow with multiple data sources."""
        # Get multiple data types
        kpi_data = query_powerbi(measure="availability_kpi")
        timeseries_data = query_powerbi(measure="revenue_monthly")
        
        # Select appropriate components
        kpi_component = select_ui_component(kpi_data["type"])
        timeseries_component = select_ui_component(timeseries_data["type"])
        
        # Assemble multi-component dashboard
        components = [
            {
                "component": kpi_component,
                "props": kpi_data["data"]
            },
            {
                "component": timeseries_component,
                "props": timeseries_data["data"]
            }
        ]
        
        html_result = assemble_dashboard(components)
        self.assertIsInstance(html_result, str)
        self.assertIn("<html>", html_result)
        
        # Should contain both components
        self.assertIn("KPIBoxComponent", html_result)
        self.assertIn("LineChartComponent", html_result)


def run_tests():
    """Run all tests and display results."""
    print("🧪 Running Dashboard System Tests")
    print("=" * 50)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(unittest.TestLoader().loadTestsFromModule(sys.modules[__name__]))
    
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed.")
        
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1) 