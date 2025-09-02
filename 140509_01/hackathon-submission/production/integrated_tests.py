#!/usr/bin/env python3
"""
Production Integration Tests - Integrated into 140509_01 project
Comprehensive testing suite for production services
"""

import requests
import json
import time
import os
from datetime import datetime
from typing import Dict, List

class ProductionIntegrationTests:
    def __init__(self):
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.join(self.base_path, "..")
        self.test_results = []
        self.session_tokens = {}
        
        # Service endpoints
        self.services = {
            "auth": "http://localhost:8004",
            "ml": "http://localhost:8001",
            "dashboard": "http://localhost:8005"
        }
        
        # Test credentials
        self.credentials = {
            "admin": {"username": "admin", "password": "admin123"},
            "manager": {"username": "manager", "password": "manager123"},
            "analyst": {"username": "analyst", "password": "analyst123"},
            "demo": {"username": "demo", "password": "demo123"}
        }
    
    def log_result(self, test_name: str, status: str, details: str = "", duration: float = 0):
        """Log test result."""
        result = {
            "test_name": test_name,
            "status": status,
            "details": details,
            "duration": duration,
            "timestamp": datetime.now().isoformat(),
            "project": "140509_01"
        }
        self.test_results.append(result)
        
        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status} ({duration:.2f}s)")
        if details and status == "FAIL":
            print(f"   → {details}")
    
    def test_project_structure(self):
        """Test that production files are in correct project structure."""
        print("\n📁 Testing Project Structure Integration...")
        
        required_files = [
            "production/ml_engine_production.py",
            "production/auth_service_production.py", 
            "production/integrated_tests.py",
            "docker-compose.production.yml",
            ".env.production",
            "PRODUCTION_READY_GUIDE.md"
        ]
        
        for file_path in required_files:
            start_time = time.time()
            full_path = os.path.join(self.project_root, file_path)
            duration = time.time() - start_time
            
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                self.log_result(
                    f"Project File - {file_path}",
                    "PASS",
                    f"File exists ({file_size} bytes)",
                    duration
                )
            else:
                self.log_result(
                    f"Project File - {file_path}",
                    "FAIL", 
                    "File missing from project structure",
                    duration
                )
    
    def test_service_health(self):
        """Test production service health endpoints."""
        print("\n🏥 Testing Production Service Health...")
        
        for service_name, base_url in self.services.items():
            start_time = time.time()
            
            try:
                response = requests.get(f"{base_url}/health", timeout=5)
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    health_data = response.json()
                    project = health_data.get("project", "unknown")
                    version = health_data.get("version", "unknown")
                    
                    if project == "140509_01":
                        self.log_result(
                            f"Health Check - {service_name.upper()}",
                            "PASS",
                            f"Project: {project}, Version: {version}",
                            duration
                        )
                    else:
                        self.log_result(
                            f"Health Check - {service_name.upper()}",
                            "FAIL",
                            f"Wrong project context: {project}",
                            duration
                        )
                else:
                    self.log_result(
                        f"Health Check - {service_name.upper()}",
                        "FAIL",
                        f"HTTP {response.status_code}",
                        duration
                    )
            
            except Exception as e:
                duration = time.time() - start_time
                self.log_result(
                    f"Health Check - {service_name.upper()}",
                    "FAIL",
                    str(e),
                    duration
                )
    
    def test_authentication_integration(self):
        """Test production authentication with project integration."""
        print("\n🔐 Testing Production Authentication Integration...")
        
        for role, creds in self.credentials.items():
            start_time = time.time()
            
            try:
                response = requests.post(
                    f"{self.services['auth']}/api/auth/login",
                    json=creds,
                    timeout=10
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    login_data = response.json()
                    
                    if login_data.get("success") and login_data.get("project") == "140509_01":
                        token = login_data.get("token")
                        self.session_tokens[role] = token
                        
                        self.log_result(
                            f"Auth Integration - {role.upper()}",
                            "PASS",
                            f"Project: {login_data.get('project')}, Environment: {login_data.get('environment')}",
                            duration
                        )
                    else:
                        self.log_result(
                            f"Auth Integration - {role.upper()}",
                            "FAIL",
                            f"Missing project context or login failed",
                            duration
                        )
                else:
                    self.log_result(
                        f"Auth Integration - {role.upper()}",
                        "FAIL",
                        f"HTTP {response.status_code}",
                        duration
                    )
            
            except Exception as e:
                duration = time.time() - start_time
                self.log_result(
                    f"Auth Integration - {role.upper()}",
                    "FAIL",
                    str(e),
                    duration
                )
    
    def test_ml_engine_integration(self):
        """Test ML engine integration with project context."""
        print("\n🧠 Testing ML Engine Production Integration...")
        
        # Test KPIs endpoint
        start_time = time.time()
        try:
            response = requests.get(f"{self.services['ml']}/api/kpis", timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                kpis_data = response.json()
                
                required_sections = ["revenue", "inventory", "operational", "ml_performance"]
                if all(section in kpis_data for section in required_sections):
                    revenue = kpis_data["revenue"].get("total_revenue", 0)
                    accuracy = kpis_data["ml_performance"].get("prediction_accuracy", 0)
                    
                    self.log_result(
                        "ML KPIs Integration",
                        "PASS",
                        f"Revenue: ${revenue:,.2f}, ML Accuracy: {accuracy}%",
                        duration
                    )
                else:
                    self.log_result(
                        "ML KPIs Integration", 
                        "FAIL",
                        "Missing required KPI sections",
                        duration
                    )
            else:
                self.log_result(
                    "ML KPIs Integration",
                    "FAIL", 
                    f"HTTP {response.status_code}",
                    duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            self.log_result("ML KPIs Integration", "FAIL", str(e), duration)
        
        # Test forecasting endpoint
        if "admin" in self.session_tokens:
            start_time = time.time()
            try:
                forecast_request = {
                    "store_id": "STORE_001",
                    "product_id": "PROD_158",
                    "days": 14,
                    "model_type": "production"
                }
                
                headers = {"Authorization": f"Bearer {self.session_tokens['admin']}"}
                response = requests.post(
                    f"{self.services['ml']}/api/forecast",
                    json=forecast_request,
                    headers=headers,
                    timeout=15
                )
                duration = time.time() - start_time
                
                if response.status_code == 200:
                    forecast_data = response.json()
                    
                    if forecast_data.get("success") and "forecast" in forecast_data:
                        predictions = forecast_data["forecast"].get("predictions", [])
                        total_demand = forecast_data["forecast"]["summary"].get("total_predicted_demand", 0)
                        
                        self.log_result(
                            "ML Forecasting Integration",
                            "PASS",
                            f"{len(predictions)} predictions, Total demand: {total_demand}",
                            duration
                        )
                    else:
                        self.log_result(
                            "ML Forecasting Integration",
                            "FAIL",
                            "Invalid forecast response structure",
                            duration
                        )
                else:
                    self.log_result(
                        "ML Forecasting Integration",
                        "FAIL",
                        f"HTTP {response.status_code}",
                        duration
                    )
            
            except Exception as e:
                duration = time.time() - start_time
                self.log_result("ML Forecasting Integration", "FAIL", str(e), duration)
    
    def test_business_workflow_integration(self):
        """Test integrated business workflows."""
        print("\n🏢 Testing Business Workflow Integration...")
        
        if "admin" not in self.session_tokens:
            self.log_result("Business Workflow", "SKIP", "No admin authentication available")
            return
        
        headers = {"Authorization": f"Bearer {self.session_tokens['admin']}"}
        
        # Test stores endpoint
        start_time = time.time()
        try:
            response = requests.get(f"{self.services['ml']}/api/stores", headers=headers, timeout=10)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                stores_data = response.json()
                
                if isinstance(stores_data, list) and len(stores_data) > 0:
                    total_revenue = sum(store.get('total_revenue', 0) for store in stores_data)
                    avg_performance = sum(store.get('performance_score', 0) for store in stores_data) / len(stores_data)
                    
                    self.log_result(
                        "Store Management Integration",
                        "PASS",
                        f"{len(stores_data)} stores, ${total_revenue:,.2f} revenue, {avg_performance:.1f}% avg performance",
                        duration
                    )
                else:
                    self.log_result(
                        "Store Management Integration",
                        "FAIL",
                        "No store data available",
                        duration
                    )
            else:
                self.log_result(
                    "Store Management Integration",
                    "FAIL",
                    f"HTTP {response.status_code}",
                    duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            self.log_result("Store Management Integration", "FAIL", str(e), duration)
        
        # Test production analysis
        start_time = time.time()
        try:
            response = requests.get(f"{self.services['ml']}/api/demo/run-analysis", headers=headers, timeout=20)
            duration = time.time() - start_time
            
            if response.status_code == 200:
                analysis_data = response.json()
                
                successful = analysis_data.get("successful_analyses", 0)
                total = analysis_data.get("total_analyzed", 0)
                profit_opportunity = analysis_data.get("summary", {}).get("estimated_profit_opportunity", 0)
                
                self.log_result(
                    "Production Analysis Integration",
                    "PASS",
                    f"{successful}/{total} analyses, ${profit_opportunity:,.2f} profit opportunity",
                    duration
                )
            else:
                self.log_result(
                    "Production Analysis Integration",
                    "FAIL",
                    f"HTTP {response.status_code}",
                    duration
                )
        
        except Exception as e:
            duration = time.time() - start_time
            self.log_result("Production Analysis Integration", "FAIL", str(e), duration)
    
    def generate_production_report(self):
        """Generate production integration test report."""
        print("\n📊 Production Integration Test Report")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed = len([r for r in self.test_results if r["status"] == "PASS"])
        failed = len([r for r in self.test_results if r["status"] == "FAIL"])
        skipped = len([r for r in self.test_results if r["status"] == "SKIP"])
        
        print(f"Project: 140509_01")
        print(f"Test Environment: Production Integration")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⏭️  Skipped: {skipped}")
        
        success_rate = (passed / total_tests * 100) if total_tests > 0 else 0
        print(f"\n🎯 Success Rate: {success_rate:.1f}%")
        
        avg_duration = sum(r["duration"] for r in self.test_results) / total_tests if total_tests > 0 else 0
        print(f"⏱️  Average Test Duration: {avg_duration:.2f}s")
        
        # Production readiness assessment
        print(f"\n🚀 Production Integration Assessment:")
        
        if success_rate >= 95 and failed == 0:
            print("✅ FULLY INTEGRATED - All systems properly integrated into 140509_01")
        elif success_rate >= 85:
            print("⚠️  MOSTLY INTEGRATED - Minor integration issues detected")
        elif success_rate >= 70:
            print("🔧 PARTIAL INTEGRATION - Significant work needed")
        else:
            print("❌ INTEGRATION FAILED - Major structural issues")
        
        # Save report to project
        report_data = {
            "project": "140509_01",
            "test_type": "production_integration",
            "summary": {
                "total_tests": total_tests,
                "passed": passed,
                "failed": failed,
                "skipped": skipped,
                "success_rate": success_rate,
                "avg_duration": avg_duration
            },
            "test_results": self.test_results,
            "generated_at": datetime.now().isoformat()
        }
        
        report_path = os.path.join(self.project_root, "logs", "production_integration_report.json")
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📁 Report saved: logs/production_integration_report.json")
        
        return report_data
    
    def run_all_tests(self):
        """Run complete production integration test suite."""
        print("🚀 Production Integration Tests for 140509_01")
        print("=" * 60)
        
        start_time = time.time()
        
        # Run all test categories
        self.test_project_structure()
        self.test_service_health() 
        self.test_authentication_integration()
        self.test_ml_engine_integration()
        self.test_business_workflow_integration()
        
        total_duration = time.time() - start_time
        print(f"\n🏁 Integration Tests Completed in {total_duration:.2f}s")
        
        return self.generate_production_report()

def main():
    """Main entry point for production integration tests."""
    test_suite = ProductionIntegrationTests()
    report = test_suite.run_all_tests()
    
    # Return appropriate exit code
    success_rate = report["summary"]["success_rate"]
    failed = report["summary"]["failed"]
    
    if success_rate >= 95 and failed == 0:
        exit(0)  # Fully integrated
    elif success_rate >= 85:
        exit(1)  # Minor issues
    else:
        exit(2)  # Major issues

if __name__ == "__main__":
    main()