import asyncio
from multiprocessing import Queue

from quart import Quart, request, jsonify, abort
from hypercorn.asyncio import serve
from hypercorn.config import Config as HypercornConfig

from astrbot.api import logger # 假设 astrbot.api.logger 可用

class PersonalAPIServer:
    def __init__(self, webhook_path: str, token: str | None, in_queue: Queue):
        self.app = Quart(__name__)
        self.webhook_path = webhook_path
        self.token = token
        self.in_queue = in_queue
        self._server_task: asyncio.Task | None = None
        self._setup_routes()

    def _setup_routes(self):
        # 错误处理
        @self.app.errorhandler(400)
        async def bad_request(e):
            return jsonify({"error": "Bad Request", "details": str(e.description if hasattr(e, 'description') else e)}), 400

        @self.app.errorhandler(403)
        async def forbidden(e):
            return jsonify({"error": "Forbidden", "details": str(e.description if hasattr(e, 'description') else e)}), 403
        
        @self.app.errorhandler(415)
        async def unsupported_media_type(e):
            return jsonify({"error": "Unsupported Media Type", "details": str(e.description if hasattr(e, 'description') else e)}), 415

        @self.app.errorhandler(500)
        async def server_error(e):
            return jsonify({"error": "Internal Server Error", "details": str(e.description if hasattr(e, 'description') else e)}), 500

        @self.app.route(self.webhook_path, methods=["POST"])
        async def handle_uptime_kuma_webhook():
            # Token Authentication
            if self.token:
                auth_header = request.headers.get("Authorization")
                expected_auth_header = f"Bearer {self.token}"
                if not auth_header or auth_header != expected_auth_header:
                    logger.warning(
                        f"来自 {request.remote_addr} 的无效或缺失令牌。"
                        f"收到: '{auth_header}', 期望: '{expected_auth_header}'"
                    )
                    abort(403, description="无效或缺失 API 令牌。")
            
            try:
                if not request.is_json:
                    logger.warning(f"从 {request.remote_addr} 收到非 JSON 请求")
                    abort(415, description="不支持的媒体类型：期望 application/json")

                data = await request.get_json()
                if not data:
                    logger.warning(f"从 {request.remote_addr} 收到空的 JSON 负载")
                    abort(400, description="空的 JSON 负载")

                notification_msg = data.get("msg")
                if notification_msg is None:
                    logger.warning(f"从 {request.remote_addr} 的负载中缺失 'msg' 字段。负载: {data}")
                    abort(400, description="JSON 负载中缺失 'msg' 字段")
                
                self.in_queue.put(str(notification_msg))
                logger.info(f"来自 {request.remote_addr} 的   消息已入队: \"{str(notification_msg)[:100]}...\"")
                
                return jsonify({"status": "queued", "message_received": str(notification_msg)[:50]}), 200

            except Exception as e:
                if hasattr(e, 'code') and isinstance(e.code, int) and e.code >= 400:
                    raise e 
                logger.error(f"处理来自 {request.remote_addr} 的   webhook 时出错: {e}", exc_info=True)
                abort(500, description="处理 webhook 时发生内部服务器错误。")

    async def start(self, host: str, port: int):
        """启动HTTP服务"""
        config = HypercornConfig()
        config.bind = [f"{host}:{port}"]
        logger.info(f"  Webhook 服务已启动于 http://{host}:{port}{self.webhook_path}")
        
        self._server_task = asyncio.create_task(serve(self.app, config))
        try:
            await self._server_task
        except asyncio.CancelledError:
            logger.info("请求关闭   Webhook 服务")
        finally:
            await self.close()

    async def close(self):
        """关闭资源"""
        if self._server_task and not self._server_task.done():
            self._server_task.cancel()
            try:
                await self._server_task
            except asyncio.CancelledError:
                logger.info("  Webhook 服务已成功关闭。")


def run_server(host: str, port: int, webhook_path: str, token: str | None, in_queue: Queue):
    """子进程入口"""
    server = PersonalAPIServer(webhook_path, token, in_queue)
    asyncio.run(server.start(host, port))
