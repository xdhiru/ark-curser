from tasks.navigation import *
from utils.ocr import *
from utils.adb import *
from utils.logger import logger
from utils.time_helper import get_ist_time_and_remaining
import time
import heapq
import yaml
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from contextlib import contextmanager

# Load configuration once at module level
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

SCREEN_COORDS = config.get('screen_coordinates', {})
CURRENTLY_TESTING = config.get('currently_testing', False)

# Cursing protocol configuration
CURSE_EXECUTION_BUFFER = config.get('curse_execution_buffer', 45)
CURSE_CONFLICT_THRESHOLD = config.get('curse_conflict_threshold', 240)

# Validate configuration
if CURSE_EXECUTION_BUFFER <= 0:
    raise ValueError(f"curse_execution_buffer must be > 0, got {CURSE_EXECUTION_BUFFER}")

if CURSE_CONFLICT_THRESHOLD < 0:
    raise ValueError(f"curse_conflict_threshold must be >= 0, got {CURSE_CONFLICT_THRESHOLD}")

# Apply testing overrides
if CURRENTLY_TESTING:
    logger.info("Testing mode: Overriding CURSE_EXECUTION_BUFFER to 2s")
    CURSE_EXECUTION_BUFFER = 2

def handle_trading_posts():
    """Main handler for processing all trading posts"""
    tp_matches_list = find_trading_posts()
    
    for match in tp_matches_list:
        TradingPost(match["x"], match["y"])
        logger.info("Trading post handled, returning to base")
        return_back_to_base_left_side()

    TradingPost.initiate_cursing_protocol()

@dataclass
class WorkerSet:
    """Defines worker configuration sets for quick selection"""
    PROVISO_SET = {"Proviso", "Quartz", "Tequila"}
    POZEMKA_SET = {"Pozemka", "Tuye", "Jaye"}
    POZEMKA_SET2 = {"Pozemka", "Tuye", "MrNothing"}
    SHAMARE_SET = {"Shamare", "Firewhistle", "Kirara"}
    SHAMARE_SET2 = {"Shamare", "Gummy", "Kirara"}


