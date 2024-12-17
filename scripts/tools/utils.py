#! -*- coding: utf-8 -*-

import time
import functools
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(levelname)s: %(message)s")
Retry_times = 3


def retry_decorator(func):
    """
    重试装饰器
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        is_success, res = True, None
        for i in range(Retry_times):
            try:
                res = func(*args, **kwargs)
            except Exception as e:
                is_success = False
                logging.error(e)
                logging.info(f"exec {func.__name__} failed {i + 1} times...")
            finally:
                if is_success:
                    break
            time.sleep(5)

        if not is_success:
            raise Exception(f"{func.__name__} still fail after try {Retry_times} times...")
        return res

    return wrapper
