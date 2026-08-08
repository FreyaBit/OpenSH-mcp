# 上海图书馆开放数据 MCP

把上海图书馆开放数据平台的 **97 个 webapi 接口** + 搜韵诗词库（199 万首，免 token）封装成 12 个 MCP 工具，可接入 WorkBuddy、Cursor、Claude Desktop 等任意 MCP 客户端。

<!-- mcp-name: io.github.FreyaBit/shanghai-library-open-data-mcp -->

---

## 特性

- 🧩 **12 个 MCP 工具**：覆盖家谱 / 古籍 / 碑帖 / 武康路 / 书目 / 地名志 / 红色事件 / 纪年表 / 电影 / 舆图 / 手迹 / 人名库等 97 个官方接口 + 搜韵诗词
- 🔑 **密钥由使用者提供**：通过环境变量 `SLC_API_KEY` 或工具参数 `key` 传入，代码不内置任何密钥
- 🐍 **零第三方依赖**：仅用 Python 标准库（urllib + json），无需 `pip install`
- 🎵 **AIGC 歌词素材**：`souyun_poem` 免 token 检索 199 万首诗词（按作者/标题/诗句/朝代/体裁/韵部），`souyun_rhyme` / `souyun_couplet` 提供韵典和对仗词汇
- 📚 **RAG 骨架**：`rag_kb.py` 纯标准库 TF-IDF 知识库，可离线灌入官方 ZIP 数据

## 工具总览

| 工具 | 说明 | 需要 Key |
|---|---|---|
| `slc_endpoints` | 列出全部 97 个接口（id/家族/路径/参数），发现能力 | ❌ |
| `slc_api` | 通用分发器：调用任意 webapi 接口 | ✅ |
| `slc_era` | 中国历史纪年表：朝代/年号 ↔ 公元年 | ✅ |
| `slc_jiapu` | 家谱谱目检索 | ✅ |
| `slc_building` | 武康路历史建筑检索 | ✅ |
| `slc_red_event` | 红色旅游/历史事件检索 | ✅ |
| `slc_raw` | 任意 data1 路径 GET 兜底调用 | ✅ |
| `slc_datasets` / `slc_sparql` | 数据集总览 / SPARQL 说明 | ❌ |
| `souyun_poem` | 搜韵诗词检索（199 万首，免 token） | ❌ |
| `souyun_rhyme` | 韵典：查字所属韵部、典故、诗例 | ❌ |
| `souyun_couplet` | 对仗词汇 | ❌ |

> 接口家族：近代城市文化(20)、古籍循证(15)、国漫革命文献(7)、武康路历史(7)、纪年表关联数据(5)、韬奋纪念馆(4)、书目数据(4)、家谱(4)、地名纪年(4)、竞赛PDF文献(3)、知识图谱人物(2)、文化总库机构(2)、舆图(2)、手迹(2)、红色旅游事件(2)、地名志(2)、纪年(2)、人名规范库(1)、机构名录(1)、其他(8)。

## 快速开始

### 本地 stdio 接入

```bash
# 1. 克隆仓库
git clone https://github.com/FreyaBit/OpenSH-mcp.git
cd OpenSH-mcp

# 2. 设置你的 APIKey（在上海图书馆开放数据平台获取）
export SLC_API_KEY='你的上图书APIKey'    # macOS/Linux
# $env:SLC_API_KEY='你的上图书APIKey'    # Windows PowerShell

# 3. 运行端到端自测
python3 tests/test_stdio.py
```

在你的 MCP 客户端里配置 stdio 服务：

```json
{
  "mcpServers": {
    "上海图书馆开放数据": {
      "command": "python3",
      "args": ["/绝对路径/slc_mcp_server.py"],
      "env": { "SLC_API_KEY": "你的上图书APIKey" }
    }
  }
}
```

### 通过 PyPI / uvx 安装（推荐，跨客户端通用）

发布到 PyPI 后，任意支持 MCP 的客户端都能用一条命令拉起，无需克隆仓库：

```bash
uvx shanghai-library-open-data-mcp              # 本地 stdio（默认）
uvx shanghai-library-open-data-mcp --transport http --port 8080      # Streamable HTTP 远程（进阶可选）
```

客户端配置只需：`command: uvx, args: ["shanghai-library-open-data-mcp"]`。

### Streamable HTTP 传输（进阶，可选）

除 stdio 外，本服务原生支持 Streamable HTTP（`slc_mcp_http.py`，纯标准库实现）：
- `POST /mcp` 处理 JSON-RPC（initialize 时签发 `Mcp-Session-Id`，通知类返回 202）
- `GET /mcp` 提供 SSE 流
- 已开启 CORS，便于网页端 / 远程网络调用

> 适合网页版 AI、手机端，或多人共用同一服务；需自行把服务跑在可访问的地址上。个人在编辑器本地使用，stdio 已足够，无需此模式。

## APIKey 说明

- 上海图书馆开放数据平台要求**每个调用者使用自己的 APIKey**（在平台注册后获取）。
- 本仓库**不包含任何 Key**，也不记录、不收集你的 Key。
- Key 读取优先级：**工具参数 `key`** > 环境变量 `SLC_API_KEY`。
- 调用需要 Key 的工具时，把 Key 放在工具参数里：

```json
{ "endpoint": "building_list", "params": { "freetext": "武康路" }, "key": "你的上图书APIKey" }
```

- 免 Key 工具（`souyun_poem` / `souyun_rhyme` / `souyun_couplet` / `slc_endpoints`）开箱即用。
- ⚠️ 请勿把你的 Key 配置到公开服务的环境变量里（等于公开给所有调用者）。

## 目录结构

```
OpenSH-mcp/
├── README.md                 # 本文件
├── pyproject.toml            # PyPI 打包配置（uvx 入口）
├── slc_mcp_server.py         # MCP 服务主程序（stdio，纯标准库）
├── slc_mcp_http.py           # Streamable HTTP 传输层（纯标准库，进阶可选）
├── slc_endpoints.py          # 97 个 webapi 接口注册表（自动生成）
├── gen_endpoints.py          # 接口注册表生成器（从官方 API 文档解析）
├── souyun_poem.py            # 搜韵诗词/韵典/对仗采集（免 token）
├── rag_kb.py                 # RAG 知识库骨架（纯标准库 TF-IDF）
├── mcp.json.template         # MCP 客户端配置模板（不含 Key）
└── tests/                    # 测试（从环境变量读 Key，缺失会提示）
    ├── test_stdio.py         #   stdio 端到端（协议 + 真实调用）
    ├── test_live.py          #   handler 级实测（GET/POST/搜韵）
    └── test_mcp.py           #   协议冒烟测试
```

## 数据源与致谢

- **上海图书馆开放数据平台（官方）**：https://opendata.library.sh.cn/opendata/
  衷心感谢**上海图书馆官方**开放数据平台提供权威、丰富且持续维护的历史文献与文脉数据接口。本项目的全部核心数据能力均建立在上海图书馆开放数据之上，若无官方的开放与授权，本项目无从实现。
- **搜韵诗词**：https://api.sou-yun.cn/open （199 万首诗词，免 token）
- 本仓库接口版权归各数据方所有，使用请遵守各平台开放数据的使用条款。

## License

[MIT](LICENSE)
