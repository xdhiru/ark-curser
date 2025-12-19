"""
Adaptive wait timing system - optimizes only WAIT TIMES for animations and loading.
"""

import time
import numpy as np
import pickle
import os
import random
from collections import deque
from typing import Dict, Tuple
from utils.config_loader import get_config_value
from utils.logger import logger

class WaitOptimizer:
    """Optimizes wait times for specific operations with smart deltas."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized: return
        
        self.logger = logger
        self.enabled = get_config_value("adaptive_waits.enabled", True)
        self.aggressiveness = get_config_value("adaptive_waits.aggressiveness", 0.7)
        self.save_file = get_config_value("adaptive_waits.save_file", "config/adaptive_waits.pkl")
        self.max_retries = get_config_value("adaptive_waits.max_retries", 4)
        
        self.history: Dict[str, deque] = {}
        self.convergence_data = {}
        
        self.success_delta = 0.97
        self.retry_expansion = 1.35
        self.stability_threshold = 5
        self.convergence_margin = 0.1
        
        self.default_waits = self._get_initial_defaults()
        self._load_saved_waits()
        self.logger.info(f"WaitOptimizer initialized (enabled: {self.enabled}, max_retries: {self.max_retries})")
        self._initialized = True

    def _get_initial_defaults(self) -> Dict[str, float]:
        """Define the initial pessimistic wait times."""
        return {
            # --- Navigation & Base ---
            "base_transition": 5.0, 
            "base_overview_load": 0.5, 
            "base_left_side_position": 0.5,
            
            # --- Trading Post Interactions ---
            "tp_building_tap": 0.5,
            "tp_entry_dialog": 1.0, 
            "tp_interior_load": 0.5, 
            "tp_workers_section_load": 1.0,
            "pre_workers_click": 0.5,
            
            # --- Worker Management ---
            "worker_list_ready": 0.15, 
            "category_filter_switch": 0.15, 
            "worker_selection_feedback": 0.3,
            "worker_deselect_all": 0.5, 
            "worker_confirmation_dialog": 1.0,
            
            # --- Drones & Orders ---
            "drone_interface_load": 0.5, 
            "drone_animation": 1.5,
            "order_collection_animation": 1.5, 
            "order_check": 0.5,
            
            # --- Low Level Operations ---
            "swipe_completion": 0.2, 
            "slow_swipe_completion": 0.2,
            "template_check_interval": 0.5, 
            "template_click": 0.5, 
            "region_click": 0.5,
            "retry_delay": 0.5, 
            "screen_transition": 0.5,
            "pre_template_search": 0.5,
            
            # --- Post-Action Delays ---
            "post_click_wait": 0.3,
            "post_region_click": 0.3,
            "post_template_find": 0.2,
            "post_navigation": 0.5,
            
            # --- OCR / Vision ---
            "text_find": 0.5,
            "timer_read_delay": 1.0
        }
    
    def _load_saved_waits(self):
        if not os.path.exists(self.save_file): return
        try:
            with open(self.save_file, 'rb') as f:
                saved_data = pickle.load(f)
            self.logger.debug(f"Importing saved waits from {self.save_file}...")
            for k, v in saved_data.get('waits', {}).items():
                if k not in self.default_waits:
                    self.logger.debug(f"Found new wait key: '{k}'={v:.2f}s (not present in adaptive_waits.py defaults)")
                self.default_waits[k] = v
            self.logger.debug("Importing completed.")
            self.history = saved_data.get('history', {})
            self.convergence_data = saved_data.get('convergence', {})
            self.logger.info(f"Loaded saved wait times from {self.save_file}")
        except Exception as e:
            self.logger.warning(f"Failed to load saved wait times: {e}")
    
    def save_waits(self):
        if not self.enabled: return
        try:
            os.makedirs(os.path.dirname(self.save_file), exist_ok=True)
            with open(self.save_file, 'wb') as f:
                pickle.dump({'waits': self.default_waits, 'history': self.history, 'convergence': self.convergence_data}, f)
        except Exception as e:
            self.logger.error(f"Failed to save wait times: {e}")
    
    def get_wait_time(self, wait_type: str, min_wait: float = 0.05) -> float:
        if not self.enabled:
            return max(min_wait, self.default_waits.get(wait_type, 0.5))
        
        base = self.default_waits.get(wait_type, 0.5)
        variance = 1.0 + (random.random() * 0.02 - 0.01)
        return max(min_wait, base * variance)
    
    def record_wait_result(self, wait_type: str, wait_time_used: float, 
                           was_successful: bool, retry_count: int = 0) -> Tuple[bool, float]:
        if not self.enabled: return False, wait_time_used
        
        if wait_type not in self.history: self.history[wait_type] = deque(maxlen=100)
        self.history[wait_type].append((wait_time_used, was_successful, retry_count))

        current_permanent_wait = self.default_waits.get(wait_type, 0.5)

        if was_successful:
            if retry_count == 0:
                # OPTIMIZATION (Learn Down)
                new_wait = current_permanent_wait * self.success_delta
                self._update_permanent_wait(wait_type, new_wait)
                return False, new_wait
            else:
                # CORRECTION (Learn Up)
                target_time = wait_time_used * 1.05
                weighted_new = (current_permanent_wait * 0.7) + (target_time * 0.3)
                self.logger.info(f"Wait '{wait_type}' adapted UP: {current_permanent_wait:.2f}s -> {weighted_new:.2f}s (Actual: {wait_time_used:.2f}s)")
                self._update_permanent_wait(wait_type, weighted_new)
                return False, weighted_new
        else:
            # FAILURE
            if retry_count < self.max_retries:
                next_temp_wait = wait_time_used * self.retry_expansion
                next_temp_wait = min(next_temp_wait, 15.0)
                return True, next_temp_wait
            else:
                self.logger.debug(f"Operation '{wait_type}' failed max retries. Timing unchanged.")
                return False, current_permanent_wait

    def _update_permanent_wait(self, wait_type: str, new_val: float):
        new_val = max(0.1, min(new_val, 10.0))
        self.default_waits[wait_type] = new_val
        
        if wait_type not in self.convergence_data:
            self.convergence_data[wait_type] = {"baseline": new_val, "stable_count": 0}
            
        baseline = self.convergence_data[wait_type]["baseline"]
        if abs(new_val - baseline) / baseline < self.convergence_margin:
            self.convergence_data[wait_type]["stable_count"] += 1
        else:
            self.convergence_data[wait_type]["baseline"] = new_val
            self.convergence_data[wait_type]["stable_count"] = 0

    def static_wait(self, wait_type: str, min_wait: float = 0.05) -> float:
        """Blind sleep wrapper using optimized timing (No validation)."""
        t = self.get_wait_time(wait_type, min_wait)
        time.sleep(t)
        return t
    
    def print_report(self):
        header = f"{'OPERATION':<35} | {'WAIT':<8} | {'STATUS':<10} | {'SAMPLES':<7} | {'SUCCESS %':<9}"
        sep = "-" * len(header)
        
        self.logger.info("\n" + "="*len(header))
        self.logger.info(f"{'WAIT OPTIMIZATION REPORT':^{len(header)}}")
        self.logger.info("="*len(header))
        self.logger.info(header)
        self.logger.info(sep)

        for key in sorted(self.default_waits.keys()):
            val = self.default_waits[key]
            hist = self.history.get(key, [])
            count = len(hist)
            
            status = "NEW"
            if "buffer" in key:
                status = "CONSTANT"
            elif key in self.convergence_data:
                if self.convergence_data[key]["stable_count"] >= self.stability_threshold:
                    status = "STABLE"
                else:
                    status = "ADAPTING"
            elif count > 0:
                status = "LEARNING"
                
            success_pct = "N/A"
            if count > 0:
                successes = sum(1 for _, s, _ in hist if s)
                pct = (successes / count) * 100
                success_pct = f"{pct:.0f}%"

            self.logger.info(f"{key:<35} | {val:5.2f}s  | {status:<10} | {count:<7} | {success_pct:>9}")

        self.logger.info("="*len(header) + "\n")

wait_optimizer = WaitOptimizer()