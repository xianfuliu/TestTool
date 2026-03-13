# GitHub Releases 自动更新指南

## 概述

本指南介绍如何为你的测试工具管理应用程序实现GitHub Releases方式的自动更新功能。通过此功能，用户可以自动检查、下载和安装新版本，无需手动分发可执行文件。

## 功能特性

- ✅ **自动检查更新** - 应用启动时自动检查GitHub Releases
- ✅ **手动检查更新** - 用户可通过菜单手动检查更新
- ✅ **版本比较** - 智能比较版本号，只提示有新版本时更新
- ✅ **后台下载** - 在后台线程中下载更新文件
- ✅ **自动安装** - 下载完成后自动重启并安装新版本
- ✅ **进度显示** - 显示下载进度和状态信息

## 配置步骤

### 1. 配置GitHub仓库信息

在 `src/ui/main_window.py` 文件中，找到以下代码并替换为你的实际GitHub仓库信息：

```python
# 更新管理相关
self.update_checker = None
self.github_repo = "your-username/your-repo"  # 替换为实际的GitHub仓库
self.current_version = self.config.get("app", {}).get("version", "1.0.0")
```

### 2. 配置GitHub Actions

项目已包含 `.github/workflows/build-and-release.yml` 文件，用于自动构建和发布。确保你的GitHub仓库已启用Actions。

### 3. 设置GitHub Token（可选）

如果需要私有仓库或更高的API限制，可以在GitHub仓库的Settings > Secrets中设置：

- `GITHUB_TOKEN` - 默认已提供，无需额外设置

## 使用方法

### 构建应用程序

使用增强的构建脚本，支持版本管理：

```bash
# 使用当前版本号构建
python build.py

# 指定版本号构建
python build.py --version 1.2.3

# 自动递增版本号构建
python build.py --increment
```

### 发布新版本

使用发布脚本简化发布流程：

```bash
# 自动递增版本并发布
python release.py --increment

# 指定版本号发布
python release.py --version 1.2.3

# 指定版本号和发布说明
python release.py --version 1.2.3 --notes "修复了XX问题，新增了YY功能"
```

### 手动发布流程

如果需要手动发布，可以按照以下步骤：

1. **更新版本号**
   ```bash
   python build.py --version 1.2.3
   ```

2. **创建Git标签**
   ```bash
   git tag v1.2.3
   git push origin --tags
   ```

3. **GitHub Actions会自动构建和发布**

## 用户更新流程

### 自动更新检查

1. 应用启动时自动在后台检查更新
2. 如果发现新版本，会弹出提示框
3. 用户可以选择立即更新或稍后更新

### 手动更新检查

1. 点击菜单栏的"帮助" -> "检查更新"
2. 查看更新说明和版本信息
3. 点击"下载更新"开始下载
4. 下载完成后点击"安装更新"

## 文件说明

### 核心文件

- `src/utils/update_manager.py` - 更新管理器核心逻辑
- `src/ui/dialogs/update_dialog.py` - 更新对话框界面
- `src/ui/main_window.py` - 主窗口集成更新功能

### 构建和发布文件

- `build.py` - 增强的构建脚本，支持版本管理
- `release.py` - 发布脚本，简化发布流程
- `.github/workflows/build-and-release.yml` - GitHub Actions工作流

### 配置文件

- `config/settings.json` - 应用配置，包含版本信息

## 技术实现细节

### 版本比较算法

使用语义化版本号比较（Semantic Versioning）：
- 格式：`主版本号.次版本号.修订号`
- 示例：`1.2.3` > `1.2.2`

### 更新流程

1. **检查更新** - 调用GitHub Releases API获取最新版本信息
2. **版本比较** - 比较当前版本和最新版本
3. **下载更新** - 下载.exe文件到临时目录
4. **安装更新** - 创建批处理文件，重启应用并替换文件

### 安全考虑

- 使用HTTPS下载，确保文件完整性
- 在临时目录操作，避免权限问题
- 用户确认后才执行安装操作

## 故障排除

### 常见问题

1. **更新检查失败**
   - 检查网络连接
   - 确认GitHub仓库地址正确
   - 查看控制台错误信息

2. **下载失败**
   - 检查磁盘空间
   - 确认有写入临时目录的权限

3. **安装失败**
   - 确保应用有管理员权限（如果需要）
   - 检查防病毒软件是否阻止了文件替换

### 调试信息

在控制台中可以查看详细的更新日志：

```
正在检查更新...
发现新版本: v1.2.3
正在下载更新... 45%
下载完成，准备安装
```

## 最佳实践

### 版本管理

- 使用语义化版本号（Semantic Versioning）
- 每次功能更新递增次版本号
- 重大变更递增主版本号
- Bug修复递增修订号

### 发布说明

在GitHub Releases中提供清晰的发布说明：
- 新功能列表
- Bug修复说明
- 已知问题
- 升级注意事项

### 测试流程

1. 在测试环境中构建和测试新版本
2. 创建预发布版本进行小范围测试
3. 确认无误后发布正式版本

## 扩展功能

### 支持的功能扩展

- [ ] 增量更新（减小下载文件大小）
- [ ] 回滚功能（安装失败时回退到旧版本）
- [ ] 多版本支持（允许用户选择安装特定版本）
- [ ] 更新前备份用户数据

通过实现GitHub Releases自动更新功能，你的应用程序将具备现代化的软件分发能力，大大简化了版本管理和用户更新流程。