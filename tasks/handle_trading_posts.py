"""
Trading post management with curse/uncurse scheduling.
"""

import logging
from tasks.navigation import reach_base, reach_base_left_side, is_inside_tp, find_trading_posts
from utils.ocr import read_text_from_image, read_timer_from_region, find_text_coordinates
from utils.adb import adb_tap, get_cached_screenshot, swipe_right, slow_swipe_left
from utils.logger import logger
from utils.time_helper import get_ist_time_and_remaining
from utils.vision import find_template_in_image
from utils.click_helper import click_template, click_region
from utils.adaptive_waits import wait_optimizer
from utils.config_loader import get_config_value
import time
import heapq
from typing import List, Tuple, Optional, Iterable
from contextlib import contextmanager

SCREEN_COORDS = get_config_value('screen_coordinates', {})
TESTING = get_config_value('currently_testing', False)
CURSE_EXECUTION_BUFFER = 2 if TESTING else get_config_value('curse_execution_buffer', 45)
CURSE_CONFLICT_THRESHOLD = get_config_value('curse_conflict_threshold', 240)

class WorkerConfig:
    WORKERS = {
        'Proviso': ('supporter', 'char-name-proviso'),
        'Quartz': ('guard', 'char-name-quartz'),
        'Tequila': ('guard', 'char-name-tequila'),
        'Pozemka': ('sniper', 'char-name-pozemka'),
        'Tuye': ('medic', 'char-name-tuye'),
        'Jaye': ('specialist', 'char-name-jaye'),
        'MrNothing': ('specialist', 'char-name-mrnothing'),
        'Shamare': ('supporter', 'char-name-shamare'),
        'Firewhistle': ('defender', 'char-name-firewhistle'),
        'Kirara': ('specialist', 'char-name-kirara'),
        'Gummy': ('defender', 'char-name-gummy'),
        'Midnight': ('guard', 'char-name-midnight'),
        'Texas': ('vanguard', 'char-name-texas'),
        'Lappland': ('guard', 'char-name-lappland'),
        'Exusiai': ('sniper', 'char-name-exusiai'),
        'Lemuen': ('sniper', 'char-name-lemuen'),
        'Underflow': ('defender', 'char-name-underflow'),
    }
    CURSE_WORKERS = ('Proviso', 'Quartz', 'Tequila')

class TradingPostAdapter(logging.LoggerAdapter):
    """Automatically prefixes logs with the Trading Post ID."""
    def process(self, msg, kwargs):
        return f"[TP {self.extra['tp_id']}] {msg}", kwargs

