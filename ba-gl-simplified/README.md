# 蔚蓝档案 国际服（Blue Archive GL）繁體 → 简体 本地汉化

把**国际服（Global / 繁中）客户端**的界面与剧情文本就地改成**简体中文**。

- ✅ **不需要 root**（`adb push` 到 `/sdcard/Android/data/...` 即可）
- ✅ **不需要重签 APK**、不需要 Magisk 模块、不碰服务器
- ✅ 改的是**本地显示文本**，不动账号、存档、网络请求
- ✅ **主要给真机（手机）用**；MuMu / LDPlayer 等模拟器也能用（方便测试）
- ✅ Windows / Linux / macOS 都有脚本
- ✅ **字体大小/粗细不一致已修复**（`tools/patch_font.py`，需自备思源黑体，见[说明](docs/字体问题.md)）

> 仅适用于 **GL（国际服，繁中）**。日服/韩服/国服的库和文本表不同，不通用。

| 改之前 | 改之后 |
|---|---|
| ![before](docs/before.jpg) | ![after](docs/after.jpg) |

（左：`任務 / 學生 / 咖啡廳 / 活動進行中`；右：`任务 / 学生 / 咖啡厅 / 活动进行中`）

---

## 快速开始

### 一次性准备（只做一次）

**① 装 Python（推荐 3.10 – 3.13 稳定版）**

| 项目 | 说明 |
|---|---|
| 下载 | https://www.python.org/downloads/ |
| 版本 | **3.10 / 3.11 / 3.12 / 3.13** —— 都用稳定版 |
| 安装要点 | ✅ 必须勾选 **Add python.exe to PATH** |
| 验证 | **新开**一个窗口跑 `python --version`，应显示 `Python 3.12.x` 之类 |

> ⚠️ **不要用 alpha / beta / rc 版 Python**（版本号带 `a` / `b` / `rc` 的，如 `3.14.0a5`）。
> 预编译的库是按该版本**正式版的 ABI** 编译的，在测试版上会「能 import、一用就崩」
> （报 `0xC0000005`），非常隐蔽。脚本会自动探测并跳过这类解释器。

**② 装依赖（只需一次）**

打开 cmd（按 `Win` 键 → 输入 `cmd` → 回车），**先切到仓库所在的文件夹**：

```cmd
:: 把下面的路径换成你自己的（尖括号 < > 只是文档里的占位符，不要照抄）
cd /d <你放这个仓库的路径>
```

> · `cd` = 切换当前目录　·`/d` 用于跨盘符切换（例如从 C 盘切到 F 盘）
> · 不知道路径？在文件夹地址栏点一下，那个就是完整路径

然后安装依赖：

```cmd
pip install -r requirements.txt
```

国内网络慢的话加个镜像（推荐）：

```cmd
py -3.12 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

> **这行命令什么意思**：`pip` 是 Python 的包管理器；`-r requirements.txt` = "按这个清单文件里列的库来装"。
> 我们的清单里只有一个 `sqlcipher3-wheels`（2.6 MB，用来读写游戏那个加密数据库）。

**验证是否装好：**

```cmd
python -c "import sqlcipher3; print('ok')"
```

打印出 `ok` 就成了。**装一次即可，以后都不用再装。**

> 忘了装也没关系：脚本启动时会自检，发现缺失会**自动帮你装一次**。但还是建议先按上面装好。

**③ 准备 adb（多数情况不用装）**

脚本按这个顺序找 adb，找到一个就用：

1. 环境变量 `ADB`（你自己指定路径）
2. PATH 里的 `adb`
3. **模拟器自带的 adb** —— 装了 MuMu / LDPlayer / 夜神 / BlueStacks 就直接用它的，**不用额外装**
   （例如 MuMu 的就在 `...\Netease\MuMu\nx_main\adb.exe`）

以上都没有（比如只用真机、没装模拟器），再自己装：

| 项目 | 说明 |
|---|---|
| 下载 | [platform-tools](https://developer.android.com/tools/releases/platform-tools) |
| 安装 | 解压到例如 `C:\platform-tools`，把该目录加进系统 PATH<br>（Win 搜「环境变量」→ 编辑系统环境变量 → 环境变量 → Path → 新建 → 填目录） |
| 验证 | **新开**窗口跑 `adb version`，能打印版本号即可 |

**④ 手机开启 USB 调试**

设置 → 关于手机 → **连点「版本号」7 次**（提示"你已处于开发者模式"）
→ 返回设置 → 系统 → **开发者选项** → 打开 **USB 调试**。

**⑤ 配好后自检一次**

**还在刚才那个文件夹里**（如果换了新窗口，先 `cd /d` 回来），跑：

```cmd
adb devices                      :: 应看到 XXXXXXXX    device
powershell -ExecutionPolicy Bypass -File localize_phone.ps1 -DryRun
```

第一条能看到你的设备序列号、第二条一路打印 `[ok]`，说明环境 OK。以后每次只需要**双击 `运行.bat`**。

### 每次汉化（游戏更新后重跑）

| 步骤 | 操作 |
|---|---|
| 1 | 手机用 **USB 数据线**连电脑（有些线只能充电，认不到设备就换一根） |
| 2 | 手机弹出「**允许 USB 调试吗？**」→ 点**允许**（建议勾"一律允许"） |
| 3 | **关掉手机上的游戏**（开着会占用要替换的文件） |
| 4 | 双击仓库里的 **`运行.bat`** |
| 5 | 等 1–3 分钟（脚本会逐步打印 `[ok]`） |
| 6 | 打开游戏 → 界面和剧情就是简体了 |

脚本内部自动完成：

```
停游戏 → 从手机拉出原文件（备份到 work/） → 繁转简 → 重算 catalog 的 CRC32 → 推回手机
```

**游戏每次大版本更新后重跑一遍即可。** 重复运行是安全的（已转换过的内容不会被二次转换）。

### 命令行用法

Windows：

```powershell
.\localize_phone.ps1                  # 自动选设备（优先挑非模拟器）
.\localize_phone.ps1 -Serial <序列号>  # 多台设备时指定
.\localize_phone.ps1 -DryRun          # 只拉取 + 转换 + 改 catalog，不推送
.\localize_phone.ps1 -Key <64位hex>   # 指定密钥
```

Linux / macOS / WSL：

```bash
chmod +x localize_phone.sh
./localize_phone.sh                   # 自动选设备
./localize_phone.sh <serial>
DRY_RUN=1 ./localize_phone.sh
BA_KEY=<64位hex> ./localize_phone.sh
```

### 先确认设备连上了

```powershell
adb devices
```

输出里要看到 `XXXXXXXX	device`。
如果是 `unauthorized` → 手机上重新点一次"允许 USB 调试"；
如果是 `offline` → 拔插一次数据线。

---

## 常见问题

| 现象 | 原因 / 解决 |
|---|---|
| `no usable Python + sqlcipher3 found` | 脚本会**逐个试探**机器上的 Python（真的建一个加密库读写一遍），全部不可用时才报这个。常见原因：① 没装 `sqlcipher3` → `pip install -r requirements.txt`；② Python 是 **alpha/beta 版**（如 `3.14.0a5`）→ 装个 **3.12/3.13 稳定版**；③ 多版本共存 → 用 `-Python "C:\...\python.exe"` 或 `$env:PYTHON` 指定 |
| 脚本中途崩溃 / `0xC0000005` | 同上，Python 版本与预编译库 ABI 不匹配，换稳定版 Python |
| `adb not found` / 不是内部或外部命令 | platform-tools 没加进 PATH，或装完没重开窗口 |
| `no device` / 设备列表为空 | USB 调试没开；没点"允许"；数据线只能充电（换线）；换个 USB 口 |
| `unauthorized` | 手机上重新点「允许 USB 调试」；或在开发者选项里"撤销 USB 调试授权"后重插 |
| 卡在 `pull` 很久 | 手机锁屏了 → 保持解锁；或换 USB 3.0 口（330 MB 正常约 10 秒） |
| `wrong key` / 打不开数据库 | 游戏大版本更新换了密钥 → 提 Issue 并说明游戏版本号 |
| `catalog patch failed` | 游戏改了 catalog 格式 → 提 Issue 并附上你的 `TableCatalog.bytes` |
| 进游戏又变回繁体了 | 你点了游戏内「资源修复 / 重新下载」→ 重跑 `运行.bat` 即可 |
| 手机重启后连不上 | adb 授权会掉，重新插线点一次"允许" |
| 只想先试不想推送 | 用命令行跑 `.\localize_phone.ps1 -DryRun` |
| 能在模拟器上用吗 | 能（MuMu / LDPlayer 等都能推）。**本工具主要面向真机手机**，模拟器适合先试；同时连着手机和模拟器时脚本会**优先选真机**，要指定就加 `-Serial <序列号>` |
| 转换完界面正常但少数词仍是台式 | 词库覆盖面问题，欢迎 PR 补词（改 `dict/` 或提 Issue 给具体词条） |
| 汉化后**某些字大小/粗细和别的不一样** | **已解决**：游戏内置的 `NotoSansTC` 字体子集缺简体字形，被改动过的字会回退到系统字体。用 `tools/patch_font.py` 把游戏字体换成思源黑体即可（详见 [docs/字体问题.md](docs/字体问题.md)）。不打补丁也**不影响任何功能** |

---

## 它到底做了什么

游戏的表数据放在一个 **SQLCipher 加密的 SQLite 库** `ExcelDB.db` 里（约 330 MB、424 张表）。
每张表是 `(Key INTEGER, Bytes BLOB)`，`Bytes` 是装着整表数据的 **FlatBuffer**。

脚本做三件事：

1. 用密钥打开这个库（SQLCipher 参数见 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)）
2. 在每行 blob 内部做**等长字节替换**：繁→简几乎都是 3 字节 UTF-8 汉字互换（`學園→学院`、`檔案→档案`）。
   **长度不变 ⇒ FlatBuffer 的所有偏移字段保持有效 ⇒ 结构零风险。**
3. 把 `TableCatalog.bytes` 里 `ExcelDB.db` 那条的 **CRC32** 改成新库的值 —— 客户端按本地 catalog 校验，于是校验通过、不会触发重新下载。

实测转换量：**267,036 行 / 1,775,029 字**。

技术细节、踩过的坑、SQLCipher 参数、catalog 二进制布局都在
👉 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)

---

## 注意

1. **游戏更新后要重跑**：库变了，catalog 的 CRC 也变了
2. **不要点游戏里的「资源修复 / 重新下载」**：会把原文件覆盖回去，重跑脚本即可
3. 脚本只改本地**文本**。严格来说修改客户端文件违反游戏用户协议，**风险请自行评估**
4. 请自行保留备份（脚本会把原文件存到 `work/`）

---

## 目录结构

```
.
├── localize_phone.ps1        Windows 一键脚本
├── localize_phone.sh         Linux / macOS / WSL 一键脚本
├── 运行.bat                  Windows 双击入口
├── tools/
│   ├── patch_db.py           繁→简（打开加密库、逐 blob 等长替换）
│   ├── patch_catalog.py      改 catalog 里的 CRC32
│   ├── patch_font.py         修字体大小/粗细（替换 NotoSansTC 并还原 bundle CRC32）
│   └── t2s.py                繁简映射（OpenCC 词库，纯 Python）
├── dict/                     OpenCC 词库（Apache-2.0）
├── docs/HOW_IT_WORKS.md      原理与踩坑记录
├── docs/字体问题.md           字体问题：现象、根因、修复步骤与验证
└── requirements.txt
```

---

## English summary

Convert the **Blue Archive Global (Traditional Chinese)** client's UI and story text to
**Simplified Chinese** by patching two local files on the device — no root, no APK
re-signing, no server interaction.

The game keeps its tables in a SQLCipher-encrypted SQLite database (`ExcelDB.db`); each row
is `(key, Bytes)` where `Bytes` is a FlatBuffer. The script performs **equal-length UTF-8
byte substitution** inside those blobs (Traditional→Simplified is almost always a 3-byte
CJK swap), so every FlatBuffer offset stays valid, then rewrites the CRC32 recorded in
`TableCatalog.bytes` so the client's integrity check still passes.

Requires `adb` + `sqlcipher3-wheels`. Re-run after each game update.

The **font weight/size inconsistency is fixed** too: the built-in `NotoSansTC` subset is
missing many Simplified glyphs, so `tools/patch_font.py` swaps the two `Font` assets in the
`prologdepengroup-…-mxprolog-*.bundle` for Noto Sans SC and restores the bundle CRC32
(see [docs/字体问题.md](docs/字体问题.md); bring your own font files).

See [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for the reverse-engineered details
(SQLCipher parameters, the HMAC key-length gotcha, the catalog binary layout).

---

## 署名与第三方组件

本项目站在社区成果之上，逐项署名见 **[THIRD_PARTY.md](THIRD_PARTY.md)**：

| 来源 | 许可证 | 用在哪 |
|---|---|---|
| [OpenCC](https://github.com/BYVoid/OpenCC) | **Apache-2.0** | `dict/` 下 3 个词库文件（原样复制，许可证全文见 [`dict/LICENSE-OpenCC.txt`](dict/LICENSE-OpenCC.txt)） |
| [asfu222/BlueArchiveLocalizationTools](https://github.com/asfu222/BlueArchiveLocalizationTools) | **MIT** | `TableCatalog.bytes` 的条目字段布局（`tools/patch_catalog.py` 为独立实现） |
| BlueArchive-Tools / BlueArchive-Tools-CLI（delayboy 系） | AGPL-3.0 | 仅作 SQLCipher 参数的**参考**；**本仓库不含其任何代码** |
| [headless-bluearchive / SDK](https://github.com/) | MIT | `Excel.zip` 口令推导（纯分析，未收录） |
| 社区所有做国际服/日服汉化的朋友 | — | 思路与经验 |

> **声明**：本仓库不含任何游戏素材。密钥是社区公开流传的**数据值**（随游戏版本轮换），
> 作为可覆盖的默认值提供（`--key` / `BA_KEY`）。

## License

本仓库自有代码：**MIT**（见 [LICENSE](LICENSE)）。
`dict/` 下的 OpenCC 词库：**Apache-2.0**（见 [dict/LICENSE-OpenCC.txt](dict/LICENSE-OpenCC.txt)）。
其余第三方署名见 [THIRD_PARTY.md](THIRD_PARTY.md)。

---

## 字体大小 / 粗细不一致 —— 已解决

> 早期本文写的是「不 root 无解」，该结论**已被推翻**。旧的 8 轮排查记录保留在
> [docs/字体问题.md](docs/字体问题.md) 的「历史记录」一节，这里只讲结论。

**现象**：汉化后，被改动过的字（動→动、務→务、購→购、覽→览 这类）比繁简同形的字
（活、一、石 这类）更细或更小，同一行里字体不统一。

**根因**：游戏内置的 `NotoSansTC-Medium` / `NotoSansTC-Bold` 是按繁体文本裁剪的子集，
cmap 只有 **20,748** 字，缺大量简体字形；缺字时 Unity 回退到系统字体，于是一行字混用
两款字体。UI 实际加载的那一份在下载目录里：
`Preload/Android/prologdepengroup-…-mxprolog-*.bundle`（APK 内虽有同名资产，但不在渲染路径上）。

**修复**：把该 bundle 里两个 `Font` 资产的 `m_FontData` 换成思源黑体简体的
`NotoSansSC-Regular/Bold.otf`，保持资产名/PathID 不变，保存时保持原压缩方式，
并把整个文件的 CRC32 还原成原值（catalog 校验用）。

```bash
pip install UnityPy==1.25.2

