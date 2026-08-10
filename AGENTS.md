- `.agents/skills/rairairai-architecture/SKILL.md`：项目级架构技能，负责应用并持续优化当前架构、模块边界和演进规则。
- `.agents/skills/rairairai-tdd/SKILL.md`：项目级 TDD 技能，负责把当前项目架构映射到 Matt 的基础 TDD 技能并维护项目特化测试方式。

## codebase-memory-mcp

本项目使用 codebase-memory-mcp 做代码知识图谱。索引必须隔离，不能把项目代码和 UE 引擎源码放进同一个索引项目。

### 项目代码索引

- 项目索引名：`RaiRaiRai`
- 项目索引根：`C:\Users\dsm\Desktop\RaiRaiRai`
- 推荐命令：

```powershell
& 'C:\Users\dsm\AppData\Local\codebase-memory-mcp\codebase-memory-mcp.exe' cli index_repository --repo-path 'C:\Users\dsm\Desktop\RaiRaiRai' --name RaiRaiRai --mode full --persistence true
```

- 项目索引只服务本游戏项目代码和项目文档。
- 不要让项目索引跟随 `.codebase-memory-views/`、`Binaries/`、`Intermediate/`、`Saved/`、`DerivedDataCache/`、`.vs/`、`.idea/` 或 `Content/`。
- 本项目已建立本地 Git 仓库。修改项目代码后，优先用 Git 变更范围辅助刷新和影响分析：

```powershell
& 'C:\Users\dsm\AppData\Local\codebase-memory-mcp\codebase-memory-mcp.exe' cli detect_changes --project RaiRaiRai --since HEAD~1
```

项目代码量小时，可以在重要修改后直接重建 `RaiRaiRai` 索引。不要重建 UE 引擎索引。

### UE5.8 源码索引
UE5.8 源码在 `C:\Program Files\Epic Games\UE_5.8\Engine\Source`；需要查引擎源码时，先读取 `C:\Program Files\Epic Games\UE_5.8\Engine\Source\AGENTS.md`。
不要把 UE 源码混进 `RaiRaiRai` 项目索引；项目代码仍只查 `RaiRaiRai` 索引。



这是一个独立游戏：“显卡制造商模拟器” 前期类似于超市模拟器，玩家开局手搓显卡来卖，然后用钱升级科技 后期类似于X4基石，没有流水线的异星工厂

刚开始自己是一个专家，花本金购买了机器，手动制作显卡

制作完可以在网上卖，或者在实体店卖

网上卖的快递员会来取货

显卡需要多个源（例如GPU，VRAM，PCB），最开始的时候，没办法自己制作，只能买，朋友赞助了仓库的好多

等玩家在工作台把这些拼凑好，全部卖完之后，就有很大的本金了

手动研究显卡，加上物理模拟功能，做成一个有意思的小游戏

之后的拼凑，也可以这样，用各种接口拼凑，自己制作研究出来牛逼的显卡，更牛逼的参数使得大卖

后期资金大了，可以开分店，店和工厂分离

之后就可以去自己生产源"
