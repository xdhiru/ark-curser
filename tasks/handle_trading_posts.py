from tasks.navigation import *
from utils.ocr import *
from utils.adb import *
from utils.logger import logger
from utils.time_helper import get_ist_time_and_remaining
import time
import heapq
import yaml
from typing import List, Tuple, Optional, Set, Iterable
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
    """Main handler for processing trading posts"""
    logger.info("=" * 45, "\nInitializing trading posts...", "=" * 45)
    
    reach_base_left_side()
    
    for match in find_trading_posts():
        TradingPost(match["x"], match["y"])
        reach_base()
    
    logger.info("Trading posts initialized. Starting cursing protocol...")
    TradingPost.initiate_cursing_protocol()


class WorkerConfig:
    """Centralized worker configuration with optimized lookups"""
    
    # Worker mappings: name -> (category, template_name)
    _WORKER_CONFIGS = {
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
    
    # Curse worker set - used during curse operations (with order!)
    CURSE_WORKERS = ('Proviso', 'Quartz', 'Tequila')
    
    # Predefined worker sets as tuples (preserves order for selection)
    WORKER_SETS = (
        ('Pozemka', 'Tuye', 'Jaye'),
        ('Shamare', 'Firewhistle', 'Kirara'),
        ('Shamare', 'Gummy', 'Kirara'),
        ('Exusiai', 'Lemuen', 'Underflow'),
        ('Pozemka', 'Tuye', 'MrNothing'),
        ('Exusiai', 'Lemuen', 'Kirara'),
        ('Pozemka', 'Tuye', 'Quartz'),
        ('Pozemka', 'Tuye', 'Underflow'),
        ('Exusiai', 'Lemuen', 'Jaye'),
        ('Shamare', 'Gummy', 'Midnight'),
        ('Texas', 'Lappland', 'Jaye'),
    )
    
    _CATEGORY_ICON_CACHE = {}  # Cache for category icons
    
    @classmethod
    def get_worker_configs(cls, worker_names: Iterable[str]) -> List[Tuple[str, str]]:
        """Convert worker names to (category_icon, template_name) pairs"""
        configs = []
        for name in worker_names:
            if worker_config := cls._WORKER_CONFIGS.get(name):
                category, template = worker_config
                category_icon = cls._get_category_icon(category)
                configs.append((category_icon, template))
            else:
                logger.warning(f"Worker '{name}' not found in configuration")
        return configs
    
    @classmethod
    def find_matching_worker_set(cls, worker_names: List[str]) -> Optional[Tuple[str, ...]]:
        """Find which predefined set matches the given workers (order doesn't matter)."""
        input_set = set(worker_names)  # Convert once
        
        for worker_tuple in cls.WORKER_SETS:
            if set(worker_tuple).issubset(input_set):
                return worker_tuple  # Returns tuple in predefined order
        return None
    
    @classmethod
    def _get_category_icon(cls, category: str) -> str:
        """Get category icon with caching"""
        if category not in cls._CATEGORY_ICON_CACHE:
            cls._CATEGORY_ICON_CACHE[category] = f"operator-categories-{category.lower()}-icon"
        return cls._CATEGORY_ICON_CACHE[category]


class TradingPost:
    """Represents a trading post with curse/uncurse scheduling"""
    
    _instances = []  # Use a list instead of static attribute
    _instance_count = 0
    _curse_uncurse_queue = []  # Use private attribute
    
    # Screen coordinate constants
    _WORKER_REGIONS = (
        SCREEN_COORDS['productivity_worker_1_region'],
        SCREEN_COORDS['productivity_worker_2_region'],
        SCREEN_COORDS['productivity_worker_3_region']
    )
    _ORDER_TIMER_REGION = SCREEN_COORDS['order_timer_scan_region']
    _TP_WORKERS_BUTTON = SCREEN_COORDS['tp_workers_entry_button']
    
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.id = self._get_next_id()
        self.productivity_workers = []
        self.is_cursed = False
        self.execution_time = 0
        
        self._instances.append(self)
        self._initialize()
    
    @classmethod
    def _get_next_id(cls) -> int:
        """Get next trading post ID"""
        cls._instance_count += 1
        return cls._instance_count
    
    def _initialize(self):
        """Initialize trading post state"""
        logger.debug(f"Initializing TradingPost {self.id} at ({self.x}, {self.y})")
        self._update_execution_time()
        self._schedule_curse()
        logger.debug(f"TradingPost {self.id} initialized with first curse at {self.execution_time}")
    
    @contextmanager
    def _ensure_inside_tp(self, max_retries: int = 3, interval: float = 1.0):
        """Context manager to ensure we're inside trading post"""
        for attempt in range(max_retries):
            if is_inside_tp():
                yield True
                return
            
            self._enter_trading_post()
            time.sleep(interval)
        
        logger.debug(f"Failed to confirm TP entry after {max_retries} attempts")
        yield False
    
    def _enter_trading_post(self):
        """Enter the trading post"""
        logger.debug(f"TP {self.id}: Entering trading post at ({self.x}, {self.y})")
        adb_tap(self.x, self.y)
        time.sleep(1)
        click_template("tp-entry-arrow")
        time.sleep(0.5)
    
    def _enter_workers_section(self) -> bool:
        """Enter the workers section of the trading post"""
        logger.debug(f"TP {self.id}: Entering workers section")
        time.sleep(0.5)
        adb_tap(*self._TP_WORKERS_BUTTON)
        time.sleep(1)
        return True
    
    def _scan_timer(self) -> int:
        """Scan and return the order timer in seconds"""
        time.sleep(1)
        return read_timer_from_region(*self._ORDER_TIMER_REGION)
    
    def _update_execution_time(self):
        """Update the timer and calculate next execution time"""
        with self._ensure_inside_tp() as inside_tp:
            if not inside_tp:
                logger.error(f"TP {self.id}: Cannot update execution time - not inside TP")
                return False
            self.execution_time = time.time() + self._scan_timer()
            ist_time, remaining_str = get_ist_time_and_remaining(self.execution_time)
            logger.info(f"TP {self.id}: Next execution at {ist_time} (in {remaining_str})")
    
    def _schedule_curse(self, prelay: int = 40):
        """Schedule a curse task"""
        curse_time = self.execution_time - prelay
        heapq.heappush(self._curse_uncurse_queue, (curse_time, self, True))
        logger.debug(f"TP {self.id}: Scheduled curse task at {curse_time}")
    
    def _schedule_uncurse(self, delay: int = 10):
        """Schedule an uncurse task"""
        uncurse_time = self.execution_time + delay
        heapq.heappush(self._curse_uncurse_queue, (uncurse_time, self, False))
        logger.debug(f"TP {self.id}: Scheduled uncurse task at {uncurse_time}")
    
    def _collect_orders(self):
        """Collect ready orders if available"""
        try:
            click_template("tp-order-ready-to-deliver")
            time.sleep(1)
        except Exception:
            logger.info(f"TP {self.id}: No ready orders to collect")
    
    def _save_productivity_workers(self):
        """Save current productivity workers"""
        self.productivity_workers = [
            read_text_from_region(*region) 
            for region in self._WORKER_REGIONS
        ]
        logger.info(f"TP {self.id}: Saved workers: {self.productivity_workers}")
    
    @staticmethod
    def _prepare_worker_list():
        """Prepare worker list with common sorting and filtering"""
        click_template("worker-list-sort-by-trust")
        time.sleep(0.15)
        click_template("worker-list-sort-by-skill")
        time.sleep(0.15)
    
    def _find_and_select_worker_by_text(self, worker_name: str, max_swipes: int = 40) -> bool:
        """Select a worker using OCR text recognition"""
        self._prepare_worker_list()
        
        # Reset category filters
        for icon in ["operator-categories-all-icon", 
                     "operator-categories-supporter-icon",
                     "operator-categories-all-icon"]:
            click_template(icon)
            time.sleep(0.15)
        
        for swipe_count in range(max_swipes):
            if coords := find_text_coordinates(worker_name):
                adb_tap(coords)
                return True
            
            slow_swipe_left()
            
            # Reset position periodically
            if (swipe_count + 1) % max_swipes == 0:
                for _ in range(30):
                    swipe_right()
        
        logger.warning(f"TP {self.id}: Worker '{worker_name}' not found")
        return False
    
    def _find_and_select_worker_by_template(self, template_name: str, max_swipes: int = 25) -> bool:
        """Helper to search for and tap a worker using template matching"""
        for _ in range(max_swipes):
            if coords := find_template(template_name):
                click_template(coords)
                logger.debug(f"TP {self.id}: Selected worker '{template_name}'")
                return True
            slow_swipe_left()
        
        logger.warning(f"TP {self.id}: Worker template '{template_name}' not found")
        return False
    
    def _select_workers(self, worker_names: Iterable[str]):
        """
        Universal worker selection method using worker names.
        Optimized to minimize category switching.
        """
        worker_configs = WorkerConfig.get_worker_configs(worker_names)
        self._prepare_worker_list()
        
        current_category = None
        for category_icon, worker_template in worker_configs:
            time.sleep(0.15)
            
            # Only switch category if necessary
            if category_icon != current_category:
                click_template(category_icon)
                current_category = category_icon
                time.sleep(0.15)
            
            self._find_and_select_worker_by_template(worker_template)
    
    def _deselect_all_workers(self):
        """Deselect all workers"""
        click_template("tp-workers-deselect-all-button")
    
    def _confirm_worker_selection(self):
        """Confirm worker selection"""
        click_template("tp-workers-confirm-button")
        if find_template("tp-workers-shift-confirmation-prompt"):
            click_template("tp-workers-shift-confirmation-confirm")
    
    def _use_drones(self) -> bool:
        """Use drones on the trading post"""
        logger.info(f"TP {self.id}: Using drones")
        
        with self._ensure_inside_tp() as inside_tp:
            if not inside_tp:
                logger.error(f"TP {self.id}: Not inside TP")
                return False
            
            if not find_template("tp-use-drones-icon"):
                logger.error(f"TP {self.id}: Drone icon not found")
                return False
            
            for action in [
                "tp-use-drones-icon",
                "tp-use-drones-max-icon",
                "tp-use-drones-confirm-button"
            ]:
                click_template(action)
                time.sleep(0.15)
            
            logger.info(f"TP {self.id}: Drones used successfully")
            time.sleep(1)
            return True
    
    def curse(self, use_drones: bool = False):
        """Perform curse task - assign special workers"""
        logger.info(f"TP {self.id}: Curse task (drones={use_drones})")
        start_time = time.time()
        
        with self._ensure_inside_tp() as inside_tp:
            if not inside_tp:
                logger.error(f"TP {self.id}: Cannot curse - not inside TP")
                return
            
            self._enter_workers_section()
            self._save_productivity_workers()
            self._deselect_all_workers()
            
            # Assign curse workers (in predefined order)
            self._select_workers(WorkerConfig.CURSE_WORKERS)
            self._confirm_worker_selection()
            self.is_cursed = True
            
            if use_drones:
                logger.info(f"TP {self.id}: Using drones and immediate uncurse")
                self._use_drones()
                self._collect_orders()
                self.uncurse()
            else:
                self._update_execution_time()
                self._schedule_uncurse()
        
        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Curse completed in {duration:.1f}s")
    
    def uncurse(self):
        """Perform uncurse task - restore original workers"""
        logger.info(f"TP {self.id}: Uncurse task")
        start_time = time.time()
        
        with self._ensure_inside_tp() as inside_tp:
            if not inside_tp:
                logger.error(f"TP {self.id}: Cannot uncurse - not inside TP")
                return
            
            self._enter_workers_section()
            self._deselect_all_workers()
            
            # Try to match with predefined worker set (returns ordered tuple)
            worker_tuple = WorkerConfig.find_matching_worker_set(self.productivity_workers)
            
            if worker_tuple:
                logger.info(f"TP {self.id}: Using predefined set: {worker_tuple}")
                self._select_workers(worker_tuple)  # Select in predefined order
            else:
                # Fallback to OCR-based selection
                logger.info(f"TP {self.id}: Using OCR selection")
                for worker in self.productivity_workers:
                    self._find_and_select_worker_by_text(worker)
            
            self._confirm_worker_selection()
            self.productivity_workers.clear()
            self.is_cursed = False
            self._update_execution_time()
            self._schedule_curse()
        
        duration = time.time() - start_time
        logger.info(f"TP {self.id}: Uncurse completed in {duration:.1f}s")
    
    @classmethod
    def _should_use_drones_for_curse(cls, execution_time: float) -> bool:
        """
        Check if curse should use drones due to another close curse task.
        """
        for task_time, _, is_curse in cls._curse_uncurse_queue:
            time_diff = task_time - execution_time
            if is_curse and 0 < time_diff <= CURSE_CONFLICT_THRESHOLD:
                logger.info(f"Another curse in {time_diff:.0f}s, using drones")
                return True
        return False
    
    @classmethod
    def _execute_task(cls, trading_post: 'TradingPost', is_curse: bool, scheduled_time: float):
        """Execute a curse or uncurse task"""
        task_type = "CURSE" if is_curse else "UNCURSE"
        logger.info(f"Executing {task_type} for TP {trading_post.id}")
        
        try:
            reach_base_left_side()
            
            if is_curse:
                use_drones = cls._should_use_drones_for_curse(scheduled_time)
                trading_post.curse(use_drones)
            else:
                # Wait until exact execution time for uncurse
                wait_time = max(0, scheduled_time - time.time())
                
                if CURRENTLY_TESTING:
                    wait_time = 2
                
                if wait_time > 0:
                    logger.info(f"Waiting {wait_time:.1f}s before uncurse")
                    time.sleep(wait_time)
                
                trading_post.uncurse()
                
        except Exception as e:
            logger.error(f"Error executing {task_type} for TP {trading_post.id}: {e}", exc_info=True)
    
    @classmethod
    def initiate_cursing_protocol(cls):
        """Main loop for processing curse/uncurse tasks"""
        logger.info("=" * 45)
        logger.info(f"Cursing Protocol: Buffer={CURSE_EXECUTION_BUFFER}s, Conflict={CURSE_CONFLICT_THRESHOLD}s")
        logger.info("=" * 45)
        
        while True:
            try:
                if not cls._curse_uncurse_queue:
                    logger.info("Task queue empty, checking in 60s")
                    time.sleep(60)
                    continue
                
                current_time = time.time()
                task_time, trading_post, is_curse = cls._curse_uncurse_queue[0]
                time_until_task = task_time - current_time
                
                if time_until_task <= CURSE_EXECUTION_BUFFER:
                    heapq.heappop(cls._curse_uncurse_queue)
                    cls._execute_task(trading_post, is_curse, task_time)
                    continue
                
                # Sleep until buffer time before execution
                sleep_time = time_until_task - CURSE_EXECUTION_BUFFER
                ist_time, remaining_str = get_ist_time_and_remaining(task_time)
                task_type = "CURSE" if is_curse else "UNCURSE"
                
                logger.info(f"Sleeping - Next Task: [TP{trading_post.id}, {task_type}, {ist_time}] in {remaining_str}")
                time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Error in cursing protocol: {e}", exc_info=True)
                time.sleep(60)