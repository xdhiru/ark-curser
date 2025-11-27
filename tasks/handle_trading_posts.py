from tasks.navigation import *
from utils.ocr import *
from utils.adb import *
from utils.logger import logger
from utils.time_helper import get_ist_time_and_remaining
import time
import heapq
import yaml
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from contextlib import contextmanager

# Load configuration once at module level
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

SCREEN_COORDS = config.get('screen_coordinates', {})
CURRENTLY_TESTING = config.get('currently_testing', False)

# Configuration constants
@dataclass
class CursingConfig:
    """
    Configuration for the cursing protocol
    
    CONSTRAINTS (to prevent logic errors):
    1. early_wakeup >= curse_execution_buffer
       - Must wake up before execution to allow monitoring phase
       - Example: If buffer is 30s, need at least 30s to monitor
    
    2. poll_interval <= curse_execution_buffer  
       - Must poll frequently enough to catch execution window
       - Example: If buffer is 30s, polling every 30s ensures we catch it
    
    3. curse_uncurse_conflict_threshold < early_wakeup (recommended)
       - Conflict detection should happen before monitoring phase
       - Prevents detecting conflicts too late
    
    4. curse_execution_buffer > 0
       - Need positive buffer time to prepare for execution
    
    5. poll_interval > 0
       - Need positive polling interval
    """
    early_wakeup: int = 90  # Wake up 90s before execution for monitoring
    poll_interval: int = 30  # Poll every 30s during monitoring phase
    curse_execution_buffer: int = 30  # Execute when within 30s of scheduled time
    curse_uncurse_conflict_threshold: int = 60  # Delay uncurse if curse within 60s
    
    def __post_init__(self):
        """Validate constraints and apply testing overrides"""
        # Validate critical constraints
        if self.early_wakeup < self.curse_execution_buffer:
            raise ValueError(
                f"early_wakeup ({self.early_wakeup}) must be >= curse_execution_buffer ({self.curse_execution_buffer})"
            )
        
        if self.poll_interval > self.curse_execution_buffer:
            raise ValueError(
                f"poll_interval ({self.poll_interval}) must be <= curse_execution_buffer ({self.curse_execution_buffer})"
            )
        
        if self.curse_execution_buffer <= 0:
            raise ValueError(f"curse_execution_buffer must be > 0")
        
        if self.poll_interval <= 0:
            raise ValueError(f"poll_interval must be > 0")
        
        # Warning for recommended constraint
        if self.curse_uncurse_conflict_threshold >= self.early_wakeup:
            logger.warning(
                f"curse_uncurse_conflict_threshold ({self.curse_uncurse_conflict_threshold}) "
                f">= early_wakeup ({self.early_wakeup}). Conflict detection may happen too late."
            )
        
        # Apply testing overrides
        if CURRENTLY_TESTING:
            self.early_wakeup = 30000
            self.poll_interval = 2
            self.curse_execution_buffer = 30000
            # curse_uncurse_conflict_threshold remains unchanged in testing


def handle_trading_posts():
    """Main handler for processing all trading posts"""
    tp_matches_list = find_trading_posts()
    
    for match in tp_matches_list:
        TradingPost(match["x"], match["y"])
        logger.info("Trading post handled, returning to base and sleeping 5 seconds")
        return_back_to_base_left_side()
        time.sleep(5)

    TradingPost.initiate_cursing_protocol()


