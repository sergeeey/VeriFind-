"""
Production Monitoring System

Week 2 Days 6-7: Production Readiness
Comprehensive monitoring with Prometheus metrics and alerting
"""

import os
import logging
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from prometheus_client import Counter, Gauge, Histogram, Info

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class AlertRule:
    """Alert rule definition"""
    name: str
    metric: str
    threshold: float
    operator: str  # '>', '<', '==', '>=', '<='
    severity: AlertSeverity
    cooldown_minutes: int = 5
    message_template: str = ""
    
    def check(self, value: float) -> bool:
        """Check if alert should fire"""
        if self.operator == ">":
            return value > self.threshold
        elif self.operator == "<":
            return value < self.threshold
        elif self.operator == ">=":
            return value >= self.threshold
        elif self.operator == "<=":
            return value <= self.threshold
        elif self.operator == "==":
            return value == self.threshold
        return False


@dataclass
class Alert:
    """Fired alert instance"""
    rule_name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    value: float
    threshold: float


class MonitoringSystem:
    """
    Production monitoring and alerting system.
    
    Features:
    - Prometheus metrics export
    - Configurable alert rules
    - Multi-channel notifications (log, slack, email)
    - Cooldown to prevent alert spam
    - Alert history tracking
    """
    
    def __init__(self):
        """Initialize monitoring system"""
        
        # Prometheus metrics
        self._setup_metrics()
        
        # Alert rules
        self.rules: List[AlertRule] = self._default_rules()
        
        # Alert state
        self._last_alert_time: Dict[str, datetime] = {}
        self._alert_handlers: List[Callable[[Alert], None]] = []
        
        # Setup default handlers
        self._setup_default_handlers()
    
    def _setup_metrics(self):
        """Setup Prometheus metrics"""
        
        # Query metrics
        self.queries_total = Counter(
            'ape_queries_total',
            'Total queries processed',
            ['status', 'category']  # status: success, error, timeout
        )
        
        self.query_duration = Histogram(
            'ape_query_duration_seconds',
            'Query processing time',
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0]
        )
        
        # Accuracy metrics
        self.accuracy = Gauge(
            'ape_accuracy',
            'Prediction accuracy by window',
            ['window']  # window: 1h, 24h, 7d, 30d
        )
        
        self.hits_total = Counter(
            'ape_hits_total',
            'Total HIT predictions',
            ['ticker']
        )
        
        self.misses_total = Counter(
            'ape_misses_total',
            'Total MISS predictions',
            ['ticker']
        )
        
        # LLM metrics
        self.llm_calls_total = Counter(
            'ape_llm_calls_total',
            'LLM API calls',
            ['provider', 'status']  # provider: deepseek, anthropic, openai
        )
        
        self.llm_latency = Histogram(
            'ape_llm_latency_seconds',
            'LLM API latency',
            ['provider'],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
        )
        
        self.llm_cost = Counter(
            'ape_llm_cost_dollars',
            'LLM API cost in USD',
            ['provider']
        )
        
        # VEE metrics
        self.vee_executions_total = Counter(
            'ape_vee_executions_total',
            'VEE sandbox executions',
            ['status']  # status: success, error, timeout
        )
        
        self.vee_execution_time = Histogram(
            'ape_vee_execution_time_seconds',
            'VEE execution time',
            buckets=[1.0, 5.0, 10.0, 30.0, 60.0]
        )
        
        # Database metrics
        self.db_queries_total = Counter(
            'ape_db_queries_total',
            'Database queries',
            ['operation', 'table']
        )
        
        self.db_latency = Histogram(
            'ape_db_latency_seconds',
            'Database query latency',
            ['operation']
        )
        
        # System metrics
        self.active_connections = Gauge(
            'ape_active_websocket_connections',
            'Current WebSocket connections'
        )
        
        self.cache_hits = Counter(
            'ape_cache_hits_total',
            'Cache hits',
            ['cache_type']
        )
        
        self.cache_misses = Counter(
            'ape_cache_misses_total',
            'Cache misses',
            ['cache_type']
        )
        
        # Application info
        self.app_info = Info(
            'ape_app',
            'Application information'
        )
        self.app_info.info({
            'version': os.getenv('APP_VERSION', 'unknown'),
            'environment': os.getenv('ENVIRONMENT', 'unknown')
        })
    
    def _default_rules(self) -> List[AlertRule]:
        """Default alert rules"""
        return [
            AlertRule(
                name="accuracy_critical",
                metric="ape_accuracy",
                threshold=0.90,
                operator="<",
                severity=AlertSeverity.CRITICAL,
                cooldown_minutes=5,
                message_template="Accuracy dropped to {value:.1%} (threshold: {threshold:.1%})"
            ),
            AlertRule(
                name="high_error_rate",
                metric="ape_error_rate",
                threshold=0.10,
                operator=">",
                severity=AlertSeverity.HIGH,
                cooldown_minutes=3,
                message_template="Error rate is {value:.1%} (threshold: {threshold:.1%})"
            ),
            AlertRule(
                name="llm_failures",
                metric="ape_llm_failure_rate",
                threshold=0.20,
                operator=">",
                severity=AlertSeverity.HIGH,
                cooldown_minutes=5,
                message_template="LLM failure rate is {value:.1%} (threshold: {threshold:.1%})"
            ),
            AlertRule(
                name="slow_queries",
                metric="ape_slow_query_rate",
                threshold=0.05,
                operator=">",
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=10,
                message_template="{value:.1%} of queries are slow (>60s)"
            ),
            AlertRule(
                name="high_latency",
                metric="ape_p95_latency",
                threshold=30.0,
                operator=">",
                severity=AlertSeverity.MEDIUM,
                cooldown_minutes=5,
                message_template="P95 latency is {value:.1f}s (threshold: {threshold:.1f}s)"
            ),
        ]
    
    def _setup_default_handlers(self):
        """Setup default alert handlers"""
        # Always log alerts
        self.add_alert_handler(self._log_alert)
        
        # Slack if configured
        if os.getenv("SLACK_WEBHOOK_URL"):
            self.add_alert_handler(self._send_slack_alert)
        
        # Email if configured
        if os.getenv("ALERT_EMAIL"):
            self.add_alert_handler(self._send_email_alert)
    
    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """Add custom alert handler"""
        self._alert_handlers.append(handler)
    
    def record_query(
        self,
        status: str,
        category: str,
        duration: float
    ):
        """Record query metrics"""
        self.queries_total.labels(
            status=status,
            category=category
        ).inc()
        
        self.query_duration.observe(duration)
        
        # Check alerts
        if status == "error":
            self._check_alert("ape_error_rate", self._calculate_error_rate())
        
        if duration > 60:
            self._check_alert("ape_slow_query_rate", self._calculate_slow_query_rate())
    
    def record_accuracy(self, accuracy: float, window: str = "1h"):
        """Record accuracy metric"""
        self.accuracy.labels(window=window).set(accuracy)
        self._check_alert("ape_accuracy", accuracy)
    
    def record_llm_call(
        self,
        provider: str,
        status: str,
        latency: float,
        cost: float = 0.0
    ):
        """Record LLM call metrics"""
        self.llm_calls_total.labels(
            provider=provider,
            status=status
        ).inc()
        
        self.llm_latency.labels(provider=provider).observe(latency)
        
        if cost > 0:
            self.llm_cost.labels(provider=provider).inc(cost)
        
        # Check failure rate
        if status != "success":
            failure_rate = self._calculate_llm_failure_rate()
            self._check_alert("ape_llm_failure_rate", failure_rate)
    
    def record_vee_execution(
        self,
        status: str,
        duration: float
    ):
        """Record VEE execution metrics"""
        self.vee_executions_total.labels(status=status).inc()
        self.vee_execution_time.observe(duration)
    
    def record_db_query(
        self,
        operation: str,
        table: str,
        latency: float
    ):
        """Record database query metrics"""
        self.db_queries_total.labels(
            operation=operation,
            table=table
        ).inc()
        
        self.db_latency.labels(operation=operation).observe(latency)
    
    def update_active_connections(self, count: int):
        """Update active WebSocket connections"""
        self.active_connections.set(count)
    
    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache hit/miss"""
        if hit:
            self.cache_hits.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses.labels(cache_type=cache_type).inc()
    
    def _check_alert(self, metric: str, value: float):
        """Check if any alert rules fire"""
        for rule in self.rules:
            if rule.metric == metric:
                if rule.check(value):
                    self._fire_alert(rule, value)
    
    def _fire_alert(self, rule: AlertRule, value: float):
        """Fire an alert"""
        # Check cooldown
        now = datetime.utcnow()
        last_fired = self._last_alert_time.get(rule.name)
        
        if last_fired:
            cooldown = timedelta(minutes=rule.cooldown_minutes)
            if now - last_fired < cooldown:
                return  # Still in cooldown
        
        # Create alert
        message = rule.message_template.format(
            value=value,
            threshold=rule.threshold
        )
        
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=message,
            timestamp=now,
            value=value,
            threshold=rule.threshold
        )
        
        # Update last fired time
        self._last_alert_time[rule.name] = now
        
        # Send to all handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
    
    def _log_alert(self, alert: Alert):
        """Log alert"""
        log_method = {
            AlertSeverity.CRITICAL: logger.critical,
            AlertSeverity.HIGH: logger.error,
            AlertSeverity.MEDIUM: logger.warning,
            AlertSeverity.LOW: logger.info,
            AlertSeverity.INFO: logger.info,
        }.get(alert.severity, logger.warning)
        
        log_method(f"ALERT [{alert.severity.value.upper()}] {alert.rule_name}: {alert.message}")
    
    def _send_slack_alert(self, alert: Alert):
        """Send alert to Slack"""
        import requests
        
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")
        if not webhook_url:
            return
        
        color = {
            AlertSeverity.CRITICAL: "#FF0000",
            AlertSeverity.HIGH: "#FF6600",
            AlertSeverity.MEDIUM: "#FFCC00",
            AlertSeverity.LOW: "#00CC00",
        }.get(alert.severity, "#CCCCCC")
        
        payload = {
            "attachments": [{
                "color": color,
                "title": f"APE 2026 Alert: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value, "short": True},
                    {"title": "Value", "value": f"{alert.value:.4f}", "short": True},
                    {"title": "Threshold", "value": f"{alert.threshold:.4f}", "short": True},
                ],
                "footer": "APE 2026 Monitoring",
                "ts": alert.timestamp.timestamp()
            }]
        }
        
        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
    
    def _send_email_alert(self, alert: Alert):
        """Send alert via email"""
        # TODO: Implement email sending
        pass
    
    def _calculate_error_rate(self) -> float:
        """Calculate current error rate"""
        # TODO: Implement actual calculation from metrics
        return 0.0
    
    def _calculate_slow_query_rate(self) -> float:
        """Calculate slow query rate"""
        # TODO: Implement actual calculation
        return 0.0
    
    def _calculate_llm_failure_rate(self) -> float:
        """Calculate LLM failure rate"""
        # TODO: Implement actual calculation
        return 0.0


# Global instance
monitor: Optional[MonitoringSystem] = None


def get_monitor() -> MonitoringSystem:
    """Get or create monitoring system"""
    global monitor
    if monitor is None:
        monitor = MonitoringSystem()
    return monitor
