import logging
import time

from celery import shared_task

logger = logging.getLogger("airport_service_api")


@shared_task
def notify_order_created(order_id, user_email):
    logger.info(f"START: Background task for Order #{order_id}")
    # implement later
    time.sleep(5)
    logger.info(f"DONE: User {user_email} notified about Order #{order_id}")
