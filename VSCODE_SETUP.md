# VS Code 调试指南

本文档将指导你如何在本地克隆本仓库，并使用 VS Code 对项目进行调试。

## 1. 克隆仓库到本地

1. 打开终端（Windows 推荐使用 PowerShell）。
2. 选择一个用于存放代码的目录，例如 `~/Projects` 或 `D:\Projects`。
3. 运行以下命令克隆仓库：

   ```bash
   git clone https://github.com/your-org-or-user/testJDsALES.git
   ```

4. 进入项目目录：

   ```bash
   cd testJDsALES
   ```

> 如果仓库位于私有网络或企业 Git 服务器，请将上述地址替换为实际的仓库 URL，并根据提示配置访问凭证。

## 2. 使用 VS Code 打开项目

1. 启动 VS Code。
2. 点击“文件”→“打开文件夹…”，选择刚才克隆的 `testJDsALES` 目录。
3. 首次打开时，VS Code 可能会提示你信任该文件夹，点击“是，信任作者”。

## 3. 安装必要的扩展与依赖

1. 在 VS Code 扩展（Extensions）面板中搜索并安装以下扩展：
   - **Python**（微软官方扩展，提供调试、语法高亮、Lint 等功能）。
   - 如需更强的代码格式化体验，可选安装 **Black Formatter** 或 **isort** 等扩展。
2. 在 VS Code 终端中创建或激活虚拟环境，并安装项目依赖：

   ```bash
   # 创建虚拟环境（以 venv 为例）
   python -m venv .venv

   # 激活虚拟环境
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1

   # macOS/Linux
   source .venv/bin/activate

   # 安装依赖（任选其一）
   pip install -e .    # 使用 pip 安装 pyproject 中声明的依赖
   uv sync             # 如果你偏好使用 uv
   ```

   > 本项目使用 `pyproject.toml` 声明依赖，建议采用上述任一方式完成安装。

## 4. 配置调试环境

1. 打开 VS Code 侧边栏的“运行和调试”面板（快捷键：`Ctrl+Shift+D`）。
2. 点击“创建一个 launch.json 文件”，在弹出的环境列表中选择“Python”。
3. 选择合适的调试模板，例如“Python File”或“Module”。VS Code 会在 `.vscode/launch.json` 中生成配置。
4. 如果项目需要启动特定脚本（如 `main.py` 或 `app.py`），将 `program` 字段设置为相应路径：

   ```json
   {
       "name": "Run main.py",
       "type": "python",
       "request": "launch",
       "program": "${workspaceFolder}/main.py",
       "console": "integratedTerminal",
       "env": {
           "ENVIRONMENT": "development"
       }
   }
   ```

5. 若需要传递命令行参数，可在配置中加入 `args` 字段，例如：

   ```json
   "args": ["--config", "configs/dev.yaml"]
   ```

## 5. 开始调试

1. 在代码中设置断点（单击行号左侧空白区域）。
2. 在“运行和调试”面板顶部选择刚刚创建的调试配置。
3. 点击绿色的“开始调试”按钮或使用快捷键 `F5`。
4. VS Code 将在终端中启动程序，并在触发断点时暂停，允许你检查变量、调用栈等信息。

## 6. 常用技巧

- **调试任务组合**：可在 `launch.json` 中配置 `preLaunchTask`，在调试前执行如“格式化”、“运行测试”等任务。
- **环境变量管理**：若项目依赖 `.env` 文件，可安装 **Python Environment Manager** 或使用 VS Code 内置的 `python.envFile` 设置进行加载。
- **远程开发**：若需要在服务器上调试，可使用 VS Code 的 Remote SSH 或 Dev Containers 功能，将调试环境延伸至远程主机。

## 7. 完成后

1. 调试结束后记得在终端中运行 `deactivate` 退出虚拟环境。
2. 若进行了代码修改，可使用 Git 命令管理变更，并推送到远程仓库：

   ```bash
   git status
   git add <files>
   git commit -m "feat: describe your change"
   git push origin <branch>
   ```

希望本指南能帮助你顺利使用 VS Code 调试本项目！

