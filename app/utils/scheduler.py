import logging
from .sync_task import sync_data

logger = logging.getLogger(__name__)

def init_scheduler():
    """初始化定时任务调度器"""
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.interval import IntervalTrigger
    
    scheduler = BackgroundScheduler()
    
    # 每30分钟执行一次同步任务
    scheduler.add_job(
        sync_data,
        trigger=IntervalTrigger(minutes=30),
        id='sync_data_job',
        name='Sync data from external system',
        replace_existing=True
    )
    
    try:
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise 