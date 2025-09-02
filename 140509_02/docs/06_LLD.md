# Low Level Design (LLD)
## Manufacturing Quality Control AI Vision System

*Building upon PRD, FRD, NFRD, Architecture Diagram, and HLD for detailed implementation specifications and code-level design*

## ETVX Framework

### ENTRY CRITERIA
- ✅ HLD completed with detailed component specifications
- ✅ Computer vision pipeline and manufacturing integration interfaces finalized
- ✅ Quality analytics algorithms and edge deployment patterns defined
- ✅ Development environment and coding standards established for manufacturing systems
- ✅ Code review and testing processes defined for safety-critical applications

### TASK
Transform high-level design into implementation-ready code specifications including computer vision class definitions, manufacturing protocol implementations, real-time processing algorithms, edge deployment configurations, and detailed implementation logic for all system components.

### VERIFICATION & VALIDATION
**Verification Checklist:**
- [ ] All HLD components have corresponding code implementations
- [ ] Computer vision classes follow real-time processing requirements (<100ms)
- [ ] Manufacturing integration implements industrial protocols correctly
- [ ] Quality analytics algorithms match statistical process control standards
- [ ] Edge deployment code handles environmental constraints and fault tolerance
- [ ] Code follows manufacturing software safety standards (IEC 61508)

**Validation Criteria:**
- [ ] Implementation logic satisfies all functional requirements (FR-001 to FR-038)
- [ ] Code structure supports non-functional requirements (NFR-001 to NFR-051)
- [ ] Computer vision algorithms meet 99.5% accuracy benchmarks
- [ ] Manufacturing integration tested with actual PLC systems
- [ ] Security implementations follow industrial cybersecurity standards
- [ ] Code review completed by computer vision and manufacturing experts

### EXIT CRITERIA
- ✅ Complete code specifications for all system components
- ✅ Implementation-ready computer vision and manufacturing integration classes
- ✅ Detailed real-time processing algorithms with performance analysis
- ✅ Edge deployment and fault tolerance specifications completed
- ✅ Foundation established for pseudocode and actual implementation

---

### Reference to Previous Documents
This LLD provides implementation-ready code specifications based on **ALL** previous requirements:
- **PRD Success Metrics** → Code implementations targeting 99.5% accuracy, <100ms processing times
- **PRD Target Users** → User-specific interfaces for operators, quality managers, engineers
- **FRD Functional Requirements (FR-001 to FR-038)** → Direct code implementation of each requirement
- **NFRD Performance Requirements** → Optimized algorithms, GPU acceleration, real-time processing
- **NFRD Environmental Requirements** → Ruggedized code for manufacturing conditions
- **NFRD Security Requirements** → Industrial cybersecurity implementations, OT/IT segmentation
- **Architecture Diagram Technology Stack** → Specific framework implementations (PyTorch, TensorRT, OPC-UA)
- **HLD System Components** → Detailed class structures, method signatures, real-time data flows
- **HLD Computer Vision Pipeline** → CNN/ViT implementations with TensorRT optimization
- **HLD Manufacturing Integration** → PLC communication protocols and production line interfaces
- **HLD Quality Analytics** → Statistical process control algorithms and dashboard implementations

### 1. Computer Vision Implementation

