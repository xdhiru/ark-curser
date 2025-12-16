"""
Task automation modules for the cursingbot project.
"""

from .navigation import (
    click_template,
    find_and_click_text,
    is_home_screen,
    is_base,
    is_inside_tp,
    reach_home_screen,
    reach_base,
    reach_base_left_side,
    find_trading_posts,
    find_factories,
    enter_base_overview,
    wait_for_template,
    retry_operation,
    ensure_at_location
)
from .handle_trading_posts import handle_trading_posts, TradingPost, WorkerConfig

__all__ = [
    # Navigation
    'click_template',
    'find_and_click_text',
    'is_home_screen',
    'is_base',
    'is_inside_tp',
    'reach_home_screen',
    'reach_base',
    'reach_base_left_side',
    'find_trading_posts',
    'find_factories',
    'enter_base_overview',
    'wait_for_template',
    'retry_operation',
    'ensure_at_location',
    
    # Trading Posts
    'handle_trading_posts',
    'TradingPost',
    'WorkerConfig',
]