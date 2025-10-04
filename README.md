# Ash-MOD-Tools

批量文件处理工具集 - 基于PyQt5的图形界面应用程序

## 项目结构

```
Ash-MOD-Tools/
├── src/                    # 源代码目录
│   ├── Ash_MOD_Tools_Main.py  # 主程序入口
│   ├── BatchRenameFiles.py    # 批量重命名功能
│   ├── BatchReplaceFiles.py   # 批量文件内容替换功能
│   └── resources.py          # 资源文件（图标等）
├── docs/                   # 文档目录
│   ├── README.md           # 项目说明（此文件）
│   ├── CHANGELOG.md        # 变更日志
│   ├── COMPLIANCE.md       # 合规性检查清单
│   └── THIRD_PARTY_LICENSES # 第三方许可证信息
├── legal/                  # 法律文件目录
│   ├── LICENSE             # GPL v3.0 许可证
│   └── COPYRIGHT           # 版权声明
├── config/                 # 配置文件目录
│   ├── requirements.txt    # Python依赖包列表
│   ├── .gitignore         # Git忽略规则
│   └── .gitattributes       # Git属性配置
├── icon.ico               # 应用程序图标（根目录）
└── Ash_MOD_Tools_Main.exe # 编译后的可执行文件（如存在）
```

## 运行方式

### 方法1：直接运行源代码
```bash
# 进入源代码目录
cd src

# 运行主程序
python Ash_MOD_Tools_Main.py
```

### 方法2：使用可执行文件
如果存在 `Ash_MOD_Tools_Main.exe`，可直接双击运行。

## 功能特性

- **批量重命名**：可视化界面批量重命名文件
- **批量替换**：批量替换文件内容
- **图形界面**：基于PyQt5的用户友好界面
- **标签页设计**：集成多个工具于一体

## 系统要求

- Python 3.6+
- PyQt5 5.15.9+
- Windows操作系统

## 安装依赖

```bash
pip install -r config/requirements.txt
```

## 许可证

本项目遵循 GNU General Public License v3.0 协议。详见 `legal/LICENSE` 文件。

## 版权信息

Copyright (C) 2025 AshToAsh815

## 项目地址

https://github.com/[你的用户名]/Ash-MOD-Tools