#### 1.1 Image Processing and Preprocessing Classes
```python
import cv2
import numpy as np
import torch
import tensorrt as trt
from typing import Tuple, List, Optional

class IndustrialImagePreprocessor:
    """High-performance image preprocessing for manufacturing environment"""
    
    def __init__(self, target_size: Tuple[int, int] = (2048, 2048)):
        self.target_size = target_size
        self.noise_filter = cv2.createFastNlMeansDenoising()
        self.clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        
    def preprocess_image(self, image: np.ndarray) -> torch.Tensor:
        """
        Preprocess image for defect detection
        Target: <10ms processing time
        """
        # Noise reduction (2-3ms)
        denoised = cv2.fastNlMeansDenoising(image)
        
        # Contrast enhancement (1-2ms)
        enhanced = self.clahe.apply(denoised)
        
        # Geometric correction (2-3ms)
        corrected = self._correct_perspective(enhanced)
        
        # Normalization and tensor conversion (1-2ms)
        normalized = corrected.astype(np.float32) / 255.0
        tensor = torch.from_numpy(normalized).unsqueeze(0)
        
        return tensor
    
    def _correct_perspective(self, image: np.ndarray) -> np.ndarray:
        """Correct perspective distortion from camera angle"""
        # Implementation for perspective correction
        return image

class DefectDetectionModel:
    """TensorRT optimized defect detection model"""
    
    def __init__(self, model_path: str, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold
        self.engine = self._load_tensorrt_engine(model_path)
        self.context = self.engine.create_execution_context()
        
    def _load_tensorrt_engine(self, model_path: str):
        """Load optimized TensorRT engine"""
        with open(model_path, 'rb') as f:
            engine_data = f.read()
        
        runtime = trt.Runtime(trt.Logger(trt.Logger.WARNING))
        engine = runtime.deserialize_cuda_engine(engine_data)
        return engine
    
    def detect_defects(self, image_tensor: torch.Tensor) -> List[dict]:
        """
        Detect defects in image
        Target: <50ms inference time
        """
        # GPU memory allocation
        input_binding = self.engine.get_binding_index("input")
        output_binding = self.engine.get_binding_index("output")
        
        # Inference execution
        self.context.execute_v2([
            image_tensor.data_ptr(),
            self.output_buffer.data_ptr()
        ])
        
        # Post-process results
        detections = self._post_process_detections(self.output_buffer)
        
        return detections
    
    def _post_process_detections(self, raw_output: torch.Tensor) -> List[dict]:
        """Convert raw model output to structured detections"""
        detections = []
        
        for detection in raw_output:
            if detection.confidence > self.confidence_threshold:
                detections.append({
                    'bbox': detection.bbox.tolist(),
                    'class': detection.class_id,
                    'confidence': float(detection.confidence),
                    'severity': self._calculate_severity(detection)
                })
        
        return detections
```

#### 1.2 Real-time Processing Pipeline Implementation
```python
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import AsyncGenerator

@dataclass
class InspectionResult:
    product_id: str
    timestamp: float
    defects: List[dict]
    overall_quality: str  # 'PASS', 'FAIL', 'REVIEW'
    confidence_score: float
    processing_time_ms: float

class RealTimeVisionPipeline:
    """Real-time computer vision pipeline for manufacturing"""
    
    def __init__(self, camera_system, defect_model, plc_interface):
        self.camera = camera_system
        self.model = defect_model
        self.plc = plc_interface
        self.preprocessor = IndustrialImagePreprocessor()
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        # Performance monitoring
        self.processing_times = []
        self.accuracy_metrics = []
        
    async def process_inspection_stream(self) -> AsyncGenerator[InspectionResult, None]:
        """Main processing loop for continuous inspection"""
        
        while True:
            try:
                # Wait for inspection trigger from PLC
                trigger_signal = await self.plc.wait_for_inspection_trigger()
                
                if trigger_signal:
                    start_time = time.time()
                    
                    # Capture image (5-10ms)
                    image = await self.camera.capture_image()
                    
                    # Process in thread pool to avoid blocking
                    result = await asyncio.get_event_loop().run_in_executor(
                        self.executor, self._process_single_image, image, trigger_signal.product_id
                    )
                    
                    # Send result to PLC (1-2ms)
                    await self.plc.send_quality_decision(result)
                    
                    # Update performance metrics
                    processing_time = (time.time() - start_time) * 1000
                    self._update_performance_metrics(processing_time, result)
                    
                    yield result
                    
            except Exception as e:
                await self._handle_processing_error(e)
                
    def _process_single_image(self, image: np.ndarray, product_id: str) -> InspectionResult:
        """Process single image for defect detection"""
        start_time = time.time()
        
        # Preprocessing (5-10ms)
        processed_image = self.preprocessor.preprocess_image(image)
        
        # Defect detection (20-40ms)
        defects = self.model.detect_defects(processed_image)
        
        # Quality decision logic (1-2ms)
        overall_quality, confidence = self._make_quality_decision(defects)
        
        processing_time = (time.time() - start_time) * 1000
        
        return InspectionResult(
            product_id=product_id,
            timestamp=time.time(),
            defects=defects,
            overall_quality=overall_quality,
            confidence_score=confidence,
            processing_time_ms=processing_time
        )
    
    def _make_quality_decision(self, defects: List[dict]) -> Tuple[str, float]:
        """Make pass/fail decision based on detected defects"""
        if not defects:
            return "PASS", 1.0
            
        # Check for critical defects
        critical_defects = [d for d in defects if d['severity'] >= 3]
        if critical_defects:
            return "FAIL", min([d['confidence'] for d in critical_defects])
            
        # Check for major defects
        major_defects = [d for d in defects if d['severity'] == 2]
        if len(major_defects) > 2:  # More than 2 major defects = fail
            return "FAIL", min([d['confidence'] for d in major_defects])
            
        # Minor defects require review
        minor_defects = [d for d in defects if d['severity'] == 1]
        if minor_defects:
            return "REVIEW", min([d['confidence'] for d in minor_defects])
            
        return "PASS", min([d['confidence'] for d in defects])
```

