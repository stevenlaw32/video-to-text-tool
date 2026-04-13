"""
日志流管理器 - 用于实时传输处理日志到前端
"""
import queue
import threading

class LogStream:
    """单例模式的日志流管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance.log_queue = queue.Queue()
                    cls._instance.active = False
        return cls._instance
    
    def start(self):
        """开始新的日志会话"""
        # 清空队列
        while not self.log_queue.empty():
            try:
                self.log_queue.get_nowait()
            except queue.Empty:
                break
        self.active = True
    
    def stop(self):
        """结束日志会话"""
        self.active = False
    
    def add_log(self, message, log_type='info'):
        """添加日志消息"""
        if self.active:
            self.log_queue.put({
                'message': message,
                'type': log_type
            })
    
    def get_logs(self, timeout=1):
        """获取日志（生成器）"""
        while self.active or not self.log_queue.empty():
            try:
                log = self.log_queue.get(timeout=timeout)
                yield log
            except queue.Empty:
                if not self.active:
                    break
                continue

# 全局日志流实例
log_stream = LogStream()