@dataclass
class WorkerSet:
    """Defines a worker configuration"""
    names: set
    selection_method: str
    
    PROVISO_SET = {"Proviso", "Quartz", "Tequila"}
    POZEMKA_SET = {"Pozemka", "Tuye", "Jaye"}
    SHAMARE_SET = {"Shamare", "Firewhistle", "Kirara"}


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
        time.sleep(1)

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
            order_timer_seconds = self.scan_timer()
            logger.debug(f"TP {self.id}: Scanned timer - {order_timer_seconds} seconds")
            
            self.execution_timestamp = time.time() + order_timer_seconds
            IST_time, remaining_str = get_ist_time_and_remaining(self.execution_timestamp)
            logger.info(f"TP {self.id}: Set execution timestamp to {IST_time} (in {remaining_str})")

    def _schedule_curse(self):
        """Schedule a curse task"""
        curse_time = self.execution_timestamp - 60
        heapq.heappush(self.curse_uncurse_queue, (curse_time, self, True))
        logger.debug(f"TP {self.id}: Scheduled curse task")

    def _schedule_uncurse(self):
        """Schedule an uncurse task"""
        uncurse_time = self.execution_timestamp + 10
        heapq.heappush(self.curse_uncurse_queue, (uncurse_time, self, False))
        logger.debug(f"TP {self.id}: Scheduled uncurse task")

    def collect_orders(self):
        """Collect ready orders"""
        time.sleep(1)
        if find_template("tp-order-ready-to-deliver"):
            click_template("tp-order-ready-to-deliver")

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
        time.sleep(0.25)
        click_template("worker-list-sort-by-skill")
        time.sleep(0.25)

    def select_tp_worker_by_text_ocr(self, tp_worker: str, max_swipes: int = 40, reset_swipes: int = 30):
        """Select a worker using OCR text recognition"""
        self._prepare_worker_list()
        
        # Reset to all category
        click_template("operator-categories-all-icon")
        time.sleep(0.25)
        click_template("operator-categories-supporter-icon")
        time.sleep(0.25)
        click_template("operator-categories-all-icon")
        time.sleep(0.25)
        
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
        Select workers by iterating through category and worker pairs
        workers_config: List of tuples (category_icon, worker_name)
        Optimized: skips redundant category clicks when consecutive workers share same category
        """
        self._prepare_worker_list()
        
        current_category = None
        for category_icon, worker_name in workers_config:
            time.sleep(0.25)
            # Only click category if it's different from the current one
            if category_icon != current_category:
                click_template(category_icon)
                current_category = category_icon
                time.sleep(0.25)
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

    def quick_select_tp_workers_shamare_firewhistle_kirara(self):
        """Select Shamare, Firewhistle, and Kirara"""
        workers = [
            ("operator-categories-supporter-icon", "char-name-shamare"),
            ("operator-categories-defender-icon", "char-name-firewhistle"),
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
        time.sleep(0.25)
        click_template("tp-use-drones-max-icon")
        time.sleep(0.25)
        click_template("tp-use-drones-confirm-button")
        logger.info(f"TP {self.id}: Used drones successfully")
        time.sleep(0.25)
        return True

    def curse(self):
        """Perform curse task - assign special workers"""
        logger.info(f"TP {self.id}: Performing curse task")
        start_time = time.time()
        
        self.enter_TP_workers()
        time.sleep(1)
        
        self.save_tp_productivity_workers()
        self.deselect_all_tp_workers()
        self.quick_select_tp_workers_proviso_quartz_tequila()
        self.confirm_tp_workers()
        self.is_currently_cursed = True

        self.update_execution_timestamp()
        self._schedule_uncurse()
        return_back_to_base_left_side()
        
        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Curse completed in {duration:.1f}s")

    def uncurse(self):
        """Perform uncurse task - restore original workers"""
        logger.info(f"TP {self.id}: Performing uncurse task")
        start_time = time.time()
        
        with self._ensure_inside_tp():
            self.enter_TP_workers()
            time.sleep(1)
            self.deselect_all_tp_workers()
            
            # Use optimized selection if workers match known sets
            worker_set = set(self.productivity_workers)
            if WorkerSet.POZEMKA_SET.issubset(worker_set):
                self.quick_select_tp_workers_pozemka_tuye_jaye()
            elif WorkerSet.SHAMARE_SET.issubset(worker_set):
                self.quick_select_tp_workers_shamare_firewhistle_kirara()
            else:
                for worker in self.productivity_workers:
                    self.select_tp_worker_by_text_ocr(worker)
            
            self.confirm_tp_workers()
            self.is_currently_cursed = False
            self.productivity_workers.clear()
        
        self.update_execution_timestamp()
        self._schedule_curse()
        
        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Uncurse completed in {duration:.1f}s")

    @classmethod
    def _should_delay_uncurse(cls, execution_time: float, threshold: int) -> bool:
        """Check if uncurse should be delayed due to close curse tasks"""
        for task_time, _, is_curse in cls.curse_uncurse_queue:
            if is_curse and 0 < (task_time - execution_time) <= threshold:
                logger.info("Found conflicting curse task, should delay uncurse")
                return True
        return False

    @classmethod
    def _execute_task(cls, trading_post: 'TradingPost', is_curse: bool, 
                     execution_time: float, config: CursingConfig) -> bool:
        """
        Execute a curse or uncurse task
        Returns True if task was rescheduled (queue changed), False otherwise
        """
        task_type = "CURSE" if is_curse else "UNCURSE"
        logger.info(f"Executing {task_type} for TP {trading_post.id}")
        
        try:
            if is_curse:
                reach_base_left_side()
                trading_post.enter_TP()
                trading_post.curse()
                return_back_to_base_left_side()
                return False  # Curse doesn't reschedule
            else:
                # Check for conflict with upcoming curse tasks
                if cls._should_delay_uncurse(execution_time, config.curse_uncurse_conflict_threshold):
                    logger.info("Delaying uncurse, using drones instead")
                    reach_base_left_side()
                    trading_post.enter_TP()
                    trading_post.use_drones_on_tp()
                    return_back_to_base_left_side()
                    
                    # Reschedule uncurse
                    new_time = time.time() + 20
                    heapq.heappush(cls.curse_uncurse_queue, (new_time, trading_post, False))
                    logger.info(f"Uncurse rescheduled - queue changed, need to re-evaluate")
                    return True  # Queue changed, need immediate re-check
                else:
                    sleep_time = max(0, execution_time - time.time())
                    if CURRENTLY_TESTING:
                        sleep_time = 2
                    
                    if sleep_time > 0:
                        logger.info(f"Sleeping {sleep_time:.1f}s before uncurse")
                        time.sleep(sleep_time)
                    
                    reach_base_left_side()
                    trading_post.enter_TP()
                    trading_post.uncurse()
                    return_back_to_base_left_side()
                    return False  # Normal uncurse doesn't reschedule
                    
        except Exception as e:
            logger.error(f"Error executing {task_type} for TP {trading_post.id}: {e}", exc_info=True)
            return False

    @classmethod
    def initiate_cursing_protocol(cls):
        """Main loop for processing curse/uncurse tasks"""
        config = CursingConfig()
        logger.info("Cursing protocol initiated")
        
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

                # Execute if within buffer
                if time_left <= config.curse_execution_buffer:
                    heapq.heappop(cls.curse_uncurse_queue)
                    queue_changed = cls._execute_task(trading_post, is_curse, execution_time, config)
                    
                    # If queue changed (uncurse was rescheduled), immediately re-evaluate
                    # Otherwise, continue normally to next iteration
                    if queue_changed:
                        logger.info("Queue changed after task execution, re-evaluating immediately")
                    continue
                
                # Calculate sleep time based on phase
                if time_left <= config.early_wakeup:
                    # Monitoring phase - poll frequently
                    sleep_time = min(config.poll_interval, max(1, time_left - config.curse_execution_buffer))
                    IST_time, remaining_str = get_ist_time_and_remaining(execution_time)
                    logger.info(f"Monitoring - Next: [TP{trading_post.id}, {task_type}, {IST_time}] in {remaining_str}, sleeping {sleep_time}s")
                else:
                    # Deep sleep phase - sleep once until early wakeup
                    sleep_time = time_left - config.early_wakeup
                    wakeup_time = current_time + sleep_time
                    IST_execution_time, exec_remaining = get_ist_time_and_remaining(execution_time)
                    IST_wakeup_time, wakeup_remaining = get_ist_time_and_remaining(wakeup_time)
                    logger.info(f"Deep sleep - Task: [TP{trading_post.id}, {task_type}, {IST_execution_time}] in {exec_remaining}. Waking at {IST_wakeup_time}")
                
                time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Unexpected error in cursing protocol: {e}", exc_info=True)
                time.sleep(60)
                    
            except Exception as e:
                logger.error(f"Unexpected error in cursing protocol: {e}", exc_info=True)
                time.sleep(60)