### 2. Manufacturing Integration Implementation

#### 2.1 PLC Communication Interface
```python
import asyncio
from opcua import Client, ua
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class PLCTriggerSignal:
    product_id: str
    line_speed: float
    batch_number: str
    timestamp: float

class OPCUAClient:
    """OPC-UA client for PLC communication"""
    
    def __init__(self, endpoint_url: str, namespace_index: int = 2):
        self.endpoint_url = endpoint_url
        self.namespace_index = namespace_index
        self.client = None
        self.connected = False
        
    async def connect(self):
        """Establish connection to PLC"""
        try:
            self.client = Client(self.endpoint_url)
            await self.client.connect()
            self.connected = True
            
            # Set up subscription for inspection triggers
            await self._setup_subscriptions()
            
        except Exception as e:
            raise ConnectionError(f"Failed to connect to PLC: {e}")
    
    async def _setup_subscriptions(self):
        """Set up OPC-UA subscriptions for real-time data"""
        subscription = await self.client.create_subscription(100, self)
        
        # Subscribe to inspection trigger node
        trigger_node = self.client.get_node(f"ns={self.namespace_index};s=InspectionTrigger")
        await subscription.subscribe_data_change(trigger_node)
        
        # Subscribe to production data
        production_node = self.client.get_node(f"ns={self.namespace_index};s=ProductionData")
        await subscription.subscribe_data_change(production_node)
    
    async def wait_for_inspection_trigger(self) -> Optional[PLCTriggerSignal]:
        """Wait for inspection trigger from PLC"""
        # Implementation for waiting for trigger signal
        pass
    
    async def send_quality_decision(self, result: InspectionResult):
        """Send quality decision back to PLC"""
        try:
            # Write quality result to PLC
            quality_node = self.client.get_node(f"ns={self.namespace_index};s=QualityResult")
            await quality_node.write_value(result.overall_quality)
            
            # Write confidence score
            confidence_node = self.client.get_node(f"ns={self.namespace_index};s=ConfidenceScore")
            await confidence_node.write_value(result.confidence_score)
            
            # Write defect count
            defect_count_node = self.client.get_node(f"ns={self.namespace_index};s=DefectCount")
            await defect_count_node.write_value(len(result.defects))
            
        except Exception as e:
            raise RuntimeError(f"Failed to send quality decision to PLC: {e}")

class ProductionLineController:
    """High-level controller for production line integration"""
    
    def __init__(self, plc_client: OPCUAClient):
        self.plc = plc_client
        self.quality_buffer = asyncio.Queue(maxsize=1000)
        self.performance_monitor = PerformanceMonitor()
        
    async def start_quality_control_loop(self):
        """Main control loop for quality control system"""
        await self.plc.connect()
        
        # Start background tasks
        asyncio.create_task(self._monitor_system_health())
        asyncio.create_task(self._process_quality_buffer())
        
        # Main processing loop
        vision_pipeline = RealTimeVisionPipeline(
            camera_system=self.camera,
            defect_model=self.model,
            plc_interface=self.plc
        )
        
        async for result in vision_pipeline.process_inspection_stream():
            await self.quality_buffer.put(result)
            await self._update_quality_metrics(result)
    
    async def _monitor_system_health(self):
        """Monitor system health and performance"""
        while True:
            health_status = await self.performance_monitor.check_system_health()
            
            if health_status.critical_issues:
                await self._handle_critical_issues(health_status.critical_issues)
            
            await asyncio.sleep(1)  # Check every second
```

### 3. Quality Analytics Implementation

