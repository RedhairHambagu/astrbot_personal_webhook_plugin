# Uptime Kuma Webhook for AstrBot

参考<https://github.com/Raven95676/astrbot_plugin_push_lite>开发，允许您通过 Webhook 从 Uptime Kuma 接收监控状态通知，并将这些通知推送到指定的 AstrBot 用户或群组。
## 功能

-   通过一个可配置的 HTTP(S) 端点接收来自 Uptime Kuma 的 Webhook 通知。
-   支持通过 Bearer Token 对传入的 Webhook 请求进行身份验证。
-   将格式化的通知消息推送到一个或多个在 AstrBot 中配置的用户或群组 ID (`target_umo`)。

## 安装

1.  **通过插件市场安装：** 在 AstrBot 的插件市场搜索 "Uptime Kuma Webhook" (或类似名称) 并安装。
2.  **手动安装：** 下载插件的压缩包，然后在 AstrBot 的 Web 控制台中上传并安装。

## AstrBot 插件配置

插件安装完成后，在 AstrBot 的 Web 控制台中找到 "Uptime Kuma Webhook" 插件并进行配置：

-   **API 服务器设置 (API Settings):**
    -   **监听主机 (Host):** 插件内建 API 服务器监听的主机地址。默认为 `0.0.0.0`。
    -   **监听端口 (Port):** 插件内建 API 服务器监听的端口。例如 `9967`。请确保此端口未被其他应用占用，并且在防火墙/安全组中已开放。
    -   **Webhook 路径 (Webhook Path):** Uptime Kuma 将向其发送 POST 请求的路径。例如，如果设置为 `/uptime`，则完整的 Webhook URL 将是 `http://<服务器IP>:<端口>/uptime`。默认为 `/`。
    -   **API 令牌 (Token):** 一个**必须设置**的安全令牌字符串。Uptime Kuma 在发送请求时需要通过 HTTP Header 提供此令牌以进行身份验证。
-   **目标 UMO (Target UMO):**
    -   一个包含 AstrBot 用户 ID 和/或群组 ID 的列表。插件会将收到的通知发送给此列表中的所有目标。您可以使用 AstrBot 的 `/sid` 命令获取这些 ID。例如：`["user_xxxxxxxx", "group_yyyyyyyy"]`。

保存配置后，插件会自动应用新的设置（可能需要重新启用插件或重启 AstrBot，具体取决于 AstrBot 的行为）。

## Uptime Kuma 设置
![image](https://github.com/user-attachments/assets/2dc20b07-e090-4c4c-a8e2-6f5b60e82f95)
范例如上图
在 Uptime Kuma 中，为您的监控项添加或编辑通知设置：

1.  **通知类型 (Notification Type):** 选择 `Webhook`。
2.  **显示名称 (Display Name):** 给这个通知起一个容易识别的名称，例如 `AstrBot Webhook`。
3.  **Post URL:**
    填写插件 API 服务器的完整 URL。它由您在 AstrBot 插件配置中设置的 `监听主机` (通常是运行 AstrBot 的服务器的 IP 地址或域名)、`监听端口` 和 `Webhook 路径` 组成。
    例如：`http://192.168.44.9:9967/` (如果 `Webhook 路径` 是 `/`)
4.  **请求体 (Request Body):**
    选择预设 `application/json`。
5.  **额外 Header (Additional Headers):**
    启用此选项，并添加一个 JSON 对象来定义请求头。您**必须**添加 `Authorization` Header，其值为 `Bearer` 加上您在 AstrBot 插件配置中设置的 `API 令牌`。

    **Header JSON 示例:**
    ```json
    {
      "Authorization": "Bearer YOUR_CONFIGURED_TOKEN"
    }
    ```
    请将 `YOUR_CONFIGURED_TOKEN` 替换为您在 AstrBot 插件配置中实际设置的 `API 令牌` 值。

6.  **保存** Uptime Kuma 的通知设置。

现在，当 Uptime Kuma 的监控项状态发生变化时，它应该会向您的 AstrBot 插件发送通知。
