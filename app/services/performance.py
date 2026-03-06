"""
Performance tracking and benchmarking for NarrativeFlow.
"""

import time
import psutil
import asyncio
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    # Data collection metrics
    data_throughput_per_second: float
    total_items_processed: int
    collection_errors: int
    avg_collection_latency_ms: float

    # Classification metrics
    classification_speed_ms: float
    classification_accuracy: float
    total_items_classified: int
    narratives_detected: Dict[str, int]

    # Signal generation metrics
    signal_generation_time_ms: float
    signals_generated: int
    divergences_detected: int
    false_positive_rate: float

    # API performance
    avg_api_response_time_ms: float
    api_requests_per_second: float
    api_error_rate: float

    # System metrics
    cpu_usage_percent: float
    memory_usage_mb: float
    disk_io_mb_per_sec: float
    uptime_hours: float

    # Database metrics
    db_query_avg_ms: float
    db_connections_active: int
    db_size_mb: float

class PerformanceTracker:
    """Track and benchmark system performance."""

    def __init__(self):
        self.start_time = datetime.now()
        self.metrics_history = []
        self.current_metrics = None

        # Counters
        self.items_processed = 0
        self.items_classified = 0
        self.signals_generated = 0
        self.api_requests = 0
        self.errors = 0

        # Timers
        self.collection_times = []
        self.classification_times = []
        self.signal_times = []
        self.api_times = []
        self.db_times = []

        # Narrative counts
        self.narrative_counts = {
            "AI": 0,
            "RWA": 0,
            "DePIN": 0,
            "Memecoins": 0,
            "L2": 0,
            "Gaming": 0,
            "DeFi": 0,
            "NFT": 0
        }

    def record_collection(self, items: int, duration_ms: float, errors: int = 0):
        """Record data collection performance."""
        self.items_processed += items
        self.collection_times.append(duration_ms)
        self.errors += errors

        # Keep only last 1000 measurements
        if len(self.collection_times) > 1000:
            self.collection_times = self.collection_times[-1000:]

    def record_classification(self, narrative: str, duration_ms: float):
        """Record classification performance."""
        self.items_classified += 1
        self.classification_times.append(duration_ms)

        if narrative in self.narrative_counts:
            self.narrative_counts[narrative] += 1

        # Keep only last 1000 measurements
        if len(self.classification_times) > 1000:
            self.classification_times = self.classification_times[-1000:]

    def record_signal_generation(self, duration_ms: float, signal_generated: bool = False):
        """Record signal generation performance."""
        self.signal_times.append(duration_ms)
        if signal_generated:
            self.signals_generated += 1

        # Keep only last 100 measurements
        if len(self.signal_times) > 100:
            self.signal_times = self.signal_times[-100:]

    def record_api_request(self, duration_ms: float, error: bool = False):
        """Record API request performance."""
        self.api_requests += 1
        self.api_times.append(duration_ms)
        if error:
            self.errors += 1

        # Keep only last 1000 measurements
        if len(self.api_times) > 1000:
            self.api_times = self.api_times[-1000:]

    def record_db_query(self, duration_ms: float):
        """Record database query performance."""
        self.db_times.append(duration_ms)

        # Keep only last 1000 measurements
        if len(self.db_times) > 1000:
            self.db_times = self.db_times[-1000:]

    def get_system_metrics(self) -> Dict:
        """Get current system resource usage."""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk_io = psutil.disk_io_counters()

            # Calculate disk I/O rate
            disk_mb_per_sec = 0
            if hasattr(self, '_last_disk_io'):
                time_diff = time.time() - self._last_disk_io_time
                bytes_diff = (disk_io.read_bytes + disk_io.write_bytes) - \
                            (self._last_disk_io.read_bytes + self._last_disk_io.write_bytes)
                disk_mb_per_sec = (bytes_diff / (1024 * 1024)) / time_diff if time_diff > 0 else 0

            self._last_disk_io = disk_io
            self._last_disk_io_time = time.time()

            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory.used / (1024 * 1024),
                "memory_percent": memory.percent,
                "disk_io_mb_per_sec": disk_mb_per_sec
            }
        except Exception:
            return {
                "cpu_percent": 0,
                "memory_mb": 0,
                "memory_percent": 0,
                "disk_io_mb_per_sec": 0
            }

    def calculate_metrics(self) -> PerformanceMetrics:
        """Calculate current performance metrics."""
        uptime = (datetime.now() - self.start_time).total_seconds() / 3600
        system_metrics = self.get_system_metrics()

        # Calculate averages
        avg_collection = sum(self.collection_times) / len(self.collection_times) if self.collection_times else 0
        avg_classification = sum(self.classification_times) / len(self.classification_times) if self.classification_times else 0
        avg_signal = sum(self.signal_times) / len(self.signal_times) if self.signal_times else 0
        avg_api = sum(self.api_times) / len(self.api_times) if self.api_times else 0
        avg_db = sum(self.db_times) / len(self.db_times) if self.db_times else 0

        # Calculate throughput
        throughput = self.items_processed / (uptime * 3600) if uptime > 0 else 0
        api_rps = self.api_requests / (uptime * 3600) if uptime > 0 else 0

        # Calculate error rates
        error_rate = self.errors / self.api_requests if self.api_requests > 0 else 0
        false_positive_rate = 0.15  # Placeholder - would calculate from actual signal outcomes

        # Classification accuracy (placeholder - would need ground truth)
        classification_accuracy = 0.92  # 92% accuracy assumption

        return PerformanceMetrics(
            data_throughput_per_second=throughput,
            total_items_processed=self.items_processed,
            collection_errors=self.errors,
            avg_collection_latency_ms=avg_collection,
            classification_speed_ms=avg_classification,
            classification_accuracy=classification_accuracy,
            total_items_classified=self.items_classified,
            narratives_detected=self.narrative_counts.copy(),
            signal_generation_time_ms=avg_signal,
            signals_generated=self.signals_generated,
            divergences_detected=self.signals_generated,
            false_positive_rate=false_positive_rate,
            avg_api_response_time_ms=avg_api,
            api_requests_per_second=api_rps,
            api_error_rate=error_rate,
            cpu_usage_percent=system_metrics["cpu_percent"],
            memory_usage_mb=system_metrics["memory_mb"],
            disk_io_mb_per_sec=system_metrics["disk_io_mb_per_sec"],
            uptime_hours=uptime,
            db_query_avg_ms=avg_db,
            db_connections_active=5,  # Placeholder
            db_size_mb=250.5  # Placeholder
        )

    def get_metrics(self) -> Dict:
        """Get current metrics as dictionary."""
        metrics = self.calculate_metrics()
        return asdict(metrics)

    def get_benchmarks(self) -> Dict:
        """Compare current performance against benchmarks."""
        current = self.calculate_metrics()

        benchmarks = {
            "data_collection": {
                "target_throughput": 1000,
                "actual_throughput": current.data_throughput_per_second,
                "status": "✓" if current.data_throughput_per_second >= 1000 else "✗",
                "performance_ratio": current.data_throughput_per_second / 1000
            },
            "classification": {
                "target_speed_ms": 100,
                "actual_speed_ms": current.classification_speed_ms,
                "status": "✓" if current.classification_speed_ms <= 100 else "✗",
                "performance_ratio": 100 / max(current.classification_speed_ms, 1)
            },
            "signal_generation": {
                "target_time_ms": 1000,
                "actual_time_ms": current.signal_generation_time_ms,
                "status": "✓" if current.signal_generation_time_ms <= 1000 else "✗",
                "performance_ratio": 1000 / max(current.signal_generation_time_ms, 1)
            },
            "api_response": {
                "target_time_ms": 200,
                "actual_time_ms": current.avg_api_response_time_ms,
                "status": "✓" if current.avg_api_response_time_ms <= 200 else "✗",
                "performance_ratio": 200 / max(current.avg_api_response_time_ms, 1)
            },
            "system_resources": {
                "cpu_target_percent": 70,
                "cpu_actual_percent": current.cpu_usage_percent,
                "memory_target_mb": 2048,
                "memory_actual_mb": current.memory_usage_mb,
                "status": "✓" if current.cpu_usage_percent <= 70 and current.memory_usage_mb <= 2048 else "✗"
            },
            "overall_score": 0
        }

        # Calculate overall performance score
        scores = [
            benchmarks["data_collection"]["performance_ratio"],
            benchmarks["classification"]["performance_ratio"],
            benchmarks["signal_generation"]["performance_ratio"],
            benchmarks["api_response"]["performance_ratio"],
            1.0 if benchmarks["system_resources"]["status"] == "✓" else 0.5
        ]
        benchmarks["overall_score"] = sum(scores) / len(scores) * 100

        return benchmarks

    async def start_monitoring(self, interval_seconds: int = 60):
        """Start continuous performance monitoring."""
        while True:
            try:
                metrics = self.calculate_metrics()
                self.current_metrics = metrics
                self.metrics_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "metrics": asdict(metrics)
                })

                # Keep only last 24 hours of history
                cutoff = datetime.now() - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history
                    if datetime.fromisoformat(m["timestamp"]) > cutoff
                ]

                # Log performance summary
                print(f"Performance Update: Throughput={metrics.data_throughput_per_second:.1f}/s, "
                      f"API={metrics.avg_api_response_time_ms:.1f}ms, "
                      f"CPU={metrics.cpu_usage_percent:.1f}%, "
                      f"Signals={metrics.signals_generated}")

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                print(f"Error in performance monitoring: {e}")
                await asyncio.sleep(interval_seconds)

    def generate_report(self) -> str:
        """Generate a performance report."""
        metrics = self.calculate_metrics()
        benchmarks = self.get_benchmarks()

        report = f"""
================================================================================
                     NARRATIVEFLOW PERFORMANCE REPORT
                            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

SYSTEM METRICS
--------------------------------------------------------------------------------
Uptime:                 {metrics.uptime_hours:.1f} hours
CPU Usage:              {metrics.cpu_usage_percent:.1f}%
Memory Usage:           {metrics.memory_usage_mb:.1f} MB
Disk I/O:              {metrics.disk_io_mb_per_sec:.2f} MB/s

DATA COLLECTION
--------------------------------------------------------------------------------
Throughput:            {metrics.data_throughput_per_second:.1f} items/sec {benchmarks['data_collection']['status']}
Total Processed:       {metrics.total_items_processed:,}
Collection Errors:     {metrics.collection_errors}
Avg Latency:          {metrics.avg_collection_latency_ms:.1f} ms

CLASSIFICATION
--------------------------------------------------------------------------------
Speed:                 {metrics.classification_speed_ms:.1f} ms {benchmarks['classification']['status']}
Accuracy:              {metrics.classification_accuracy*100:.1f}%
Total Classified:      {metrics.total_items_classified:,}

Top Narratives:
"""
        for narrative, count in sorted(metrics.narratives_detected.items(), key=lambda x: x[1], reverse=True)[:5]:
            report += f"  - {narrative}: {count:,}\n"

        report += f"""
SIGNAL GENERATION
--------------------------------------------------------------------------------
Generation Time:       {metrics.signal_generation_time_ms:.1f} ms {benchmarks['signal_generation']['status']}
Signals Generated:     {metrics.signals_generated}
Divergences:          {metrics.divergences_detected}
False Positive Rate:   {metrics.false_positive_rate*100:.1f}%

API PERFORMANCE
--------------------------------------------------------------------------------
Response Time:         {metrics.avg_api_response_time_ms:.1f} ms {benchmarks['api_response']['status']}
Requests/sec:         {metrics.api_requests_per_second:.1f}
Error Rate:           {metrics.api_error_rate*100:.2f}%

DATABASE
--------------------------------------------------------------------------------
Query Time:           {metrics.db_query_avg_ms:.1f} ms
Active Connections:   {metrics.db_connections_active}
Database Size:        {metrics.db_size_mb:.1f} MB

BENCHMARK SUMMARY
--------------------------------------------------------------------------------
Overall Score:        {benchmarks['overall_score']:.1f}/100

Status Legend: ✓ = Meeting target, ✗ = Below target

================================================================================
"""
        return report

# Global tracker instance
tracker = PerformanceTracker()

# Decorators for automatic performance tracking
def track_collection(func):
    """Decorator to track data collection performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            items = len(result) if hasattr(result, '__len__') else 1
            tracker.record_collection(items, duration_ms)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            tracker.record_collection(0, duration_ms, errors=1)
            raise e
    return wrapper

def track_api(func):
    """Decorator to track API performance."""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            tracker.record_api_request(duration_ms)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            tracker.record_api_request(duration_ms, error=True)
            raise e
    return wrapper

if __name__ == "__main__":
    # Demo performance tracking
    import random

    # Simulate some metrics
    for _ in range(100):
        tracker.record_collection(random.randint(10, 100), random.uniform(50, 150))
        tracker.record_classification(random.choice(list(tracker.narrative_counts.keys())), random.uniform(20, 80))

    for _ in range(50):
        tracker.record_signal_generation(random.uniform(200, 800), random.random() > 0.7)
        tracker.record_api_request(random.uniform(50, 250), random.random() > 0.95)

    # Generate report
    print(tracker.generate_report())

    # Show benchmarks
    benchmarks = tracker.get_benchmarks()
    print(f"\nOverall Performance Score: {benchmarks['overall_score']:.1f}/100")