#### 3.1 Statistical Process Control Engine
```python
import numpy as np
import pandas as pd
from scipy import stats
from typing import List, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ControlLimits:
    ucl: float  # Upper Control Limit
    lcl: float  # Lower Control Limit
    center_line: float
    
@dataclass
class SPCAlert:
    chart_type: str
    alert_type: str  # 'OUT_OF_CONTROL', 'TREND', 'SHIFT'
    timestamp: datetime
    value: float
    description: str

class StatisticalProcessControl:
    """Statistical Process Control implementation for quality analytics"""
    
    def __init__(self, sample_size: int = 25):
        self.sample_size = sample_size
        self.x_bar_data = []
        self.r_data = []
        self.p_data = []
        
    def add_quality_sample(self, measurements: List[float]) -> List[SPCAlert]:
        """Add new quality measurements and check for control violations"""
        alerts = []
        
        # Calculate sample statistics
        x_bar = np.mean(measurements)
        r_value = np.max(measurements) - np.min(measurements)
        
        self.x_bar_data.append(x_bar)
        self.r_data.append(r_value)
        
        # Check X-bar chart
        x_bar_alerts = self._check_x_bar_control(x_bar)
        alerts.extend(x_bar_alerts)
        
        # Check R chart
        r_alerts = self._check_r_control(r_value)
        alerts.extend(r_alerts)
        
        return alerts
    
    def _check_x_bar_control(self, x_bar: float) -> List[SPCAlert]:
        """Check X-bar chart for out-of-control conditions"""
        alerts = []
        
        if len(self.x_bar_data) < self.sample_size:
            return alerts
            
        # Calculate control limits
        control_limits = self._calculate_x_bar_limits()
        
        # Rule 1: Point beyond control limits
        if x_bar > control_limits.ucl or x_bar < control_limits.lcl:
            alerts.append(SPCAlert(
                chart_type='X_BAR',
                alert_type='OUT_OF_CONTROL',
                timestamp=datetime.now(),
                value=x_bar,
                description=f'Point beyond control limits: {x_bar:.3f}'
            ))
        
        # Rule 2: 7 consecutive points on same side of center line
        recent_points = self.x_bar_data[-7:]
        if len(recent_points) == 7:
            if all(p > control_limits.center_line for p in recent_points) or \
               all(p < control_limits.center_line for p in recent_points):
                alerts.append(SPCAlert(
                    chart_type='X_BAR',
                    alert_type='SHIFT',
                    timestamp=datetime.now(),
                    value=x_bar,
                    description='7 consecutive points on same side of center line'
                ))
        
        # Rule 3: 7 consecutive increasing or decreasing points
        if len(recent_points) == 7:
            increasing = all(recent_points[i] < recent_points[i+1] for i in range(6))
            decreasing = all(recent_points[i] > recent_points[i+1] for i in range(6))
            
            if increasing or decreasing:
                alerts.append(SPCAlert(
                    chart_type='X_BAR',
                    alert_type='TREND',
                    timestamp=datetime.now(),
                    value=x_bar,
                    description='7 consecutive trending points'
                ))
        
        return alerts
    
    def _calculate_x_bar_limits(self) -> ControlLimits:
        """Calculate control limits for X-bar chart"""
        x_double_bar = np.mean(self.x_bar_data)
        r_bar = np.mean(self.r_data)
        
        # Constants for control chart calculations (n=5 assumed)
        A2 = 0.577  # Factor for X-bar chart limits
        
        ucl = x_double_bar + A2 * r_bar
        lcl = x_double_bar - A2 * r_bar
        
        return ControlLimits(ucl=ucl, lcl=lcl, center_line=x_double_bar)

class QualityMetricsCalculator:
    """Calculate quality metrics and KPIs"""
    
    def __init__(self):
        self.inspection_history = []
        
    def calculate_process_capability(self, measurements: List[float], 
                                   specification_limits: Tuple[float, float]) -> Dict[str, float]:
        """Calculate process capability indices (Cp, Cpk)"""
        lsl, usl = specification_limits
        
        mean = np.mean(measurements)
        std = np.std(measurements, ddof=1)
        
        # Process capability (Cp)
        cp = (usl - lsl) / (6 * std)
        
        # Process capability index (Cpk)
        cpu = (usl - mean) / (3 * std)
        cpl = (mean - lsl) / (3 * std)
        cpk = min(cpu, cpl)
        
        return {
            'cp': cp,
            'cpk': cpk,
            'cpu': cpu,
            'cpl': cpl,
            'mean': mean,
            'std': std
        }
    
    def calculate_defect_rates(self, time_window: timedelta = timedelta(hours=1)) -> Dict[str, float]:
        """Calculate defect rates for different time windows"""
        current_time = datetime.now()
        window_start = current_time - time_window
        
        # Filter inspections within time window
        recent_inspections = [
            inspection for inspection in self.inspection_history
            if inspection.timestamp >= window_start.timestamp()
        ]
        
        if not recent_inspections:
            return {'total_rate': 0.0, 'critical_rate': 0.0, 'major_rate': 0.0}
        
        total_inspections = len(recent_inspections)
        defective_inspections = len([i for i in recent_inspections if i.defects])
        critical_defects = len([i for i in recent_inspections 
                               if any(d['severity'] >= 3 for d in i.defects)])
        major_defects = len([i for i in recent_inspections 
                            if any(d['severity'] == 2 for d in i.defects)])
        
        return {
            'total_rate': defective_inspections / total_inspections,
            'critical_rate': critical_defects / total_inspections,
            'major_rate': major_defects / total_inspections
        }
```

