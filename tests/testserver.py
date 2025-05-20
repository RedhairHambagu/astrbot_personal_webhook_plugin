#!/usr/bin/env python3
# filename: kuma_receiver.py
from http.server import BaseHTTPRequestHandler, HTTPServer
import json, logging

class KumaHandler(BaseHTTPRequestHandler):
    # 只处理 POST（Uptime Kuma 默认用 POST 调用 Webhook）
    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(length)

        # 打印 header & body
        logging.info("=== 请求路径: %s ===", self.path)
        logging.info("Headers: %s", dict(self.headers))

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = raw.decode(errors="replace")  # 可能是纯文本
        logging.info("Body   : %s\n", payload)

        # 回复 200，JSON 随意
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"received"}')

    # 去掉默认的超长 console access 日志
    def log_message(self, *args):
        return

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s"
    )
    server = HTTPServer(("0.0.0.0", 4000), KumaHandler)
    logging.info("Listening on http://0.0.0.0:4000")
    server.serve_forever()
