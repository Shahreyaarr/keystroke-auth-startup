"""
Keystroke Dynamics Engine - Feature Extraction and Authentication
"""

import json
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from collections import defaultdict
import structlog

logger = structlog.get_logger()


@dataclass
class KeystrokeFeatures:
    """Extracted keystroke features"""
    dwell_times: Dict[str, List[float]]  # Key press duration in ms
    flight_times: List[float]  # Time between release and next press
    digraph_times: Dict[str, List[float]]  # Two-key sequence times
    trigraph_times: Dict[str, List[float]]  # Three-key sequence times
    typing_speed_wpm: float
    rhythm_consistency: float
    total_keystrokes: int


class KeystrokeEngine:
    """
    Keystroke Dynamics Authentication Engine
    
    Extracts behavioral biometric features from keystroke timing data
    and performs template matching for user authentication.
    """
    
    def __init__(self, threshold: float = 0.75):
        """
        Initialize the keystroke engine
        
        Args:
            threshold: Authentication threshold (0-1)
        """
        self.threshold = threshold
        self.min_samples = 5
        logger.info(f"KeystrokeEngine initialized with threshold={threshold}")
    
    def extract_features(self, events: List[Dict]) -> KeystrokeFeatures:
        """
        Extract keystroke features from raw event data
        
        Args:
            events: List of keystroke events with key, action, timestamp
            
        Returns:
            KeystrokeFeatures object
        """
        # Sort events by timestamp
        events = sorted(events, key=lambda x: x.get('timestamp', 0))
        
        # Track key press and release times
        key_press_times = {}
        key_release_times = {}
        dwell_times = defaultdict(list)
        
        # Process events
        for event in events:
            key = event.get('key', '')
            action = event.get('action', '')
            timestamp = event.get('timestamp', 0)
            
            if action == 'press':
                key_press_times[key] = timestamp
            elif action == 'release':
                key_release_times[key] = timestamp
                # Calculate dwell time
                if key in key_press_times:
                    dwell = timestamp - key_press_times[key]
                    if dwell > 0 and dwell < 5000:  # Filter outliers (>5s)
                        dwell_times[key].append(dwell)
        
        # Calculate flight times (time between release and next press)
        flight_times = []
        sorted_events = sorted(events, key=lambda x: x.get('timestamp', 0))
        
        for i in range(len(sorted_events) - 1):
            curr = sorted_events[i]
            next_event = sorted_events[i + 1]
            
            if curr.get('action') == 'release' and next_event.get('action') == 'press':
                flight = next_event.get('timestamp', 0) - curr.get('timestamp', 0)
                if flight > 0 and flight < 5000:  # Filter outliers
                    flight_times.append(flight)
        
        # Calculate digraphs (two-key sequences)
        digraph_times = defaultdict(list)
        press_events = [e for e in sorted_events if e.get('action') == 'press']
        
        for i in range(len(press_events) - 1):
            curr_key = press_events[i].get('key', '')
            next_key = press_events[i + 1].get('key', '')
            digraph = f"{curr_key}{next_key}"
            
            time_diff = press_events[i + 1].get('timestamp', 0) - press_events[i].get('timestamp', 0)
            if time_diff > 0 and time_diff < 5000:
                digraph_times[digraph].append(time_diff)
        
        # Calculate trigraphs (three-key sequences)
        trigraph_times = defaultdict(list)
        for i in range(len(press_events) - 2):
            trig = f"{press_events[i].get('key', '')}{press_events[i+1].get('key', '')}{press_events[i+2].get('key', '')}"
            time_diff = press_events[i + 2].get('timestamp', 0) - press_events[i].get('timestamp', 0)
            if time_diff > 0 and time_diff < 10000:
                trigraph_times[trig].append(time_diff)
        
        # Calculate typing speed (WPM approximation)
        total_chars = len([e for e in events if e.get('action') == 'press'])
        if len(events) >= 2:
            time_span = (events[-1].get('timestamp', 0) - events[0].get('timestamp', 0)) / 1000  # seconds
            typing_speed = (total_chars / 5) / (time_span / 60) if time_span > 0 else 0
        else:
            typing_speed = 0
        
        # Calculate rhythm consistency (coefficient of variation of flight times)
        if len(flight_times) > 1:
            mean_flight = np.mean(flight_times)
            std_flight = np.std(flight_times)
            rhythm_consistency = 1 - (std_flight / mean_flight) if mean_flight > 0 else 0
            rhythm_consistency = max(0, min(1, rhythm_consistency))  # Clamp to 0-1
        else:
            rhythm_consistency = 0
        
        return KeystrokeFeatures(
            dwell_times=dict(dwell_times),
            flight_times=flight_times,
            digraph_times=dict(digraph_times),
            trigraph_times=dict(trigraph_times),
            typing_speed_wpm=round(typing_speed, 2),
            rhythm_consistency=round(rhythm_consistency, 4),
            total_keystrokes=total_chars
        )
    
    def create_template(self, samples: List[List[Dict]]) -> Dict[str, Any]:
        """
        Create a user template from multiple keystroke samples
        
        Args:
            samples: List of keystroke event lists
            
        Returns:
            Template dictionary with aggregated features
        """
        if len(samples) < self.min_samples:
            raise ValueError(f"At least {self.min_samples} samples required for enrollment")
        
        # Extract features from all samples
        all_features = [self.extract_features(sample) for sample in samples]
        
        # Aggregate dwell times
        template_dwell = defaultdict(list)
        for features in all_features:
            for key, times in features.dwell_times.items():
                template_dwell[key].extend(times)
        
        # Calculate mean and std for each key
        dwell_stats = {}
        for key, times in template_dwell.items():
            if len(times) >= 2:
                dwell_stats[key] = {
                    'mean': float(np.mean(times)),
                    'std': float(np.std(times)),
                    'count': len(times)
                }
        
        # Aggregate flight times
        all_flight_times = []
        for features in all_features:
            all_flight_times.extend(features.flight_times)
        
        flight_stats = {}
        if len(all_flight_times) >= 2:
            flight_stats = {
                'mean': float(np.mean(all_flight_times)),
                'std': float(np.std(all_flight_times)),
                'count': len(all_flight_times)
            }
        
        # Aggregate digraphs
        digraph_stats = defaultdict(list)
        for features in all_features:
            for digraph, times in features.digraph_times.items():
                digraph_stats[digraph].extend(times)
        
        digraph_template = {}
        for digraph, times in digraph_stats.items():
            if len(times) >= 2:
                digraph_template[digraph] = {
                    'mean': float(np.mean(times)),
                    'std': float(np.std(times)),
                    'count': len(times)
                }
        
        # Calculate average typing speed
        avg_speed = np.mean([f.typing_speed_wpm for f in all_features])
        avg_rhythm = np.mean([f.rhythm_consistency for f in all_features])
        
        template = {
            'dwell_stats': dwell_stats,
            'flight_stats': flight_stats,
            'digraph_stats': digraph_template,
            'typing_speed': float(avg_speed),
            'rhythm_consistency': float(avg_rhythm),
            'sample_count': len(samples),
            'total_keystrokes': sum(f.total_keystrokes for f in all_features)
        }
        
        logger.info(f"Template created with {len(samples)} samples, {len(dwell_stats)} keys")
        return template
    
    def verify(self, template: Dict[str, Any], sample_events: List[Dict]) -> Tuple[float, Dict]:
        """
        Verify a keystroke sample against a user template
        
        Args:
            template: User's keystroke template
            sample_events: Keystroke events to verify
            
        Returns:
            Tuple of (match_score 0-1, details dict)
        """
        # Extract features from sample
        sample_features = self.extract_features(sample_events)
        
        # Calculate match scores for different feature types
        scores = []
        details = {
            'dwell_score': 0,
            'flight_score': 0,
            'digraph_score': 0,
            'speed_score': 0,
            'rhythm_score': 0
        }
        
        # Compare dwell times
        dwell_matches = 0
        dwell_total = 0
        template_dwell = template.get('dwell_stats', {})
        
        for key, times in sample_features.dwell_times.items():
            if key in template_dwell and times:
                sample_mean = np.mean(times)
                template_mean = template_dwell[key]['mean']
                template_std = template_dwell[key]['std']
                
                # Calculate z-score
                if template_std > 0:
                    z_score = abs(sample_mean - template_mean) / template_std
                    # Convert to similarity score (higher is better)
                    similarity = max(0, 1 - (z_score / 3))
                    dwell_matches += similarity
                else:
                    dwell_matches += 1 if abs(sample_mean - template_mean) < 50 else 0
                dwell_total += 1
        
        if dwell_total > 0:
            details['dwell_score'] = dwell_matches / dwell_total
            scores.append(details['dwell_score'])
        
        # Compare flight times
        flight_stats = template.get('flight_stats', {})
        if sample_features.flight_times and flight_stats:
            sample_mean = np.mean(sample_features.flight_times)
            template_mean = flight_stats['mean']
            template_std = flight_stats['std']
            
            if template_std > 0:
                z_score = abs(sample_mean - template_mean) / template_std
                details['flight_score'] = max(0, 1 - (z_score / 3))
            else:
                details['flight_score'] = 1 if abs(sample_mean - template_mean) < 100 else 0
            scores.append(details['flight_score'])
        
        # Compare digraphs
        digraph_stats = template.get('digraph_stats', {})
        if sample_features.digraph_times and digraph_stats:
            digraph_matches = 0
            digraph_total = 0
            
            for digraph, times in sample_features.digraph_times.items():
                if digraph in digraph_stats and times:
                    sample_mean = np.mean(times)
                    template_mean = digraph_stats[digraph]['mean']
                    template_std = digraph_stats[digraph]['std']
                    
                    if template_std > 0:
                        z_score = abs(sample_mean - template_mean) / template_std
                        similarity = max(0, 1 - (z_score / 3))
                        digraph_matches += similarity
                    else:
                        digraph_matches += 1 if abs(sample_mean - template_mean) < 100 else 0
                    digraph_total += 1
            
            if digraph_total > 0:
                details['digraph_score'] = digraph_matches / digraph_total
                scores.append(details['digraph_score'])
        
        # Compare typing speed
        template_speed = template.get('typing_speed', 0)
        if template_speed > 0 and sample_features.typing_speed_wpm > 0:
            speed_diff = abs(sample_features.typing_speed_wpm - template_speed) / template_speed
            details['speed_score'] = max(0, 1 - speed_diff)
            scores.append(details['speed_score'])
        
        # Compare rhythm consistency
        template_rhythm = template.get('rhythm_consistency', 0)
        if template_rhythm > 0:
            rhythm_diff = abs(sample_features.rhythm_consistency - template_rhythm)
            details['rhythm_score'] = max(0, 1 - rhythm_diff)
            scores.append(details['rhythm_score'])
        
        # Calculate overall score
        if scores:
            # Weighted average
            weights = [0.25, 0.20, 0.25, 0.15, 0.15]  # dwell, flight, digraph, speed, rhythm
            weighted_sum = sum(s * w for s, w in zip(scores, weights[:len(scores)]))
            total_weight = sum(weights[:len(scores)])
            match_score = weighted_sum / total_weight
        else:
            match_score = 0
        
        details['sample_keystrokes'] = sample_features.total_keystrokes
        details['template_keystrokes'] = template.get('total_keystrokes', 0)
        
        logger.info(f"Verification complete: score={match_score:.3f}, threshold={self.threshold}")
        
        return match_score, details
    
    def calculate_quality_score(self, template: Dict[str, Any]) -> float:
        """
        Calculate the quality score of a template
        
        Args:
            template: User template
            
        Returns:
            Quality score 0-100
        """
        scores = []
        
        # Sample count score
        sample_count = template.get('sample_count', 0)
        sample_score = min(1, sample_count / 10)  # Max score at 10 samples
        scores.append(sample_score * 25)
        
        # Key coverage score
        dwell_stats = template.get('dwell_stats', {})
        key_coverage = min(1, len(dwell_stats) / 20)  # Max at 20 unique keys
        scores.append(key_coverage * 25)
        
        # Consistency score (based on std/mean ratio)
        consistency_scores = []
        for key, stats in dwell_stats.items():
            if stats['mean'] > 0:
                cv = stats['std'] / stats['mean']  # Coefficient of variation
                consistency_scores.append(max(0, 1 - cv))
        
        if consistency_scores:
            avg_consistency = np.mean(consistency_scores)
            scores.append(avg_consistency * 25)
        else:
            scores.append(0)
        
        # Total keystrokes score
        total_keystrokes = template.get('total_keystrokes', 0)
        keystroke_score = min(1, total_keystrokes / 500)  # Max at 500 keystrokes
        scores.append(keystroke_score * 25)
        
        return sum(scores)


# Global engine instance
keystroke_engine = KeystrokeEngine()
