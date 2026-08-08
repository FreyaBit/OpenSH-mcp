# ModelScope 魔搭 MCP 广场 提交材料（上海图书馆开放数据 MCP）

ModelScope MCP 广场是国内 Cherry Studio / 魔搭生态的关键入口。提交方式：到 https://modelscope.cn/mcp 创建 MCP，选择「自定义创建」或「从 GitHub 仓库导入」，填以下信息即可。

## 填写字段（直接复制）

- **名称（name）**：`shanghai-library-open-data-mcp`
- **展示名（displayName）**：`上海图书馆开放数据 MCP`
- **简介（description）**：上海图书馆开放数据（纪年/家谱/建筑/红色事件/古籍循证/书目/诗词/戏单等 99 个接口 + 搜韵诗词）的 Model Context Protocol 服务。stdio + Streamable HTTP 双传输，纯标准库零依赖，APIKey 由使用者自行提供。
- **仓库地址**：`https://github.com/FreyaBit/OpenSH-mcp`
- **PyPI 包**：`shanghai-library-open-data-mcp==1.3.2`
- **标签（tags）**：`mcp` `上海图书馆` `开放数据` `古籍` `家谱` `诗词` `知识库` `stdio` `http`
- **作者 / 组织**：`FreyaBit`
- **许可证**：`MIT`

## 启动配置（自定义创建时粘贴到「配置」）

stdio 方式（推荐，用户本机用 `uvx` 拉起）：

```json
{
  "mcpServers": {
    "shanghai-library-open-data-mcp": {
      "command": "uvx",
      "args": ["shanghai-library-open-data-mcp"],
      "env": {
        "SLC_API_KEY": "你的上海图书馆开放数据 APIKey（可选，不填则调用时传 key 参数）"
      }
    }
  }
}
```

Streamable HTTP 方式（若你已按本目录 `Dockerfile` 自托管并暴露 `/mcp`）：

```json
{
  "mcpServers": {
    "shanghai-library-open-data-mcp": {
      "url": "http://<你的域名>:8080/mcp"
    }
  }
}
```

## 提交步骤

1. 打开 https://modelscope.cn/mcp ，登录后点「创建 MCP」。
2. 选「自定义创建」→ 粘贴上方名称/简介/标签；或选「从 GitHub 仓库导入」直接填仓库地址。
3. 启动方式选 `stdio`，把上面的 stdio 配置 JSON 粘进「配置」框。
4. 提交后等待审核（通常较快），上线后即可在 Cherry Studio 等国内客户端一键添加。
