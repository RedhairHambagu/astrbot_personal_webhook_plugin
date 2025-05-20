import asyncio
from multiprocessing import Process, Queue

import astrbot.core.message.components as Comp
from astrbot.api import logger
from astrbot.api.star import Context, Star, register
from astrbot.core.config.astrbot_config import AstrBotConfig
from astrbot.core.message.message_event_result import MessageChain

from .api import run_server # type: ignore

@register("astrbot_uptime_kuma_webhook_plugin", "RC-CHN", "通过 Webhook 接收 Uptime Kuma 的监控通知并推送到 AstrBot", "0.1.0") # 与 metadata.yaml 一致
class UptimeKumaWebhook(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.in_queue: Queue | None = None
        self.process: Process | None = None
        self._running = False
        self.target_umos: list[str] = [] # 改为列表

    async def initialize(self):
        """初始化插件"""
        api_conf = self.config.get("api", {})
        # 确保读取到的是列表，如果不是或者为空，则记录错误
        target_umo_config = self.config.get("target_umo")
        if isinstance(target_umo_config, list) and target_umo_config:
            self.target_umos = target_umo_config
        else:
            logger.error("Uptime Kuma Webhook: 配置中的 'target_umo' 不是一个有效的列表或为空，插件无法发送消息。")
            return

        host = api_conf.get("host", "0.0.0.0")
        port = api_conf.get("port", 9967)
        webhook_path = api_conf.get("webhook_path", "/")
        token = api_conf.get("token")

        # self.target_umos 的检查已在上面完成

        if not token:
            logger.error("Uptime Kuma Webhook: 配置中未找到 API 'token'，API 服务不会启动。请配置令牌以确保安全。")
            return

        self.in_queue = Queue()
        self.process = Process(
            target=run_server,
            args=(
                host,
                port,
                webhook_path,
                token,
                self.in_queue,
            ),
            daemon=True,
        )
        self.process.start()
        self._running = True
        asyncio.create_task(self._process_messages())
        logger.info("Uptime Kuma Webhook 插件已初始化并启动 API 服务。")

    async def _process_messages(self):
        """处理来自子进程的消息"""
        if not self.in_queue or not self.target_umos:
            logger.error("Uptime Kuma Webhook: 消息队列或 target_umos 未初始化/为空，无法处理消息。")
            return

        while self._running:
            try:
                # 使用 asyncio.to_thread 来在 executor 中运行阻塞的 get 调用
                # 或者确保 Queue.get() 是非阻塞的或有超时
                notification_msg = await asyncio.get_event_loop().run_in_executor(
                    None, self.in_queue.get
                )
                
                if notification_msg is None and not self._running: # 可能是终止信号
                    break

                if isinstance(notification_msg, str):
                    logger.info(f"正在处理 Uptime Kuma 消息: \"{notification_msg[:100]}...\"")
                    prefixed_msg = f"[Uptime Kuma] {notification_msg}"
                    chain = MessageChain(chain=[Comp.Plain(prefixed_msg)])
                    for umo in self.target_umos:
                        try:
                            await self.context.send_message(umo, chain)
                            logger.info(f"Uptime Kuma 消息已发送至 {umo}")
                        except Exception as send_error:
                            logger.error(f"Uptime Kuma 消息发送至 {umo} 失败: {send_error}", exc_info=True)
                else:
                    logger.warning(f"从队列中收到意外的消息类型: {type(notification_msg)}")

            except EOFError: # 当队列的另一端关闭时，可能会发生这种情况
                logger.info("Uptime Kuma Webhook: 消息队列已关闭。")
                self._running = False # 确保循环终止
                break
            except Exception as e:
                logger.error(f"Uptime Kuma Webhook: 处理消息时发生错误: {e}", exc_info=True)
                # 根据错误类型决定是否继续循环
                await asyncio.sleep(1) # 避免快速失败循环

    async def terminate(self):
        """停止插件"""
        logger.info("正在终止 Uptime Kuma Webhook 插件...")
        self._running = False
        
        # 尝试向队列发送一个特殊值以唤醒 _process_messages 中的 get()
        if self.in_queue:
            try:
                self.in_queue.put_nowait(None) 
            except Exception:
                pass # 忽略队列已满或关闭的错误

        if self.process and self.process.is_alive():
            logger.info("正在终止 API 服务进程...")
            self.process.terminate() # 发送 SIGTERM
            try:
                # 等待进程终止，设置超时
                await asyncio.get_event_loop().run_in_executor(None, self.process.join, 5)
                if self.process.is_alive():
                    logger.warning("API 服务进程在5秒后仍未终止，将强制终止。")
                    self.process.kill() # 发送 SIGKILL
                    await asyncio.get_event_loop().run_in_executor(None, self.process.join, 1)
            except Exception as e:
                logger.error(f"终止 API 进程时发生错误: {e}")
        
        if self.in_queue:
            while not self.in_queue.empty():
                try:
                    self.in_queue.get_nowait()
                except Exception:
                    break # 队列为空或发生其他错误
            self.in_queue.close()
            self.in_queue.join_thread() # 等待后台线程完成

        logger.info("Uptime Kuma Webhook 插件已终止。")