class TradingPost:
    """Represents a trading post with curse/uncurse scheduling"""
    
    _tp_count = 0
    all_trading_posts: List['TradingPost'] = []
    curse_uncurse_queue: List[Tuple[float, 'TradingPost', bool]] = []
    
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = self._increment_count()
        self.productivity_workers: List[str] = []
        self.is_currently_cursed = False
        self.execution_timestamp = 0
        
        TradingPost.all_trading_posts.append(self)
        self.update_execution_timestamp()
        self._schedule_curse()
        
    @classmethod
    def _increment_count(cls) -> int:
        cls._tp_count += 1
        return cls._tp_count
        
    def __del__(self):
        if self in TradingPost.all_trading_posts:
            TradingPost.all_trading_posts.remove(self)
        
    def __repr__(self) -> str:
        return f"TradingPost({self.id}, x={self.x}, y={self.y}, cursed={self.is_currently_cursed})"
    
    @contextmanager
    def _ensure_inside_tp(self):
        """Context manager to ensure we're inside the trading post"""
        if not find_template("check-if-inside-tp"):
            self.enter_TP()
        try:
            yield
        finally:
            pass  # Could add cleanup logic here
    
    def enter_TP(self):
        """Enter the trading post"""
        logger.info(f"TP {self.id}: Clicking TP at ({self.x}, {self.y}) to enter")
        adb_tap(self.x, self.y)
        time.sleep(1)
        click_template("tp-entry-arrow")
        time.sleep(0.5)

    def enter_TP_workers(self) -> bool:
        """Enter the workers section of the trading post"""
        logger.info(f"TP {self.id}: Entering TP workers")
        time.sleep(0.5)
        x, y = SCREEN_COORDS['tp_workers_entry_button']
        adb_tap(x, y)
        time.sleep(1)
        return True

    def scan_timer(self) -> int:
        """Scan and return the order timer in seconds"""
        time.sleep(1)
        region = SCREEN_COORDS['order_timer_scan_region']
        return read_timer_from_region(*region)

    def update_execution_timestamp(self):
        """Updates the timer and calculates next execution time"""
        with self._ensure_inside_tp():
            self.execution_timestamp = time.time() + self.scan_timer()
            IST_time, remaining_str = get_ist_time_and_remaining(self.execution_timestamp)
            logger.info(f"TP {self.id}: Set execution timestamp to {IST_time} (in {remaining_str})")

    def _schedule_curse(self, prelay: int = 45):
        """Schedule a curse task"""
        curse_time = self.execution_timestamp - prelay
        heapq.heappush(self.curse_uncurse_queue, (curse_time, self, True))
        logger.debug(f"TP {self.id}: Scheduled curse task")

    def _schedule_uncurse(self, delay: int = 10):
        """Schedule an uncurse task"""
        uncurse_time = self.execution_timestamp + delay
        heapq.heappush(self.curse_uncurse_queue, (uncurse_time, self, False))
        logger.debug(f"TP {self.id}: Scheduled uncurse task")

    def collect_orders(self):
        """Collect ready orders"""
        time.sleep(0.5)
        try: 
            click_template("tp-order-ready-to-deliver")
        except:
            logger.info(f"TP {self.id}: No ready orders to collect")
            pass  # No ready orders

    def save_tp_productivity_workers(self):
        """Save current productivity workers"""
        regions = [
            SCREEN_COORDS['productivity_worker_1_region'],
            SCREEN_COORDS['productivity_worker_2_region'],
            SCREEN_COORDS['productivity_worker_3_region']
        ]
        self.productivity_workers = [read_text_from_region(*r) for r in regions]
        logger.info(f"TP {self.id}: Saved productivity workers: {self.productivity_workers}")

    def _prepare_worker_list(self):
        """Prepare worker list with common sorting and filtering"""
        click_template("worker-list-sort-by-trust")
        time.sleep(0.15)
        click_template("worker-list-sort-by-skill")
        time.sleep(0.15)

    def select_tp_worker_by_text_ocr(self, tp_worker: str, max_swipes: int = 40, reset_swipes: int = 30):
        """Select a worker using OCR text recognition"""
        self._prepare_worker_list()
        
        # Reset to all category
        click_template("operator-categories-all-icon")
        time.sleep(0.15)
        click_template("operator-categories-supporter-icon")
        time.sleep(0.15)
        click_template("operator-categories-all-icon")
        time.sleep(0.15)
        
        swipe_count = 0
        while swipe_count < max_swipes:
            worker_coords = find_text_coordinates(tp_worker)
            if worker_coords:
                adb_tap(worker_coords)
                return True
                
            slow_swipe_left()
            swipe_count += 1
            
            if swipe_count % max_swipes == 0:
                for _ in range(reset_swipes):
                    swipe_right()
        
        logger.warning(f"TP {self.id}: Could not find worker '{tp_worker}'")
        return False
    
    def _scroll_and_tap_worker(self, worker_name: str, timeout_swipes: int = 25) -> bool:
        """Helper to search for and tap a worker using template matching"""
        for _ in range(timeout_swipes):
            if coords := find_template(worker_name):
                click_template(coords)
                logger.info(f"TP {self.id}: Found and tapped worker '{worker_name}'")
                return True
            slow_swipe_left()
        
        logger.warning(f"TP {self.id}: Could not find worker '{worker_name}' after {timeout_swipes} swipes")
        return False

    def _select_workers_by_category(self, workers_config: List[Tuple[str, str]]):
        """
        Select workers by iterating through category and worker pairs.
        Optimized: skips redundant category clicks when consecutive workers share same category.
        
        Args:
            workers_config: List of tuples (category_icon, worker_name)
        """
        self._prepare_worker_list()
        
        current_category = None
        for category_icon, worker_name in workers_config:
            time.sleep(0.15)
            # Only click category if it's different from the current one
            if category_icon != current_category:
                click_template(category_icon)
                current_category = category_icon
                time.sleep(0.15)
            self._scroll_and_tap_worker(worker_name)

    def quick_select_tp_workers_proviso_quartz_tequila(self):
        """Select Proviso, Quartz, and Tequila"""
        workers = [
            ("operator-categories-supporter-icon", "char-name-proviso"),
            ("operator-categories-guard-icon", "char-name-quartz"),
            ("operator-categories-guard-icon", "char-name-tequila"),  # Same category - optimized
        ]
        self._select_workers_by_category(workers)

    def quick_select_tp_workers_pozemka_tuye_jaye(self):
        """Select Pozemka, Tuye, and Jaye"""
        workers = [
            ("operator-categories-sniper-icon", "char-name-pozemka"),
            ("operator-categories-medic-icon", "char-name-tuye"),
            ("operator-categories-specialist-icon", "char-name-jaye"),
        ]
        self._select_workers_by_category(workers)

    def quick_select_tp_workers_pozemka_tuye_mrnothing(self):
        """Select Pozemka, Tuye, and Mr. Nothing"""
        workers = [
            ("operator-categories-sniper-icon", "char-name-pozemka"),
            ("operator-categories-medic-icon", "char-name-tuye"),
            ("operator-categories-specialist-icon", "char-name-mrnothing"),
        ]
        self._select_workers_by_category(workers)

    def quick_select_tp_workers_shamare_firewhistle_kirara(self):
        """Select Shamare, Firewhistle, and Kirara"""
        workers = [
            ("operator-categories-supporter-icon", "char-name-shamare"),
            ("operator-categories-defender-icon", "char-name-firewhistle"),
            ("operator-categories-specialist-icon", "char-name-kirara"),
        ]
        self._select_workers_by_category(workers)
    
    def quick_select_tp_workers_shamare_gummy_kirara(self):
        """Select Shamare, Gummy, and Kirara"""
        workers = [
            ("operator-categories-supporter-icon", "char-name-shamare"),
            ("operator-categories-defender-icon", "char-name-gummy"),
            ("operator-categories-specialist-icon", "char-name-kirara"),
        ]
        self._select_workers_by_category(workers)

    def deselect_all_tp_workers(self):
        """Deselect all workers"""
        click_template("tp-workers-deselect-all-button")

    def confirm_tp_workers(self):
        """Confirm worker selection"""
        click_template("tp-workers-confirm-button")
        if find_template("tp-workers-shift-confirmation-prompt"):
            click_template("tp-workers-shift-confirmation-confirm")
    
    def use_drones_on_tp(self) -> bool:
        """Use drones on the trading post"""
        time.sleep(0.5)
        
        if not find_template("order-efficiency-screen"):
            logger.warning(f"TP {self.id}: Not inside trading post, trying to enter")
            reach_base_left_side()
            self.enter_TP()
        
        if not (drones_icon := find_template("tp-use-drones-icon")):
            logger.info(f"TP {self.id}: Can't find drone icon, halting")
            return False
        
        click_template(drones_icon)
        time.sleep(0.15)
        click_template("tp-use-drones-max-icon")
        time.sleep(0.15)
        click_template("tp-use-drones-confirm-button")
        logger.info(f"TP {self.id}: Used drones successfully")
        time.sleep(0.15)
        return True

    def curse(self, use_drones_after_curse: bool = False):
        """
        Perform curse task - assign special workers.
        
        Args:
            use_drones_after_curse: If True, use drones after assigning curse workers
        """
        logger.info(f"TP {self.id}: Performing curse task (drones={use_drones_after_curse})")
        start_time = time.time()
        
        with self._ensure_inside_tp():
            self.enter_TP_workers()
            self.save_tp_productivity_workers()
            self.deselect_all_tp_workers()
            self.quick_select_tp_workers_proviso_quartz_tequila()
            self.confirm_tp_workers()
            self.is_currently_cursed = True
            
            # Use drones if another curse task is coming soon
            if use_drones_after_curse:
                logger.info(f"TP {self.id}: Using drones and uncursing immediately due to upcoming curse task.")
                self.use_drones_on_tp()
                self.collect_orders()
                self.uncurse()
            else:
                self.update_execution_timestamp()
                self._schedule_uncurse()

        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Curse completed in {duration:.1f}s")

    def uncurse(self):
        """Perform uncurse task - restore original workers"""
        logger.info(f"TP {self.id}: Performing uncurse task")
        start_time = time.time()
        
        with self._ensure_inside_tp():
            self.enter_TP_workers()
            self.deselect_all_tp_workers()
            
            # Use optimized selection if workers match known sets
            worker_set = set(self.productivity_workers)
            if WorkerSet.POZEMKA_SET.issubset(worker_set):
                self.quick_select_tp_workers_pozemka_tuye_jaye()
            elif WorkerSet.POZEMKA_SET2.issubset(worker_set):
                self.quick_select_tp_workers_pozemka_tuye_mrnothing()
            elif WorkerSet.SHAMARE_SET.issubset(worker_set):
                self.quick_select_tp_workers_shamare_firewhistle_kirara()
            elif WorkerSet.SHAMARE_SET2.issubset(worker_set):
                self.quick_select_tp_workers_shamare_gummy_kirara()
            else:
                for worker in self.productivity_workers:
                    self.select_tp_worker_by_text_ocr(worker)
        
            self.confirm_tp_workers()
            self.productivity_workers.clear()
            self.is_currently_cursed = False
            self.update_execution_timestamp()
            self._schedule_curse()

        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Uncurse completed in {duration:.1f}s")

    @classmethod
    def _should_use_drones_after_curse(cls, execution_time: float) -> bool:
        """
        Check if curse should use drones due to another close curse task.
        
        Args:
            execution_time: Current curse task execution time
        
        Returns:
            bool: True if should use drones, False otherwise
        """
        for task_time, _, is_curse in cls.curse_uncurse_queue:
            # Check if there's another CURSE task coming within threshold
            if is_curse and 0 < (task_time - execution_time) <= CURSE_CONFLICT_THRESHOLD:
                logger.info(f"Found another curse task in {task_time - execution_time:.0f}s, using drones")
                return True
        return False

    @classmethod
    def _execute_task(cls, trading_post: 'TradingPost', is_curse: bool, execution_time: float):
        """
        Execute a curse or uncurse task.
        
        Args:
            trading_post: TradingPost instance to execute on
            is_curse: True for curse, False for uncurse
            execution_time: Scheduled execution time
        """
        task_type = "CURSE" if is_curse else "UNCURSE"
        logger.info(f"Executing {task_type} for TP {trading_post.id}")
        
        try:
            reach_base_left_side()
            if is_curse:
                # Check if we should use drones due to upcoming curse tasks
                trading_post.enter_TP()
                use_drones = cls._should_use_drones_after_curse(execution_time)
                trading_post.curse(use_drones_after_curse=use_drones)
            else:
                # For uncurse, sleep until exact execution time
                sleep_time = max(0, execution_time - time.time())
                
                if CURRENTLY_TESTING:
                    sleep_time = 2
                
                time.sleep(sleep_time)
                trading_post.enter_TP()  # it's imporrtant that we enter TP *after* the sleep as it collects the orders on the first tap
                trading_post.uncurse()
            return_back_to_base_left_side()
        except Exception as e:
            logger.error(f"Error executing {task_type} for TP {trading_post.id}: {e}", exc_info=True)

    @classmethod
    def initiate_cursing_protocol(cls):
        """Main loop for processing curse/uncurse tasks"""
        logger.info("Cursing protocol initiated")
        logger.info(f"Config: buffer={CURSE_EXECUTION_BUFFER}s, "
                   f"conflict_threshold={CURSE_CONFLICT_THRESHOLD}s")
        while True:
            try:
                if not cls.curse_uncurse_queue:
                    logger.info("Task queue empty, checking again in 60s")
                    time.sleep(60)
                    continue
                
                current_time = time.time()
                execution_time, trading_post, is_curse = cls.curse_uncurse_queue[0]
                time_left = execution_time - current_time
                task_type = "CURSE" if is_curse else "UNCURSE"

                # Execute if within buffer window (or already past scheduled time)
                if time_left <= CURSE_EXECUTION_BUFFER:
                    heapq.heappop(cls.curse_uncurse_queue)
                    cls._execute_task(trading_post, is_curse, execution_time)
                    continue
                
                # Sleep until CURSE_EXECUTION_BUFFER seconds before execution
                sleep_time = time_left - CURSE_EXECUTION_BUFFER
                IST_time, remaining_str = get_ist_time_and_remaining(execution_time)
                logger.info(f"Deep Sleep - Next Task: [TP{trading_post.id}, {task_type}, {IST_time}] in {remaining_str}")
                time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Unexpected error in cursing protocol: {e}", exc_info=True)
                time.sleep(60)