# 🚀 Cursor MCP 本地安装指南（不用 Docker）

完全本地安装 TouchDesigner MCP，无需 Docker。

---

## 📦 方案 A：使用 npx（推荐，最简单）

### 步骤 1：配置 Cursor MCP

找到 Cursor 的 MCP 配置文件：

**Windows**:
```
%APPDATA%\Cursor\User\globalStorage\saoudrizwan.claude-dev\settings\cline_mcp_settings.json
```

或者在 Cursor 中：
1. 打开 Settings（`Ctrl+,`）
2. 搜索 "MCP"
3. 点击 "Edit MCP Settings"

### 步骤 2：添加配置

在配置文件中添加：

```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "npx",
      "args": [
        "-y",
        "touchdesigner-mcp-server@latest",
        "--stdio",
        "--host=http://localhost",
        "--port=9980"
      ]
    }
  }
}
```

**注意**：
- `npx` 会自动下载最新版本的 `touchdesigner-mcp-server`
- `--host=http://localhost` - TouchDesigner 运行在本地
- `--port=9980` - MCP WebServer 默认端口

### 步骤 3：重启 Cursor

完全退出并重新打开 Cursor，使配置生效。

---

## 📦 方案 B：本地构建（开发模式）

如果你想修改源代码或使用本地版本：

### 步骤 1：进入项目目录并安装依赖

```bash
cd C:\Users\Admin\Desktop\touchdesigner-mcp
npm install
```

### 步骤 2：构建项目

```bash
npm run build
```

这会生成 `dist/` 目录，包含编译后的代码。

### 步骤 3：配置 Cursor 使用本地构建

在 Cursor MCP 配置文件中添加：

```json
{
  "mcpServers": {
    "touchdesigner": {
      "command": "node",
      "args": [
        "C:\\Users\\Admin\\Desktop\\touchdesigner-mcp\\dist\\cli.js",
        "--stdio",
        "--host=http://localhost",
        "--port=9980"
      ]
    }
  }
}
```

**注意**：Windows 路径需要双反斜杠 `\\`。

### 步骤 4：重启 Cursor

---

## 🎯 配置 TouchDesigner

无论用哪个方案，都需要在 TouchDesigner 中设置 MCP 服务器。

### 步骤 1：导入组件

1. 打开 TouchDesigner
2. 拖拽文件到 `/project1` 下：
   ```
   C:\Users\Admin\Desktop\what sees you\td_mcp\mcp_webserver_base.tox
   ```
3. 确保路径是 `/project1/mcp_webserver_base`

### 步骤 2：验证启动

打开 Textport（Dialogs → Textport）：

应该看到：
```
Python >> Imported mcp modules successfully
Python >> Starting MCP Web Server on port 9980...
Python >> MCP Web Server started successfully
```

---

## ✅ 测试连接

### 方法 1：使用测试脚本

```bash
cd "C:\Users\Admin\Desktop\what sees you"
python test_mcp_connection.py
```

预期输出：
```
✅ 连接成功！

📊 TouchDesigner 信息:
   版本: 2023.11760
   平台: Windows
   状态: 运行中 🟢
```

### 方法 2：在 Cursor 中直接测试

在 Cursor 的聊天中输入：

```
检查 TouchDesigner 连接状态
```

我会使用 MCP 工具自动查询。

---

## 🛠️ 故障排除

### 问题 1：Cursor 找不到 MCP 工具

**解决**：
1. 确认配置文件路径正确
2. 完全重启 Cursor（退出所有窗口）
3. 检查 TouchDesigner 的 MCP 组件是否启动

---

### 问题 2：`npx` 下载失败

**解决**：
```bash
# 手动安装全局包
npm install -g touchdesigner-mcp-server

# 然后在配置中改用全局包
"command": "touchdesigner-mcp-server"
```

---

### 问题 3：TouchDesigner 端口 9980 被占用

**检查端口**：
```bash
netstat -ano | findstr :9980
```

**解决**：
- 关闭占用端口的程序
- 或者修改端口（在 `mcp_webserver_base` 组件参数中）

---

### 问题 4：MCP 工具在 Cursor 中不显示

**检查**：
1. Cursor 的 MCP 扩展是否启用
2. 配置文件是否有语法错误（JSON 格式）
3. 查看 Cursor 的 Developer Tools（Help → Toggle Developer Tools）中的错误

---

## 📊 配置对比

| 方式 | 优点 | 缺点 | 适合 |
|------|------|------|------|
| **npx** | 自动更新、简单 | 首次慢 | 一般使用 |
| **本地构建** | 可修改代码、快 | 需要手动更新 | 开发者 |
| **Docker** | 隔离环境 | 占用资源多 | 服务器部署 |

---

## 🎉 完成后的能力

配置成功后，你可以在 Cursor 中：

### 1. 查询信息
```
"列出 TouchDesigner 中的所有 TOP 节点"
"显示 /project1 下的节点结构"
```

### 2. 创建节点
```
"创建一个 Text TOP，显示 'Hello World'"
"创建一个 UDP In DAT，端口 7000"
```

### 3. 修改参数
```
"把 text1 的文本改为 'New Text'"
"把 movie1 的播放速度设为 2.0"
```

### 4. 执行脚本
```
"执行 Python 脚本：print(op('/project1').children)"
```

### 5. 连接节点
```
"把 movie1 连接到 out1"
```

---

## 🔗 下一步

1. ✅ 安装 MCP Server（选择方案 A 或 B）
2. ✅ 配置 Cursor
3. ✅ 导入 TouchDesigner 组件
4. ✅ 测试连接
5. 🚀 开始使用！

---

## 📚 相关文档

- [DUAL_SYSTEM_SETUP.md](DUAL_SYSTEM_SETUP.md) - 完整双系统指南
- [TD_UDP_JSON_SETUP.md](TD_UDP_JSON_SETUP.md) - 摄像头数据接收
- [touchdesigner-mcp GitHub](https://github.com/8beeeaaat/touchdesigner-mcp) - 官方文档

---

**推荐使用方案 A（npx）**，最简单、最稳定！🚀







