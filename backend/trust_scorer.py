from typing import Dict, Any, Optional
from datetime import datetime
import logging
from config import settings

logger = logging.getLogger(__name__)

class TrustScorer:
    def __init__(self):
        self.current_score = settings.INITIAL_TRUST_SCORE
        self.session_id = None
        self.score_history = []
        self.trust_deductions = {}  # Track deductions for potential restoration
        
    def initialize_session(self, session_id: int) -> float:
        """Initialize trust score for a new live session"""
        self.current_score = settings.INITIAL_TRUST_SCORE
        self.session_id = session_id
        self.score_history = [{
            'timestamp': datetime.now(),
            'score': self.current_score,
            'change': 0,
            'reason': 'session_start'
        }]
        self.trust_deductions = {}
        
        logger.info(f"Trust score initialized for session {session_id}: {self.current_score}")
        return self.current_score
    
    def calculate_trust_deduction(self, event_type: str, confidence: float) -> float:
        """Calculate trust deduction based on event type and confidence"""
        base_weight = settings.TRUST_WEIGHTS.get(event_type, -5)
        
        # Scale deduction by confidence (0.0 to 1.0)
        deduction = abs(base_weight) * confidence
        
        # Cap maximum deduction per event
        max_deduction = abs(base_weight)
        deduction = min(deduction, max_deduction)
        
        return deduction
    
    def update_trust_score(self, event_id: int, event_type: str, confidence: float, 
                          is_anomaly: bool) -> Dict[str, Any]:
        """Update trust score based on anomaly detection"""
        if not is_anomaly:
            return {
                'new_score': self.current_score,
                'change': 0,
                'deduction': 0,
                'alert_triggered': False
            }
        
        # Calculate trust deduction
        deduction = self.calculate_trust_deduction(event_type, confidence)
        
        # Update score
        new_score = max(0, self.current_score - deduction)
        change = new_score - self.current_score
        
        # Track deduction for potential restoration
        self.trust_deductions[event_id] = {
            'deduction': deduction,
            'event_type': event_type,
            'confidence': confidence,
            'timestamp': datetime.now()
        }
        
        # Update score history
        self.score_history.append({
            'timestamp': datetime.now(),
            'score': new_score,
            'change': change,
            'reason': f'anomaly_{event_type}',
            'event_id': event_id,
            'confidence': confidence
        })
        
        self.current_score = new_score
        
        # Check for alert threshold
        alert_triggered = new_score < settings.TRUST_ALERT_THRESHOLD
        
        if alert_triggered:
            logger.warning(f"Trust score alert triggered: {new_score} < {settings.TRUST_ALERT_THRESHOLD}")
        
        logger.info(f"Trust score updated: {self.current_score} (change: {change})")
        
        return {
            'new_score': self.current_score,
            'change': change,
            'deduction': deduction,
            'alert_triggered': alert_triggered,
            'confidence': confidence
        }
    
    def restore_trust(self, event_id: int) -> Dict[str, Any]:
        """Restore trust points when admin marks anomaly as normal"""
        if event_id not in self.trust_deductions:
            logger.warning(f"No trust deduction found for event {event_id}")
            return {
                'new_score': self.current_score,
                'change': 0,
                'restored': 0
            }
        
        deduction_info = self.trust_deductions[event_id]
        restored_points = deduction_info['deduction']
        
        # Restore trust score
        new_score = min(settings.INITIAL_TRUST_SCORE, self.current_score + restored_points)
        change = new_score - self.current_score
        
        # Update score history
        self.score_history.append({
            'timestamp': datetime.now(),
            'score': new_score,
            'change': change,
            'reason': f'admin_restore_{event_id}',
            'event_id': event_id
        })
        
        self.current_score = new_score
        
        # Remove from deductions tracking
        del self.trust_deductions[event_id]
        
        logger.info(f"Trust restored for event {event_id}: +{restored_points} points")
        
        return {
            'new_score': self.current_score,
            'change': change,
            'restored': restored_points
        }
    
    def get_current_score(self) -> float:
        """Get current trust score"""
        return self.current_score
    
    def get_score_history(self, limit: Optional[int] = None) -> list:
        """Get trust score history"""
        if limit:
            return self.score_history[-limit:]
        return self.score_history
    
    def get_score_stats(self) -> Dict[str, Any]:
        """Get trust score statistics"""
        if not self.score_history:
            return {
                'current_score': self.current_score,
                'total_changes': 0,
                'max_score': self.current_score,
                'min_score': self.current_score,
                'average_score': self.current_score
            }
        
        scores = [entry['score'] for entry in self.score_history]
        
        return {
            'current_score': self.current_score,
            'total_changes': len(self.score_history),
            'max_score': max(scores),
            'min_score': min(scores),
            'average_score': sum(scores) / len(scores),
            'session_duration': (self.score_history[-1]['timestamp'] - self.score_history[0]['timestamp']).total_seconds() / 60
        }
    
    def reset_score(self):
        """Reset trust score to initial value"""
        self.current_score = settings.INITIAL_TRUST_SCORE
        self.score_history = [{
            'timestamp': datetime.now(),
            'score': self.current_score,
            'change': 0,
            'reason': 'reset'
        }]
        self.trust_deductions = {}
        
        logger.info("Trust score reset to initial value")

# Global trust scorer instance
trust_scorer = TrustScorer()
