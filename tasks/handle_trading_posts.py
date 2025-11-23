from tasks.navigation import *
from utils.ocr import *
from utils.adb import *
from utils.logger import logger
from utils.time_helper import get_ist_time_and_remaining
import time
import heapq  # To maintain a sorted job queue based on the timer
import yaml

# Load configuration
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)
screen_coords = config.get('screen_coordinates', {})

def handle_trading_posts():

    tpMatchesList=find_trading_posts()
        
    for match in tpMatchesList:
        TradingPost(match["x"],match["y"])
        logger.info("Trading post handled, returning to base and sleeping 5 seconds")
        return_back_to_base_left_side()
        time.sleep(5)

    TradingPost.initiate_cursing_protocol()

class TradingPost:
    TPcount = 0
    all_trading_posts = []

    def __init__(self, x, y, timer=0):
        self.x = x
        self.y = y
        TradingPost.TPcount += 1
        self.productivity_workers=[]
        self.id = TradingPost.TPcount
        self.is_currently_cursed=False
        TradingPost.all_trading_posts.append(self)
        self.execution_timestamp = 0
        self.update_execution_timestamp()
        self.add_to_curse()
        
    def __del__(self):
        TradingPost.all_trading_posts.remove(self)
        
    def __repr__(self):
        return f"TradingPost({self.id}, x={self.x}, y={self.y})"
    
    def enter_TP(self):
        adb_tap(self.x,self.y)
        time.sleep(1)
        click_template("tp-entry-arrow")
        time.sleep(1)

    def scan_timer(self):
        time.sleep(1)
        region = screen_coords['order_timer_scan_region']
        return read_timer_from_region(*region) #order timer in seconds (no delay)

    def enter_TP_workers(self):
        time.sleep(1)
        if not find_template("order-efficiency-screen"):
            logger.warning(f"TP {self.id}: Not inside trading post, cannot open TP workers")
            return False
        x, y = screen_coords['tp_workers_entry_button']
        adb_tap(x, y)
        logger.debug(f"TP {self.id}: Entered TP workers successfully")
        time.sleep(1)
        return True

    def update_execution_timestamp(self):
        """Updates the timer and re-adds to the job queue to maintain order"""
        if not find_template("check-if-inside-tp"):
            self.enter_TP()
        order_timer_seconds=self.scan_timer()
        logger.debug(f"TP {self.id}: Scanned timer - {order_timer_seconds} seconds")
        self.execution_timestamp=time.time()+order_timer_seconds
        logger.debug(f"TP {self.id}: Set execution timestamp to {self.execution_timestamp}")

    def add_to_curse(self):
        heapq.heappush(self.__class__.curse_uncurse_queue, (self.execution_timestamp-40, self, True))  # Push to curse, tuple (execution_timestamp, TradingPost object, do_curse_flag)
        logger.debug(f"TP {self.id}: Added curse task to queue (execution: {self.execution_timestamp-40})")

    def add_to_uncurse(self):
        heapq.heappush(self.__class__.curse_uncurse_queue, (self.execution_timestamp+5, self, False)) # Push to uncurse, tuple (execution_timestamp, TradingPost object, do_curse_flag)
        logger.debug(f"TP {self.id}: Added uncurse task to queue (execution: {self.execution_timestamp+5})")

    def collect_orders(self):
        time.sleep(1.5)
        if find_template("tp-order-ready-to-deliver"):
            click_template("tp-order-ready-to-deliver")
        return

    def save_tp_productivity_workers(self):
        r1 = screen_coords['productivity_worker_1_region']
        r2 = screen_coords['productivity_worker_2_region']
        r3 = screen_coords['productivity_worker_3_region']
        worker1=read_text_from_region(*r1)
        worker2=read_text_from_region(*r2)
        worker3=read_text_from_region(*r3)
        self.productivity_workers=[worker1,worker2,worker3]
        logger.debug(f"TP {self.id}: Saved productivity workers: {self.productivity_workers}")

    def select_tp_worker(self, tp_worker, max_slow_swipe_left_count=20, reset_to_left_swipe_count=5):
        click_template("worker-list-sort-by-trust")
        time.sleep(0.25)
        click_template("worker-list-sort-by-skill")
        time.sleep(0.25)
        click_template("operator-categories-all-icon")
        time.sleep(0.25)
        click_template("operator-categories-supporter-icon")
        time.sleep(0.25)
        click_template("operator-categories-all-icon")
        time.sleep(0.25)
        slow_swipe_left_count=0
        while True:
            worker_coords = find_text_coordinates(tp_worker)
            if worker_coords:
                adb_tap(worker_coords)
                break
            slow_swipe_left()
            slow_swipe_left_count+=1
            if slow_swipe_left_count==max_slow_swipe_left_count:
                slow_swipe_left_count=0
                for _ in range(reset_to_left_swipe_count):
                    swipe_right()
    
    def find_and_tap_worker(self, worker_name, timeout_swipes=25):
        """Helper to search for and tap a worker"""
        swipe_count = 0
        while swipe_count < timeout_swipes:
            worker_coords = find_text_coordinates(worker_name)
            if worker_coords:
                adb_tap(worker_coords)
                logger.debug(f"TP {self.id}: Found and tapped worker '{worker_name}'")
                return True
            slow_swipe_left()
            swipe_count += 1
        logger.warning(f"TP {self.id}: Could not find worker '{worker_name}' after {timeout_swipes} swipes")
        return False

    def select_tp_workers_proviso_quartz_tequila(self):
        click_template("worker-list-sort-by-trust")
        time.sleep(0.25)
        click_template("worker-list-sort-by-skill")
        time.sleep(0.25)
        
        # Supporter category
        click_template("operator-categories-supporter-icon")
        time.sleep(0.25)
        self.find_and_tap_worker("Proviso")
        
        # Guard category
        time.sleep(0.25)
        click_template("operator-categories-guard-icon")
        time.sleep(0.25)
        self.find_and_tap_worker("Quartz")
        time.sleep(0.25)
        self.find_and_tap_worker("Tequila")
        time.sleep(0.25)


    def deselect_all_tp_workers(self):
        click_template("tp-workers-deselect-all-button")

    def confirm_tp_workers(self):
        if find_template("tp-workers-shift-confirmation-prompt"):
            click_template("tp-workers-shift-confirmation-confirm")
        else:
            click_template("tp-workers-confirm-button")

    def curse(self):
        """Performs a curse task, needs to reach the base left side beforehand"""
        logger.info(f"TP {self.id}: Performing curse task at ({self.x}, {self.y})")
        
        # Curse code goes here
        self.enter_TP()
        self.enter_TP_workers()
        time.sleep(2)
        
        self.save_tp_productivity_workers()
        self.deselect_all_tp_workers()
        self.select_tp_workers_proviso_quartz_tequila()
        self.confirm_tp_workers()
        self.is_currently_cursed=True

        self.update_execution_timestamp() # Calculate new time after assigned curse prov teq
        self.add_to_uncurse() # Add an uncurse task for this timestamp
        return_back_to_base_left_side()
        logger.debug(f"TP {self.id}: Curse task completed")
        

    def uncurse(self):
        """Performs a uncurse task"""
        logger.info(f"TP {self.id}: Performing uncurse task at ({self.x}, {self.y})")
        
        # unCurse code goes here
        self.enter_TP()
        time.sleep(1)
        if not find_template("order-efficiency-screen"):
            logger.warning(f"TP {self.id}: Not inside trading post, retrying entry")
            self.enter_TP()
        self.enter_TP_workers()
        time.sleep(2)
        
        self.deselect_all_tp_workers()
        for tp_worker in self.productivity_workers:
            self.select_tp_worker(tp_worker)
        self.confirm_tp_workers()
        self.is_currently_cursed=False
        self.productivity_workers=[]
        
        self.update_execution_timestamp() # Calculate new time after unassigned prov teq
        self.add_to_curse()
        return_back_to_base_left_side()
        logger.debug(f"TP {self.id}: Uncurse task completed")
        
        
    # Class-level job queue
    curse_uncurse_queue = []

    # old code when the curse priority over uncurse task was not implemented, and may have flaw in sleep logic, which may miss a task by sleeping longer.
    #
    # @classmethod
    # def initiate_cursing_protocol(cls):
    #     while True:
    #         if cls.curse_uncurse_queue:
    #             execution_time, trading_post, curse_flag = cls.curse_uncurse_queue[0]
    #             time_left = execution_time - time.time()

    #             if time_left <= 60:
    #                 print(f"Performing {cls.curse_uncurse_queue[0]}")
    #                 heapq.heappop(cls.curse_uncurse_queue)
    #                 if curse_flag:
    #                     reach_base_left_side()
    #                     trading_post.curse()
    #                 else:
    #                     time.sleep(60)  # Could this be reduced?
    #                     reach_base_left_side()
    #                     trading_post.uncurse()
                    
    #                 # Continue to next iteration immediately after operation
    #                 continue
    #             else:
    #                 # Dynamic sleep based on time_left
    #                 sleep_time = min(30, max(1, time_left - 60 - 60))  # Wake up 60 seconds early
    #                 IST_execution_time, remaining_time_str = get_ist_time_and_remaining(execution_time)
    #                 print(f"Next task at {IST_execution_time} in {remaining_time_str}. Sleeping for {sleep_time:.1f}s...")
    #                 time.sleep(sleep_time)
    #         else:
    #             # Longer sleep when queue is empty to reduce resource usage
    #             print("Queue is empty, sleeping for 60 seconds...")
    #             time.sleep(60)


    @classmethod
    def initiate_cursing_protocol(cls):
        # CONSTRAINTS:
        # EARLY_WAKEUP >= MAX_SLEEP (to prevent oversleeping past monitoring phase)
        # POLL_INTERVAL <= CURSE_EXECUTION_BUFFER (so we poll frequently enough before execution)
        # CURSE_UNCRSE_CONFLICT_THRESHOLD can be any value (independent logic)
        
        EARLY_WAKEUP = 300        # 7 minutes - Must be >= MAX_SLEEP
        MAX_SLEEP = 300           # 5 minutes - Must be <= EARLY_WAKEUP  
        POLL_INTERVAL = 30        # 30 seconds - Should be <= CURSE_EXECUTION_BUFFER
        CURSE_EXECUTION_BUFFER = 30  # 60 seconds - Should be >= POLL_INTERVAL
        CURSE_UNCURSE_CONFLICT_THRESHOLD = 90  # 90 seconds - Independent, can be any value
        
        logger.info("Cursing protocol initiated")
        while True:
            try:
                if not cls.curse_uncurse_queue:
                    logger.debug("Task queue empty, checking again in 60s")
                    time.sleep(60)
                    continue
                
                current_time = time.time()
                execution_time, trading_post, curse_flag = cls.curse_uncurse_queue[0]
                time_left = execution_time - current_time

                if time_left <= CURSE_EXECUTION_BUFFER:
                    # Execute task
                    task_type = "CURSE" if curse_flag else "UNCURSE"
                    logger.info(f"Executing {task_type} task for TP {trading_post.id}")
                    heapq.heappop(cls.curse_uncurse_queue)
                    
                    try:
                        if curse_flag:
                            reach_base_left_side()
                            trading_post.curse()
                        else:
                            # For uncurse, check if we should delay due to upcoming curse tasks
                            # that are scheduled very close AFTER this uncurse task
                            should_delay = False
                            for task in cls.curse_uncurse_queue:
                                task_exec_time, _, task_curse_flag = task
                                if (task_curse_flag and 
                                    task_exec_time > execution_time and  # Curse task is AFTER uncurse
                                    task_exec_time - execution_time <= CURSE_UNCURSE_CONFLICT_THRESHOLD):
                                    should_delay = True
                                    logger.debug(f"Found conflicting curse task too close to uncurse, rescheduling")
                                    break
                            
                            if should_delay:
                                logger.debug("Rescheduling uncurse due to close curse task")
                                # Reschedule uncurse to happen after the curse task
                                new_time = current_time + CURSE_UNCURSE_CONFLICT_THRESHOLD + 5
                                heapq.heappush(cls.curse_uncurse_queue, (new_time, trading_post, curse_flag))
                            else:
                                # Sleep until actual execution time for uncurse
                                sleep_time = max(0, execution_time - current_time)
                                if sleep_time > 0:
                                    logger.debug(f"Sleeping {sleep_time:.1f}s before uncurse")
                                    time.sleep(sleep_time)
                                reach_base_left_side()
                                trading_post.uncurse()
                                
                    except Exception as e:
                        logger.error(f"Error performing task for TP {trading_post.id}: {e}", exc_info=True)
                        # Optionally reschedule failed task with backoff
                    
                    continue
                    
                elif time_left <= EARLY_WAKEUP:
                    # Monitoring phase
                    sleep_time = min(POLL_INTERVAL, max(1, time_left - CURSE_EXECUTION_BUFFER))
                    IST_time, remaining_str = get_ist_time_and_remaining(execution_time)
                    logger.debug(f"Monitoring - Next task at {IST_time} (in {remaining_str}), sleeping {sleep_time}s")
                    time.sleep(sleep_time)
                    
                else:
                    # Deep sleep phase
                    sleep_until_early_wakeup = time_left - EARLY_WAKEUP
                    sleep_time = min(MAX_SLEEP, max(1, sleep_until_early_wakeup))
                    sleep_time = min(sleep_time, sleep_until_early_wakeup)
                    
                    IST_time, remaining_str = get_ist_time_and_remaining(execution_time)
                    logger.debug(f"Deep sleep - Task at {IST_time} (in {remaining_str}), sleeping {sleep_time}s")
                    time.sleep(sleep_time)
                    
            except Exception as e:
                logger.error(f"Unexpected error in cursing protocol: {e}", exc_info=True)
                time.sleep(60)