### 4. Edge Computing and Deployment Implementation

#### 4.1 Resource Management and Optimization
```python
import psutil
import GPUtil
import threading
import time
from typing import Dict, Any

class EdgeResourceManager:
    """Manage computing resources on edge devices"""
    
    def __init__(self):
        self.cpu_threshold = 80.0  # CPU usage threshold
        self.memory_threshold = 85.0  # Memory usage threshold
        self.gpu_threshold = 90.0  # GPU usage threshold
        self.temperature_threshold = 75.0  # Temperature threshold (°C)
        
        self.monitoring_active = False
        self.performance_data = {
            'cpu_usage': [],
            'memory_usage': [],
            'gpu_usage': [],
            'temperature': []
        }
        
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        self.monitoring_active = True
        monitoring_thread = threading.Thread(target=self._monitor_resources)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
    def _monitor_resources(self):
        """Monitor system resources continuously"""
        while self.monitoring_active:
            try:
                # CPU monitoring
                cpu_percent = psutil.cpu_percent(interval=1)
                self.performance_data['cpu_usage'].append(cpu_percent)
                
                # Memory monitoring
                memory = psutil.virtual_memory()
                self.performance_data['memory_usage'].append(memory.percent)
                
                # GPU monitoring
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu_usage = gpus[0].load * 100
                    gpu_temp = gpus[0].temperature
                    self.performance_data['gpu_usage'].append(gpu_usage)
                    self.performance_data['temperature'].append(gpu_temp)
                    
                    # Check for thermal throttling
                    if gpu_temp > self.temperature_threshold:
                        self._handle_thermal_throttling()
                
                # Trim history to last 1000 samples
                for key in self.performance_data:
                    if len(self.performance_data[key]) > 1000:
                        self.performance_data[key] = self.performance_data[key][-1000:]
                        
            except Exception as e:
                print(f"Resource monitoring error: {e}")
                
            time.sleep(1)
    
    def _handle_thermal_throttling(self):
        """Handle thermal throttling by reducing processing load"""
        # Reduce inference frequency
        # Lower model precision
        # Increase cooling fan speed
        pass
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get current system health status"""
        if not self.performance_data['cpu_usage']:
            return {'status': 'UNKNOWN', 'details': 'No monitoring data available'}
            
        current_cpu = self.performance_data['cpu_usage'][-1]
        current_memory = self.performance_data['memory_usage'][-1]
        current_gpu = self.performance_data['gpu_usage'][-1] if self.performance_data['gpu_usage'] else 0
        current_temp = self.performance_data['temperature'][-1] if self.performance_data['temperature'] else 0
        
        status = 'HEALTHY'
        issues = []
        
        if current_cpu > self.cpu_threshold:
            status = 'WARNING'
            issues.append(f'High CPU usage: {current_cpu:.1f}%')
            
        if current_memory > self.memory_threshold:
            status = 'WARNING'
            issues.append(f'High memory usage: {current_memory:.1f}%')
            
        if current_gpu > self.gpu_threshold:
            status = 'WARNING'
            issues.append(f'High GPU usage: {current_gpu:.1f}%')
            
        if current_temp > self.temperature_threshold:
            status = 'CRITICAL'
            issues.append(f'High temperature: {current_temp:.1f}°C')
        
        return {
            'status': status,
            'cpu_usage': current_cpu,
            'memory_usage': current_memory,
            'gpu_usage': current_gpu,
            'temperature': current_temp,
            'issues': issues
        }
```