# 1. 找当前的包（文件名带日期/hash，游戏更新后会变；只读）
python tools/patch_font.py --find "<设备>/.../PUB/Preload/Android"

# 2. 打补丁：先 --dry-run 看结果（不写文件），确认无误再去掉
python tools/patch_font.py --bundle <原包> \
    --regular NotoSansSC-Regular.otf --bold NotoSansSC-Bold.otf \
    --out <输出包>

# 3. 推回设备（文件名必须与原文件一致）
adb push <输出包> /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Preload/Android/<原文件名>
```

需要**自备**原版资源包和思源黑体（Noto Sans SC）。不需要 root，也不改 APK。
三个关键点：`env.save(pack="original")`（换 lz4 会改 flags，游戏加载失败）、
还原 CRC32（否则游戏静默重下官方包，表现成「改了没效果」）、同步 header 里的文件长度。
验证方法、热更覆盖、回滚步骤都写在 👉 **[docs/字体问题.md](docs/字体问题.md)**。

> 这个补丁**不在** `运行.bat` 的自动流程里：它要额外处理一个 ~11 MB 的资源包，
> 还要用户自备字体，且只影响观感，所以做成独立工具。**不打也不影响任何功能**。

---

## 免责声明 / Disclaimer

This project is intended solely for educational and demonstrative purposes and does not provide any actual resources. Please note that all content downloaded through this project should only be used for legal and legitimate purposes. The developers are not liable for any direct or indirect loss, damage, legal liability, or other consequences that may arise from the use of this project. Users assume all risks associated with the use of this project and must ensure compliance with all relevant laws and regulations. If anyone uses this project for any unauthorized or illegal activities, the developers bear no responsibility. Users are responsible for their own actions and should understand the risks involved in using this project.

"Blue Archive" is a registered trademark of NEXON Korea Corp. & NEXON GAMES Co., Ltd. All rights reserved.

该仓库仅供学习和展示用途，不托管任何实际资源。请注意，所有通过本项目下载的内容均应仅用于合法和正当的目的。开发者不对任何人因使用本项目而可能引发的直接或间接的损失、损害、法律责任或其他后果承担任何责任。用户在使用本项目时需自行承担风险，并确保遵守所有相关法律法规。如果有人使用本项目从事任何未经授权或非法的活动，开发者对此不承担任何责任。用户应对自身的行为负责，并了解使用本项目可能带来的任何风险。

“蔚蓝档案”是上海星啸网络科技有限公司的注册商标，版权所有。

「ブルーアーカイブ」は株式会社Yostarの登録商標です。著作権はすべて保有されています。
