#!/usr/bin/env python3
"""
RetailAI Platform - Comprehensive API Integration Tests
Tests all microservices endpoints for functionality, performance, and reliability
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import pytest
import requests
from datetime import datetime, timedelta
import concurrent.futures
import statistics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None

@dataclass
class ServiceConfig:
    """Service configuration."""
    name: str
    base_url: str
    port: int
    health_endpoint: str = "/health"

class APITestSuite:
    """Comprehensive API testing suite for RetailAI platform."""
    
    def __init__(self):
        self.services = {
            'ml_engine': ServiceConfig('ML Engine', 'http://localhost', 8001),
            'external_data': ServiceConfig('External Data', 'http://localhost', 8002),
            'alert_engine': ServiceConfig('Alert Engine', 'http://localhost', 8003),
            'auth_rbac': ServiceConfig('Authentication & RBAC', 'http://localhost', 8004),
            'dashboard': ServiceConfig('Dashboard', 'http://localhost', 8005),
            'reporting': ServiceConfig('Reporting', 'http://localhost', 8006),
            'monitoring': ServiceConfig('Performance Monitoring', 'http://localhost', 8007)
        }
        
        self.auth_token = None
        self.test_results = []
        self.performance_metrics = {}
        
    def get_service_url(self, service_name: str) -> str:
        """Get full service URL."""
        service = self.services[service_name]
        return f"{service.base_url}:{service.port}"
    
    async def authenticate(self) -> bool:
        """Authenticate and get JWT token."""
        
        logger.info("🔐 Authenticating with RBAC service...")
        
        auth_url = f"{self.get_service_url('auth_rbac')}/api/auth/login"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(auth_url, json={
                    "username": "admin",
                    "password": "admin123"
                }) as response:
                    
                    if response.status == 200:
                        data = await response.json()
                        self.auth_token = data.get('session_id')
                        logger.info("✅ Authentication successful")
                        return True
                    else:
                        logger.error(f"❌ Authentication failed: {response.status}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            return False
    
    async def make_request(self, method: str, url: str, **kwargs) -> TestResult:
        """Make HTTP request and record metrics."""
        
        start_time = time.time()
        
        headers = kwargs.get('headers', {})
        if self.auth_token and 'Authorization' not in headers:
            headers['Authorization'] = f'Bearer {self.auth_token}'
        kwargs['headers'] = headers
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, **kwargs) as response:
                    response_time_ms = (time.time() - start_time) * 1000
                    
                    try:
                        response_data = await response.json()
                    except:
                        response_data = await response.text()
                    
                    return TestResult(
                        test_name=kwargs.get('test_name', 'Unknown'),
                        endpoint=url,
                        method=method.upper(),
                        status_code=response.status,
                        response_time_ms=response_time_ms,
                        success=200 <= response.status < 300,
                        response_data=response_data if isinstance(response_data, dict) else None
                    )
                    
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return TestResult(
                test_name=kwargs.get('test_name', 'Unknown'),
                endpoint=url,
                method=method.upper(),
                status_code=0,
                response_time_ms=response_time_ms,
                success=False,
                error_message=str(e)
            )
    
    async def test_service_health(self) -> List[TestResult]:
        """Test health endpoints for all services."""
        
        logger.info("🏥 Testing service health checks...")
        
        health_tests = []
        
        for service_name, config in self.services.items():
            health_url = f"{self.get_service_url(service_name)}{config.health_endpoint}"
            
            result = await self.make_request(
                'GET', health_url,
                test_name=f"{config.name} Health Check"
            )
            
            health_tests.append(result)
            
            if result.success:
                logger.info(f"✅ {config.name} is healthy")
            else:
                logger.error(f"❌ {config.name} health check failed: {result.error_message}")
        
        return health_tests
    
    async def test_authentication_api(self) -> List[TestResult]:
        """Test Authentication & RBAC API endpoints."""
        
        logger.info("🔐 Testing Authentication & RBAC API...")
        
        base_url = self.get_service_url('auth_rbac')
        auth_tests = []
        
        # Test login
        result = await self.make_request(
            'POST', f"{base_url}/api/auth/login",
            json={"username": "admin", "password": "admin123"},
            test_name="User Login"
        )
        auth_tests.append(result)
        
        # Test session info
        result = await self.make_request(
            'GET', f"{base_url}/api/auth/session",
            test_name="Get Session Info"
        )
        auth_tests.append(result)
        
        # Test get users (admin only)
        result = await self.make_request(
            'GET', f"{base_url}/api/auth/users",
            test_name="Get All Users"
        )
        auth_tests.append(result)
        
        # Test get roles
        result = await self.make_request(
            'GET', f"{base_url}/api/auth/roles",
            test_name="Get Available Roles"
        )
        auth_tests.append(result)
        
        # Test permission check
        result = await self.make_request(
            'GET', f"{base_url}/api/auth/check-permission/read_sales_data",
            test_name="Check Permission"
        )
        auth_tests.append(result)
        
        return auth_tests
    
    async def test_ml_engine_api(self) -> List[TestResult]:
        """Test ML Engine API endpoints."""
        
        logger.info("🧠 Testing ML Engine API...")
        
        base_url = self.get_service_url('ml_engine')
        ml_tests = []
        
        # Test get models
        result = await self.make_request(
            'GET', f"{base_url}/api/ml/models",
            test_name="Get ML Models"
        )
        ml_tests.append(result)
        
        # Test forecast generation
        result = await self.make_request(
            'POST', f"{base_url}/api/ml/forecast",
            json={
                "product_id": "PROD_001",
                "store_id": "STORE_001", 
                "forecast_days": 7,
                "model_type": "arima"
            },
            test_name="Generate Forecast"
        )
        ml_tests.append(result)
        
        # Test inventory optimization
        result = await self.make_request(
            'POST', f"{base_url}/api/ml/optimize-inventory",
            json={
                "product_id": "PROD_001",
                "store_id": "STORE_001",
                "current_stock": 100,
                "lead_time_days": 7
            },
            test_name="Optimize Inventory"
        )
        ml_tests.append(result)
        
        # Test model performance
        result = await self.make_request(
            'GET', f"{base_url}/api/ml/performance/arima_forecaster",
            test_name="Get Model Performance"
        )
        ml_tests.append(result)
        
        return ml_tests
    
    async def test_dashboard_api(self) -> List[TestResult]:
        """Test Dashboard API endpoints."""
        
        logger.info("📊 Testing Dashboard API...")
        
        base_url = self.get_service_url('dashboard')
        dashboard_tests = []
        
        # Test get KPIs
        result = await self.make_request(
            'GET', f"{base_url}/api/dashboard/kpis",
            test_name="Get Real-time KPIs"
        )
        dashboard_tests.append(result)
        
        # Test inventory insights
        result = await self.make_request(
            'GET', f"{base_url}/api/dashboard/inventory",
            test_name="Get Inventory Insights"
        )
        dashboard_tests.append(result)
        
        # Test sales insights
        result = await self.make_request(
            'GET', f"{base_url}/api/dashboard/sales",
            test_name="Get Sales Insights"
        )
        dashboard_tests.append(result)
        
        # Test alert summary
        result = await self.make_request(
            'GET', f"{base_url}/api/dashboard/alerts",
            test_name="Get Alert Summary"
        )
        dashboard_tests.append(result)
        
        # Test executive summary
        result = await self.make_request(
            'GET', f"{base_url}/api/dashboard/executive-summary",
            test_name="Get Executive Summary"
        )
        dashboard_tests.append(result)
        
        return dashboard_tests
    
    async def test_alert_engine_api(self) -> List[TestResult]:
        """Test Alert Engine API endpoints."""
        
        logger.info("⚠️ Testing Alert Engine API...")
        
        base_url = self.get_service_url('alert_engine')
        alert_tests = []
        
        # Test get active alerts
        result = await self.make_request(
            'GET', f"{base_url}/api/alerts/active",
            test_name="Get Active Alerts"
        )
        alert_tests.append(result)
        
        # Test create alert rule
        result = await self.make_request(
            'POST', f"{base_url}/api/alerts/rules",
            json={
                "name": "Test Alert Rule",
                "conditions": {
                    "metric": "stock_level",
                    "operator": "less_than",
                    "threshold": 10
                },
                "severity": "high",
                "notification_channels": ["email"]
            },
            test_name="Create Alert Rule"
        )
        alert_tests.append(result)
        
        # Test get alert rules
        result = await self.make_request(
            'GET', f"{base_url}/api/alerts/rules",
            test_name="Get Alert Rules"
        )
        alert_tests.append(result)
        
        # Test alert analytics
        result = await self.make_request(
            'GET', f"{base_url}/api/alerts/analytics",
            test_name="Get Alert Analytics"
        )
        alert_tests.append(result)
        
        return alert_tests
    
    async def test_external_data_api(self) -> List[TestResult]:
        """Test External Data API endpoints."""
        
        logger.info("🌤️ Testing External Data API...")
        
        base_url = self.get_service_url('external_data')
        external_tests = []
        
        # Test weather data
        result = await self.make_request(
            'GET', f"{base_url}/api/external/weather",
            params={"city": "New York", "days": 7},
            test_name="Get Weather Data"
        )
        external_tests.append(result)
        
        # Test local events
        result = await self.make_request(
            'GET', f"{base_url}/api/external/events",
            params={"city": "New York", "date": "2024-01-15"},
            test_name="Get Local Events"
        )
        external_tests.append(result)
        
        # Test demographics
        result = await self.make_request(
            'GET', f"{base_url}/api/external/demographics",
            params={"store_id": "STORE_001"},
            test_name="Get Demographics"
        )
        external_tests.append(result)
        
        return external_tests
    
    async def test_reporting_api(self) -> List[TestResult]:
        """Test Reporting API endpoints."""
        
        logger.info("📊 Testing Reporting API...")
        
        base_url = self.get_service_url('reporting')
        reporting_tests = []
        
        # Test generate report
        result = await self.make_request(
            'POST', f"{base_url}/api/reports/generate",
            json={
                "report_type": "daily_summary",
                "format": "json"
            },
            test_name="Generate Report"
        )
        reporting_tests.append(result)
        
        # Test get report executions
        result = await self.make_request(
            'GET', f"{base_url}/api/reports/executions",
            test_name="Get Report Executions"
        )
        reporting_tests.append(result)
        
        # Test create schedule
        result = await self.make_request(
            'POST', f"{base_url}/api/reports/schedules",
            json={
                "report_type": "weekly_business_review",
                "frequency": "weekly",
                "recipients": ["test@retailai.com"],
                "format": "html"
            },
            test_name="Create Report Schedule"
        )
        reporting_tests.append(result)
        
        return reporting_tests
    
    async def test_monitoring_api(self) -> List[TestResult]:
        """Test Performance Monitoring API endpoints."""
        
        logger.info("🔍 Testing Performance Monitoring API...")
        
        base_url = self.get_service_url('monitoring')
        monitoring_tests = []
        
        # Test get current metrics
        result = await self.make_request(
            'GET', f"{base_url}/api/monitoring/metrics/current",
            test_name="Get Current Metrics"
        )
        monitoring_tests.append(result)
        
        # Test record custom metric
        result = await self.make_request(
            'POST', f"{base_url}/api/monitoring/metrics/custom",
            json={
                "name": "test_metric",
                "value": 42.5,
                "unit": "items",
                "metric_type": "gauge"
            },
            test_name="Record Custom Metric"
        )
        monitoring_tests.append(result)
        
        # Test get performance summary
        result = await self.make_request(
            'GET', f"{base_url}/api/monitoring/metrics/summary",
            params={"hours": 1},
            test_name="Get Performance Summary"
        )
        monitoring_tests.append(result)
        
        # Test get active alerts
        result = await self.make_request(
            'GET', f"{base_url}/api/monitoring/alerts/active",
            test_name="Get Performance Alerts"
        )
        monitoring_tests.append(result)
        
        return monitoring_tests
    
    async def test_performance_load(self, service_name: str, endpoint: str, 
                                  concurrent_requests: int = 50) -> Dict[str, Any]:
        """Run performance/load tests on specific endpoint."""
        
        logger.info(f"🚀 Running load test: {concurrent_requests} concurrent requests to {endpoint}")
        
        url = f"{self.get_service_url(service_name)}{endpoint}"
        
        async def make_load_request():
            return await self.make_request('GET', url, test_name=f"Load Test - {endpoint}")
        
        # Run concurrent requests
        start_time = time.time()
        
        tasks = [make_load_request() for _ in range(concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, TestResult) and r.success]
        failed_requests = [r for r in results if not isinstance(r, TestResult) or not r.success]
        
        response_times = [r.response_time_ms for r in successful_requests]
        
        return {
            "endpoint": endpoint,
            "concurrent_requests": concurrent_requests,
            "total_time_seconds": total_time,
            "requests_per_second": concurrent_requests / total_time,
            "successful_requests": len(successful_requests),
            "failed_requests": len(failed_requests),
            "success_rate": len(successful_requests) / concurrent_requests * 100,
            "response_times": {
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0,
                "avg_ms": statistics.mean(response_times) if response_times else 0,
                "p95_ms": statistics.quantiles(response_times, n=20)[18] if len(response_times) > 20 else 0,
                "p99_ms": statistics.quantiles(response_times, n=100)[98] if len(response_times) > 100 else 0
            }
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run comprehensive test suite."""
        
        logger.info("🧪 Starting comprehensive API test suite...")
        
        start_time = time.time()
        
        # Authenticate first
        if not await self.authenticate():
            return {"error": "Authentication failed", "tests": []}
        
        # Run all test categories
        test_categories = [
            ("Health Checks", self.test_service_health()),
            ("Authentication API", self.test_authentication_api()),
            ("ML Engine API", self.test_ml_engine_api()),
            ("Dashboard API", self.test_dashboard_api()),
            ("Alert Engine API", self.test_alert_engine_api()),
            ("External Data API", self.test_external_data_api()),
            ("Reporting API", self.test_reporting_api()),
            ("Monitoring API", self.test_monitoring_api())
        ]
        
        all_results = []
        
        for category_name, test_coroutine in test_categories:
            logger.info(f"📋 Running {category_name} tests...")
            
            try:
                category_results = await test_coroutine
                all_results.extend(category_results)
                
                successful = sum(1 for r in category_results if r.success)
                total = len(category_results)
                logger.info(f"✅ {category_name}: {successful}/{total} tests passed")
                
            except Exception as e:
                logger.error(f"❌ {category_name} tests failed: {e}")
        
        # Run performance tests on key endpoints
        logger.info("🚀 Running performance tests...")
        
        performance_tests = [
            ("dashboard", "/api/dashboard/kpis"),
            ("ml_engine", "/api/ml/models"),
            ("monitoring", "/api/monitoring/metrics/current")
        ]
        
        performance_results = []
        
        for service, endpoint in performance_tests:
            try:
                perf_result = await self.test_performance_load(service, endpoint, 20)
                performance_results.append(perf_result)
                
                logger.info(f"🚀 {endpoint}: {perf_result['requests_per_second']:.1f} RPS, "
                          f"{perf_result['success_rate']:.1f}% success rate")
                          
            except Exception as e:
                logger.error(f"❌ Performance test failed for {endpoint}: {e}")
        
        total_time = time.time() - start_time
        
        # Compile results
        successful_tests = sum(1 for r in all_results if r.success)
        total_tests = len(all_results)
        
        summary = {
            "test_suite_duration_seconds": total_time,
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "failed_tests": total_tests - successful_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "test_results": [
                {
                    "test_name": r.test_name,
                    "endpoint": r.endpoint,
                    "method": r.method,
                    "status_code": r.status_code,
                    "response_time_ms": r.response_time_ms,
                    "success": r.success,
                    "error_message": r.error_message
                }
                for r in all_results
            ],
            "performance_results": performance_results,
            "services_tested": list(self.services.keys()),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"🧪 Test suite completed: {successful_tests}/{total_tests} tests passed "
                   f"({summary['success_rate']:.1f}%) in {total_time:.1f} seconds")
        
        return summary
    
    def generate_test_report(self, results: Dict[str, Any]) -> str:
        """Generate HTML test report."""
        
        html_template = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>RetailAI API Test Report</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                .header { background: #667eea; color: white; padding: 20px; border-radius: 8px; }
                .summary { display: flex; justify-content: space-around; margin: 20px 0; }
                .metric { text-align: center; padding: 15px; background: #f8f9fa; border-radius: 5px; }
                .metric-value { font-size: 2em; font-weight: bold; }
                .success { color: #28a745; }
                .failure { color: #dc3545; }
                .warning { color: #ffc107; }
                table { width: 100%; border-collapse: collapse; margin: 20px 0; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background: #f8f9fa; }
                .test-success { background: #d4edda; }
                .test-failure { background: #f8d7da; }
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🧪 RetailAI API Test Report</h1>
                <p>Comprehensive API integration and performance testing</p>
                <p>Generated: {timestamp}</p>
            </div>
            
            <div class="summary">
                <div class="metric">
                    <div class="metric-value success">{successful_tests}</div>
                    <div>Passed</div>
                </div>
                <div class="metric">
                    <div class="metric-value failure">{failed_tests}</div>
                    <div>Failed</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{success_rate:.1f}%</div>
                    <div>Success Rate</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{duration:.1f}s</div>
                    <div>Duration</div>
                </div>
            </div>
            
            <h2>📋 Test Results</h2>
            <table>
                <tr>
                    <th>Test Name</th>
                    <th>Endpoint</th>
                    <th>Method</th>
                    <th>Status</th>
                    <th>Response Time</th>
                    <th>Result</th>
                </tr>
                {test_rows}
            </table>
            
            <h2>🚀 Performance Results</h2>
            <table>
                <tr>
                    <th>Endpoint</th>
                    <th>Requests/sec</th>
                    <th>Success Rate</th>
                    <th>Avg Response Time</th>
                    <th>P95 Response Time</th>
                </tr>
                {performance_rows}
            </table>
            
        </body>
        </html>
        """
        
        # Generate test result rows
        test_rows = ""
        for test in results['test_results']:
            row_class = "test-success" if test['success'] else "test-failure"
            status_text = "✅ PASS" if test['success'] else f"❌ FAIL ({test.get('status_code', 'N/A')})"
            
            test_rows += f"""
                <tr class="{row_class}">
                    <td>{test['test_name']}</td>
                    <td>{test['endpoint']}</td>
                    <td>{test['method']}</td>
                    <td>{test.get('status_code', 'N/A')}</td>
                    <td>{test['response_time_ms']:.1f}ms</td>
                    <td>{status_text}</td>
                </tr>
            """
        
        # Generate performance result rows
        performance_rows = ""
        for perf in results['performance_results']:
            performance_rows += f"""
                <tr>
                    <td>{perf['endpoint']}</td>
                    <td>{perf['requests_per_second']:.1f}</td>
                    <td>{perf['success_rate']:.1f}%</td>
                    <td>{perf['response_times']['avg_ms']:.1f}ms</td>
                    <td>{perf['response_times']['p95_ms']:.1f}ms</td>
                </tr>
            """
        
        return html_template.format(
            timestamp=results['timestamp'],
            successful_tests=results['successful_tests'],
            failed_tests=results['failed_tests'],
            success_rate=results['success_rate'],
            duration=results['test_suite_duration_seconds'],
            test_rows=test_rows,
            performance_rows=performance_rows
        )

# Main execution
async def main():
    """Run the comprehensive API test suite."""
    
    test_suite = APITestSuite()
    
    # Run all tests
    results = await test_suite.run_all_tests()
    
    # Save results to JSON
    with open('api_test_results.json', 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    # Generate HTML report
    html_report = test_suite.generate_test_report(results)
    with open('api_test_report.html', 'w') as f:
        f.write(html_report)
    
    print("\n" + "="*80)
    print("🧪 API TEST SUITE COMPLETE")
    print("="*80)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Successful: {results['successful_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    print(f"Duration: {results['test_suite_duration_seconds']:.1f} seconds")
    print("\n📊 Reports generated:")
    print("  - api_test_results.json (detailed results)")
    print("  - api_test_report.html (visual report)")
    print("="*80)

# pytest integration
class TestRetailAIAPIs:
    """Pytest test class for RetailAI APIs."""
    
    @classmethod
    def setup_class(cls):
        """Setup test class."""
        cls.test_suite = APITestSuite()
        
    @pytest.mark.asyncio
    async def test_health_checks(self):
        """Test all service health endpoints."""
        await self.test_suite.authenticate()
        results = await self.test_suite.test_service_health()
        assert all(r.success for r in results), "Some health checks failed"
    
    @pytest.mark.asyncio
    async def test_authentication_endpoints(self):
        """Test authentication endpoints."""
        await self.test_suite.authenticate()
        results = await self.test_suite.test_authentication_api()
        success_rate = sum(1 for r in results if r.success) / len(results)
        assert success_rate >= 0.8, f"Authentication tests success rate too low: {success_rate}"
    
    @pytest.mark.asyncio 
    async def test_ml_engine_endpoints(self):
        """Test ML Engine endpoints."""
        await self.test_suite.authenticate()
        results = await self.test_suite.test_ml_engine_api()
        success_rate = sum(1 for r in results if r.success) / len(results)
        assert success_rate >= 0.7, f"ML Engine tests success rate too low: {success_rate}"
    
    @pytest.mark.asyncio
    async def test_dashboard_endpoints(self):
        """Test Dashboard endpoints."""
        await self.test_suite.authenticate()
        results = await self.test_suite.test_dashboard_api()
        success_rate = sum(1 for r in results if r.success) / len(results)
        assert success_rate >= 0.8, f"Dashboard tests success rate too low: {success_rate}"
    
    @pytest.mark.asyncio
    async def test_performance_load(self):
        """Test performance under load."""
        await self.test_suite.authenticate()
        
        # Test dashboard KPI endpoint performance
        perf_result = await self.test_suite.test_performance_load(
            'dashboard', '/api/dashboard/kpis', 25
        )
        
        assert perf_result['success_rate'] >= 95, "Load test success rate too low"
        assert perf_result['response_times']['avg_ms'] < 1000, "Average response time too high"

if __name__ == "__main__":
    # Run the test suite
    asyncio.run(main())