class TradingPost:
    """Represents a trading post with curse/uncurse scheduling."""
    
    _instances = []
    _curse_uncurse_queue = []
    
    def __init__(self, x: int, y: int, tp_id: int):
        self.x = x
        self.y = y
        self.id = tp_id
        self.productivity_workers = []
        self.execution_time = 0
        self.is_cursed = False
        
        # Initialize Contextual Logger
        self.logger = TradingPostAdapter(logger, {'tp_id': tp_id})
        
        self._instances.append(self)
        self._initialize()
    
    def _initialize(self):
        self.logger.debug("Initializing")
        if self._update_execution_time():
            self._schedule_curse()
    
    # --- Navigation ---
    @contextmanager
    def _ensure_inside_tp(self):
        for _ in range(3):
            if is_inside_tp():
                yield True
                return
            
            if self._enter_trading_post()[0]:
                wait_optimizer.wait("tp_interior_load")
                yield True
                return
                
        self.logger.error("Failed to confirm entry.")
        yield False

    def _enter_trading_post(self) -> Tuple[bool, int]:
        click_region(
            (self.x-10, self.y-10, self.x+10, self.y+10), 
            max_retries=wait_optimizer.max_retries,
            sleep_after=0
        )
        wait_optimizer.wait("tp_entry_dialog")
        success, r = click_template("tp-entry-arrow", max_retries=0, description=f"TP{self.id}:entry_arrow_check")
        
        if success:
            return True, r
        self.logger.debug("Entry arrow missing. Assuming order collected. Tapping again...")
        time.sleep(0.5) 

        click_region(
            (self.x-10, self.y-10, self.x+10, self.y+10), 
            max_retries=1,
            sleep_after=0
        )
        wait_optimizer.wait("tp_entry_dialog")
        return click_template("tp-entry-arrow", description=f"TP{self.id}:entry_arrow_final")

    def _enter_workers_section(self) -> Tuple[bool, int]:
        wait_optimizer.wait("pre_workers_click")
        x, y = SCREEN_COORDS['tp_workers_entry_button']
        s, r = click_region((x-5, y-5, x+5, y+5))
        if s: wait_optimizer.wait("tp_workers_section_load")
        return s, r

    # --- Scanning ---
    def _update_execution_time(self) -> bool:
        with self._ensure_inside_tp() as ready:
            if not ready: return False
            
            for i in range(3):
                wait_optimizer.wait("timer_read_delay")
                timer = read_timer_from_region(*SCREEN_COORDS['order_timer_scan_region'])
                
                if timer is not None:
                    self.execution_time = time.time() + timer
                    ist, rem = get_ist_time_and_remaining(self.execution_time)
                    self.logger.info(f"Next execution {ist} (in {rem})")
                    return True
        return False

    # --- Scheduling ---
    def _schedule_curse(self, prelay: int = 40):
        if self.execution_time <= 0: return
        curse_time = self.execution_time - prelay
        heapq.heappush(self._curse_uncurse_queue, (curse_time, self, True))
        self.logger.debug(f"Scheduled CURSE at {curse_time}")

    def _schedule_uncurse(self, delay: int = 10):
        if self.execution_time <= 0: return
        uncurse_time = self.execution_time + delay
        heapq.heappush(self._curse_uncurse_queue, (uncurse_time, self, False))
        self.logger.debug(f"Scheduled UNCURSE at {uncurse_time}")

    # --- Worker Logic ---
    def _save_productivity_workers(self) -> Tuple[bool, int]:
        screenshot = get_cached_screenshot(force_fresh=True)
        if screenshot is None: return False, 0
        
        self.productivity_workers = []
        regions = [
            SCREEN_COORDS['productivity_worker_1_region'],
            SCREEN_COORDS['productivity_worker_2_region'],
            SCREEN_COORDS['productivity_worker_3_region']
        ]
        
        for region in regions:
            worker_text = read_text_from_image(screenshot, *region)
            self.productivity_workers.append(worker_text if worker_text else "Unknown")
            
        self.logger.info(f"Saved workers: {self.productivity_workers}")
        return True, 0

    def _sort_workers(self):
        click_template("worker-list-sort-by-trust")
        wait_optimizer.wait("worker_list_ready")
        click_template("worker-list-sort-by-skill")
        wait_optimizer.wait("worker_list_ready")

    def _find_and_select_worker(self, target: str, is_template: bool) -> bool:
        for swipe_count in range(15):
            if is_template:
                s, _ = click_template(target, max_retries=1, wait_after=True)
                if s: 
                    wait_optimizer.wait("worker_selection_feedback")
                    return True
            else:
                coords = find_text_coordinates(target)
                if coords:
                    adb_tap(coords[0][0], coords[0][1])
                    wait_optimizer.wait("worker_selection_feedback")
                    return True
            slow_swipe_left()
        return False

    def _select_workers(self, worker_names: Iterable[str]) -> int:
        self._sort_workers()
        total_retries = 0
        
        current_category = None
        for worker_name in worker_names:
            if worker_name in WorkerConfig.WORKERS:
                category, template_name = WorkerConfig.WORKERS[worker_name]
                category_icon = f"operator-categories-{category.lower()}-icon"
                
                if category_icon != current_category:
                    if click_template(category_icon)[0]:
                        current_category = category_icon
                        wait_optimizer.wait("category_filter_switch")
                
                if not self._find_and_select_worker(template_name, is_template=True):
                    self.logger.warning(f"Failed to find {worker_name}")
            else:
                click_template("operator-categories-all-icon")
                current_category = None
                if not self._find_and_select_worker(worker_name, is_template=False):
                    self.logger.warning(f"Failed to find {worker_name} (OCR)")
                    
        return total_retries

    # --- Actions ---
    def curse(self, use_drones: bool = False) -> Tuple[bool, int]:
        start_time = time.time()
        self.logger.info("Executing CURSE")
        
        with self._ensure_inside_tp() as inside:
            if not inside: return False, 0
            
            self._enter_workers_section()
            self._save_productivity_workers()
            click_template("tp-workers-deselect-all-button")
            wait_optimizer.wait("worker_deselect_all")
            
            self._select_workers(WorkerConfig.CURSE_WORKERS)
            
            s, r = click_template("tp-workers-confirm-button")
            if s:
                wait_optimizer.wait("worker_confirmation_dialog")
                click_template("tp-workers-shift-confirmation-prompt", max_retries=0)
                wait_optimizer.wait("worker_change_animation")
            else:
                return False, r

            self.is_cursed = True
            
            if use_drones:
                self._use_drones()
                self._collect_orders()
                duration = time.time() - start_time
                self.logger.info(f"CURSE (with drones) complete in {duration:.2f}s")
                return self.uncurse()
            else:
                if self._update_execution_time():
                    self._schedule_uncurse()
                    duration = time.time() - start_time
                    self.logger.info(f"CURSE complete in {duration:.2f}s")
                    return True, 0
        return False, 0

    def uncurse(self) -> Tuple[bool, int]:
        start_time = time.time()
        self.logger.info("Executing UNCURSE")
        
        with self._ensure_inside_tp() as inside:
            if not inside: return False, 0
            
            self._enter_workers_section()
            click_template("tp-workers-deselect-all-button")
            wait_optimizer.wait("worker_deselect_all")
            
            if not self.productivity_workers:
                self.logger.warning("No saved workers!")
            
            self._select_workers(self.productivity_workers)
            self.productivity_workers = []
            
            s, r = click_template("tp-workers-confirm-button")
            if s:
                wait_optimizer.wait("worker_confirmation_dialog")
                click_template("tp-workers-shift-confirmation-prompt", max_retries=0)
                wait_optimizer.wait("worker_change_animation")
            else:
                return False, r

            self.is_cursed = False
            
            if self._update_execution_time():
                self._schedule_curse()
                duration = time.time() - start_time
                self.logger.info(f"UNCURSE complete in {duration:.2f}s")
                return True, 0
        return False, 0

    def _use_drones(self):
        if click_template("tp-use-drones-icon")[0]:
            wait_optimizer.wait("drone_interface_load")
            click_template("tp-use-drones-max-icon")
            wait_optimizer.wait("drone_interface_load")
            click_template("tp-use-drones-confirm-button")
            wait_optimizer.wait("drone_animation")

    def _collect_orders(self):
        wait_optimizer.wait("order_check")
        if click_template("tp-order-ready-to-deliver", max_retries=0)[0]:
            wait_optimizer.wait("order_collection_animation")

    # --- Protocol ---
    @classmethod
    def initiate_cursing_protocol(cls):
        logger.info(f"Protocol Started: Buffer={CURSE_EXECUTION_BUFFER}s, Conflict Threshold={CURSE_CONFLICT_THRESHOLD}s")
        while True:
            try:
                if not cls._curse_uncurse_queue:
                    logger.info("Queue empty, checking in 60s...")
                    time.sleep(60)
                    continue
                
                now = time.time()
                task_time, tp, is_curse = cls._curse_uncurse_queue[0]
                
                if task_time - now <= CURSE_EXECUTION_BUFFER:
                    heapq.heappop(cls._curse_uncurse_queue)
                    
                    use_drones = False
                    if is_curse and cls._curse_uncurse_queue:
                        next_time = cls._curse_uncurse_queue[0][0]
                        if 0 < (next_time - task_time) <= CURSE_CONFLICT_THRESHOLD:
                            logger.info(f"Conflict detected for TP {tp.id}, using drones.")
                            use_drones = True
                    
                    reach_base_left_side()
                    if is_curse:
                        tp.curse(use_drones)
                    else:
                        wait = max(0, task_time - time.time())
                        if wait > 0: time.sleep(wait)
                        tp.uncurse()
                else:
                    sleep_time = task_time - now - CURSE_EXECUTION_BUFFER
                    if sleep_time > 0:
                        ist, rem = get_ist_time_and_remaining(task_time)
                        type_str = "CURSE" if is_curse else "UNCURSE"
                        logger.info(f"Next: TP {tp.id} {type_str} at {ist}. Sleeping {sleep_time:.1f}s")
                        time.sleep(sleep_time)
            except Exception as e:
                logger.error(f"Protocol Error: {e}", exc_info=True)
                time.sleep(60)

def handle_trading_posts():
    reach_base_left_side()
    tps = find_trading_posts()
    for i, match in enumerate(tps):
        TradingPost(match["x"], match["y"], i+1)
        reach_base()
    TradingPost.initiate_cursing_protocol()