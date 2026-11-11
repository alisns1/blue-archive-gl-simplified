# 蔚蓝档案 国际服（蓝档）繁中 → 简体中文 + 字体统一

**一个脚本，把国际服客户端变成简体中文，并且字体大小/粗细完全统一。**

- ✅ **文本**：界面、剧情、语音字幕、道具说明全部繁转简
- ✅ **字体**：修掉「有的字粗、有的字细」的问题（这是纯文本汉化的老大难，本工具已解决）
- ✅ **不 root、不重签 APK、不装 Magisk、不碰服务器**
- ✅ 只改手机上的**本地文件**，不碰账号、存档、网络请求
- ✅ 主要面向**真机手机**；MuMu / LDPlayer / 夜神等模拟器也能用

> 仅适用于 **GL 国际服（繁中）**。日服 / 韩服 / 国服的数据库和文本表不同，不通用。

| 改之前（繁中） | 改之后（简体 + 字体统一） |
|---|---|
| ![before](docs/before.jpg) | ![after](docs/after.jpg) |

放大看细节：改之前 `任務 / 學生 / 咖啡廳 / 活動進行中`，改之后 `任务 / 学生 / 咖啡厅 / 活动进行中`，
且每个字的大小和字重都一致。

---

## 三分钟上手（Windows + 手机）

如果你是第一次用，照这个顺序做，**每一步都写了"做完应该看到什么"**。

| # | 做什么 | 做完应该看到 |
|---|---|---|
| 1 | 装 **Python 3.12**（[python.org](https://www.python.org/downloads/)，安装时**勾上 `Add python.exe to PATH`**） | 新开一个 cmd 窗口，`python --version` 打印 `Python 3.12.x` |
| 2 | 把本仓库**解压到一个文件夹**（例如 `D:\ba-cn`），在该文件夹打开 cmd，跑 `pip install -r requirements.txt` | 最后打印 `Successfully installed sqlcipher3-wheels-… unitypy-… lz4-…` |
| 3 | 手机：设置 → 关于手机 → **连点「版本号」7 次** → 开发者选项 → 打开 **USB 调试**；用**数据线**连电脑，手机上点「允许 USB 调试」 | 电脑上 `adb devices` 能看到 `XXXXXXXX  device` |
| 4 | **关掉手机上的游戏**，双击文件夹里的 **`运行.bat`** | 弹出 UAC 点「是」；黑色窗口里一行行 `[ok] …` |
| 5 | 等它跑完（首次约 3–5 分钟，之后 1–2 分钟），看到 `[ok] done.` | 打开游戏，界面已经是简体、字体也统一了 |

> 第 3 步的 `adb` 多数电脑不用单独装（见[下面第 3 节](#3-adb手机和电脑的桥)）。
> 第 2 步国内网络慢的话，把命令换成：
> `py -3.12 -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt`

**跑完这一次就完事了。** 以后游戏大版本更新后，回到第 4 步重跑一遍即可。

---

## 首次准备（详细版，只做一次）

### 1. Python

| 项目 | 说明 |
|---|---|
| 下载 | https://www.python.org/downloads/ |
| 版本 | **3.10 / 3.11 / 3.12 / 3.13** 都可以，**推荐 3.12** |
| 安装要点 | ✅ 必须勾选 **Add python.exe to PATH**（否则命令行找不到 python） |
| 验证 | **新开**一个 cmd 窗口，跑 `python --version` |

> ⚠️ **不要用 alpha / beta / rc 版**（版本号里带 `a` / `b` / `rc` 的，例如 `3.14.0a5`）。
> 预编译的库是按正式版 ABI 编的，在测试版上会「能 import、一用就崩」（报 `0xC0000005`），
> 而且报错很难看懂。脚本会自动跳过这类解释器。

### 2. 依赖库

在**仓库所在的文件夹**里打开 cmd（在文件夹地址栏输入 `cmd` 回车最快），然后：

```cmd
pip install -r requirements.txt
```

这行命令的意思是：按 `requirements.txt` 里列的清单安装三个库——

| 库 | 作用 | 不装会怎样 |
|---|---|---|
| `sqlcipher3-wheels` | 读写游戏加密数据库，**必需** | 文本汉化跑不了 |
| `unitypy==1.25.2` | 读写游戏资源包，字体统一用 | 只跳过字体统一，文本照常 |
| `lz4` | 资源包解压，字体统一用 | 同上 |

**验证：**

```cmd
python -c "import sqlcipher3; print('ok')"
python -c "import UnityPy, lz4; print('ok')"
```

两条都打印 `ok` 就装好了。**装一次即可，以后不用再装。**

> 忘了装也没关系，脚本会自检并**自动补装**：
> - `sqlcipher3` 缺失 → 脚本启动时就会自动 `pip install`（否则没法跑）
> - `UnityPy` / `lz4` 缺失 → 跑到字体那一步时自动补装
>
> 自动安装用清华源 → 官方源依次尝试；**两条都失败**（比如完全没网）才会跳过字体阶段并提示手动装。

### 3. adb（手机和电脑的桥）

脚本按这个顺序找 `adb`，找到一个就用，**多数电脑不用你操心**：

1. 环境变量 `ADB`（你自己指定的路径）
2. 系统 PATH 里的 `adb`
3. **模拟器自带的 adb** —— 装了 MuMu / LDPlayer / 夜神 / BlueStacks 就直接拿来用
   （例如 MuMu 的在 `...\Netease\MuMu\nx_main\adb.exe`）

只有一种情况需要你自己装：**只用真机、也没装过任何模拟器**。那就：

| 项目 | 说明 |
|---|---|
| 下载 | [platform-tools](https://developer.android.com/tools/releases/platform-tools)（Google 官方，20 MB 左右） |
| 安装 | 解压到例如 `C:\platform-tools`，把该目录加进系统 PATH：<br>Win 搜「环境变量」→ 编辑系统环境变量 → 环境变量 → Path → 新建 → 填 `C:\platform-tools` |
| 验证 | **新开**窗口跑 `adb version`，能打印版本号即可 |

### 4. 手机开启 USB 调试

1. 设置 → 关于手机 → **连点「版本号」7 次** → 提示「你已处于开发者模式」
2. 返回设置 → 系统 → **开发者选项** → 打开 **USB 调试**
3. 插上数据线，手机弹「**允许 USB 调试吗？**」→ 点**允许**（建议勾「一律允许」）

> 数据线有讲究：有些线只能充电、不能传数据，认不到设备就换一根。
> 也可以在同一网络下用无线调试，但**第一次建议用线**，最稳。

### 5. 自检一次

在仓库文件夹里跑：

```cmd
python -c "import sqlcipher3, UnityPy, lz4; print('ok')"
adb devices
powershell -ExecutionPolicy Bypass -File localize_phone.ps1 -DryRun
```

- 第一条打印 `ok` → 三个依赖都在（缺了见上一节；脚本也会自动补装）
- `adb devices` 应列出你的设备（后面是 `device`，不是 `unauthorized`）
- 第三条会一路打印 `[ok]`，到 `[ok] dry run finished` 就是环境全通

> `-DryRun` 只验证文本流程（拉取 → 转换 → 改 catalog），**不碰字体阶段**；
> 字体那步要真机推送时才会跑，缺依赖时脚本会当场自动补装。

---

## 每次汉化（游戏更新后重跑）

| 步骤 | 操作 |
|---|---|
| 1 | 手机用**数据线**连电脑 |
| 2 | 手机弹「允许 USB 调试吗」→ 允许（勾"一律允许"后就不用每次点了） |
| 3 | **关掉手机上的游戏**（开着会占用要替换的文件） |
| 4 | 双击 **`运行.bat`** |
| 5 | 等 1–2 分钟（首次 3–5 分钟，要下载字体），窗口里逐行打印 `[ok]` |
| 6 | 看到 `[ok] done.` → 打开游戏 |

**脚本自动做的事：**

```
1. 停游戏
2. 从手机拉出原文件（备份到 work/）
3. 繁 → 简（等长字节替换）
4. 重算 TableCatalog.bytes 里的 CRC32，让客户端校验通过
5. 推回手机
6. 替换游戏内置中文字体 → 思源黑体（字体统一，首次自动下载约 17 MB）
7. 把 App 语言设成简体中文（Android 13+，能让部分界面文字走简体字形）
8. 完事
```

重复运行是安全的：已经转换过的内容不会被二次转换（第二次跑只会改动几十个漏网词条）。

---

## 字体统一：为什么需要、脚本做了什么

### 问题长什么样

纯文本汉化后，**被改动过的字**（動→动、務→务、購→购、覽→览）会比**繁简同形的字**
（活、一、石、任）看起来**更细或更小**，同一行里字体不统一。这是安卓端汉化最容易翻车的地方。

### 根本原因

游戏内置带的中文字体 `NotoSansTC-Medium` / `NotoSansTC-Bold` 是**按繁体文本裁剪过的子集**，
字符表只有 **20,748** 个字，缺大量简体专用字（厅、览、编、购、辉…）。
缺字时 Unity 会逐字回退到系统字体，于是一句话里混用两款字体 → 大小粗细不一致。

真正被 UI 加载的那份字体在**下载资源目录**里：
`.../files/PUB/Resource/Preload/Android/prologdepengroup-…-mxprolog-*.bundle`
（APK 里虽然有同名资产，但不在渲染路径上，改它没用——这也是网上很多教程照做后"没效果"的原因。）

### 脚本怎么修

把这个资源包里两个 `Font` 资产的字体数据换成**思源黑体简体**（Noto Sans SC），
资产名和 PathID 保持不变，保存时保持原压缩方式，最后把**整个文件的 CRC32 还原成原值**
（客户端会校验 CRC，改了不还原就会被判定损坏并静默重新下载官方包）。

### 怎么确认成功

- 脚本里会打印 `[ok] font patched: …bundle` 和 `[ok] font crc verified`
- 进游戏看「咖啡厅 / 编辑 / 活动一览」——`厅`、`编`、`览` 应该和旁边的字**一样粗、一样高**

### 失败了怎么办

字体阶段是**可选**的：下载失败、没装 UnityPy、设备上找不到资源包时，脚本只打印 `[!!]` 然后
**继续做文本汉化**，绝不影响主流程。想跳过它就直接加 `-SkipFont`。

如果自动识别失效（游戏版本更新后包名变了），可以手动跑：

```bash
# 1. 在设备上找出含字体的那个包（只读，不修改）
python tools/patch_font.py --find "<设备路径>/.../PUB/Preload/Android"

# 2. 打补丁（先 --dry-run 看结果，确认后再去掉）
python tools/patch_font.py --bundle <原包> \
    --regular NotoSansSC-Regular.otf --bold NotoSansSC-Bold.otf --out <输出包>

# 3. 推回设备（文件名必须和原文件一致）
adb push <输出包> /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Preload/Android/<原文件名>
```

详细原理、验证方法和回滚步骤见 👉 **[docs/字体问题.md](docs/字体问题.md)**。

---

## 常见问题

| 现象 | 原因 / 怎么解决 |
|---|---|
| `no usable Python + sqlcipher3 found` | 脚本会逐个试探机器上的 Python（真的建一个加密库读写一遍），全部不可用才报这个。① 没装库 → `pip install -r requirements.txt`；② Python 是 alpha/beta 版 → 换 **3.12** 稳定版；③ 装了多个 Python → 加 `-Python "C:\…\python.exe"` 指定 |
| 脚本中途崩溃 / `0xC0000005` | Python 版本和预编译库 ABI 不匹配，换稳定版 Python |
| `adb not found` / 不是内部或外部命令 | platform-tools 没加进 PATH，或者装完没**重新开窗口** |
| `no device` / 设备列表为空 | USB 调试没开；没点「允许」；数据线只能充电（换线）；换个 USB 口 |
| `unauthorized` | 手机上重新点「允许 USB 调试」；或在开发者选项里「撤销 USB 调试授权」后重新插线 |
| 卡在 `pull` 很久 | 手机锁屏了 → 保持解锁；换 USB 3.0 口（330 MB 正常约 10 秒） |
| `wrong key` / 打不开数据库 | 游戏大版本更新换了密钥 → 提 Issue 并附上游戏版本号 |
| `catalog patch failed` | 游戏改了 catalog 格式 → 提 Issue 并附上你的 `TableCatalog.bytes` |
| 进游戏又变回繁体了 | 你点了游戏内「资源修复 / 重新下载」→ 关掉游戏，重跑 `运行.bat` |
| 手机重启后连不上 | adb 授权会掉，重新插线点一次「允许」 |
| 只想先试、不想推送 | `powershell -ExecutionPolicy Bypass -File localize_phone.ps1 -DryRun` |
| 字体那句 `[!!]` 是报错吗 | **不是错误，是跳过**。文本汉化已经成功，想修字体看[上面那节](#字体统一为什么需要脚本做了什么) |
| 能在模拟器上用吗 | 能（MuMu / LDPlayer 等都可以推）。同时连着手机和模拟器时脚本**优先选真机**，要指定就加 `-Serial <序列号>` |
| 转换完界面正常，少数词还是台式说法 | 词库覆盖面问题，欢迎 PR 补词（改 `dict/` 里的词库，或提 Issue 给具体词条） |

---

## 命令行用法（进阶）

Windows：

```powershell
.\localize_phone.ps1                  # 自动选设备（优先真机）
.\localize_phone.ps1 -Serial <序列号>  # 多台设备时指定
.\localize_phone.ps1 -DryRun          # 只拉取 + 转换 + 改 catalog，不推回手机
.\localize_phone.ps1 -SkipFont        # 跳过字体统一（只要文本）
.\localize_phone.ps1 -FontRegular <Regular.otf> -FontBold <Bold.otf>   # 用自己的字体
.\localize_phone.ps1 -Key <64位hex>   # 手动指定数据库密钥
```

Linux / macOS / WSL：

```bash
chmod +x localize_phone.sh
./localize_phone.sh            # 自动选设备
./localize_phone.sh <serial>   # 指定设备
DRY_RUN=1 ./localize_phone.sh  # 只转换不推送
BA_KEY=<64位hex> ./localize_phone.sh
```

---

## 它到底做了什么（原理简述）

游戏的文本表放在一个 **SQLCipher 加密的 SQLite 数据库** `ExcelDB.db` 里（约 340 MB、424 张表）。
每张表都是 `(Key INTEGER, Bytes BLOB)`，`Bytes` 里装着整张表的 **FlatBuffer** 数据。

脚本做三件事：

1. 用密钥打开这个库（SQLCipher 参数见 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)）
2. 在每一行 blob 内部做**等长字节替换**：繁 → 简几乎都是 3 字节 UTF-8 汉字互换
   （`學園 → 学院`、`檔案 → 档案`）。**长度不变 ⇒ FlatBuffer 里所有偏移字段依然有效 ⇒ 结构零风险**
3. 把 `TableCatalog.bytes` 里 `ExcelDB.db` 那条记录的 **CRC32** 改成新库的值
   —— 客户端按本地 catalog 校验，校验通过就不会触发重新下载

实测转换量（2026-11 版本）：扫描 **564,220** 行，改动 **291,438** 行 / **1,897,476** 字。

字体部分见[上面的字体章节](#字体统一为什么需要脚本做了什么)；更细的逆向细节、踩过的坑
都在 👉 [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md)。

---

## 注意事项

1. **游戏大版本更新后要重跑**：数据库换了，catalog 里的 CRC 也变了
2. **不要点游戏里的「资源修复 / 重新下载」**：会把原文件覆盖回去，重跑脚本即可恢复
3. **备份**：脚本会把原文件存到 `work/`，字体原包存到 `work/font/orig/`
4. 严格来说修改客户端文件违反游戏用户协议，**风险请自行评估**

---

## 目录结构

```
.
├── 运行.bat                  Windows 双击入口（推荐）
├── localize_phone.ps1        Windows 主脚本（文本 + 字体 + app 语言）
├── localize_phone.sh         Linux / macOS / WSL 脚本
├── tools/
│   ├── patch_db.py           繁→简（打开加密库、逐 blob 等长替换）
│   ├── patch_catalog.py      改 catalog 里的 CRC32
│   ├── patch_font.py         字体统一（替换 NotoSansTC 为思源黑体 + 还原 bundle CRC32）
│   └── t2s.py                繁简映射（OpenCC 词库，纯 Python）
├── dict/                     OpenCC 词库（Apache-2.0）
├── docs/
│   ├── HOW_IT_WORKS.md       原理、SQLCipher 参数、catalog 布局、踩坑记录
│   └── 字体问题.md            字体问题：现象、根因、修复步骤、验证、回滚
├── fonts/                    首次运行自动下载的思源黑体（也可用 -FontRegular 指定）
└── requirements.txt
```

---

## English summary

Turn the **Blue Archive Global (Traditional Chinese)** client into **Simplified Chinese**,
including fixing the mixed font weights, by patching local files on the device — no root,
no APK re-signing, no server interaction.

The game stores its tables in a SQLCipher-encrypted SQLite database (`ExcelDB.db`). Each row is
`(key, Bytes)` where `Bytes` is a FlatBuffer. The script performs **equal-length UTF-8 byte
substitution** inside those blobs (Traditional→Simplified is almost always a 3-byte CJK swap), so
every FlatBuffer offset stays valid, then rewrites the CRC32 recorded in `TableCatalog.bytes` so
the client's integrity check still passes.

The **font issue** is fixed in the same one-click run: the built-in `NotoSansTC` subset only has
20,748 CJK codepoints and lacks many Simplified glyphs, so Unity falls back to a system font
per-character and words end up with mixed weights/sizes. The script swaps the two `Font` assets in
`.../Preload/Android/prologdepengroup-…-mxprolog-*.bundle` for Noto Sans SC and restores the
bundle CRC32 (otherwise the client silently re-downloads it). The two fonts (~17 MB) are fetched
from this repository's release on first run; `-SkipFont` skips the stage, and a failed font stage
never affects the text localisation.

Requires `adb` + `sqlcipher3-wheels` (plus `unitypy==1.25.2` and `lz4` for the font stage).
**Re-run after each game update.**

See [docs/HOW_IT_WORKS.md](docs/HOW_IT_WORKS.md) for reverse-engineered details and
[docs/字体问题.md](docs/字体问题.md) for the font investigation.

---

## 署名与第三方组件

本项目站在社区成果之上，逐项署名见 **[THIRD_PARTY.md](THIRD_PARTY.md)**：

| 来源 | 许可证 | 用在哪 |
|---|---|---|
| [OpenCC](https://github.com/BYVoid/OpenCC) | **Apache-2.0** | `dict/` 下 3 个词库文件（原样复制，许可证全文见 [`dict/LICENSE-OpenCC.txt`](dict/LICENSE-OpenCC.txt)） |
| [asfu222/BlueArchiveLocalizationTools](https://github.com/asfu222/BlueArchiveLocalizationTools) | **MIT** | `TableCatalog.bytes` 的条目字段布局（`tools/patch_catalog.py` 为独立实现） |
| BlueArchive-Tools / BlueArchive-Tools-CLI（delayboy 系） | AGPL-3.0 | 仅作 SQLCipher 参数与 bundle 等长度补丁思路的**参考**；**本仓库不含其任何代码** |
| [headless-bluearchive / SDK](https://github.com/) | MIT | `Excel.zip` 口令推导（纯分析，未收录） |
| 社区所有做国际服 / 日服汉化的朋友 | — | 思路与经验 |

> **声明**：本仓库不含任何游戏素材。密钥是社区公开流传的**数据值**（随游戏版本轮换），
> 作为可覆盖的默认值提供（`--key` / `BA_KEY`）。

## License

本仓库自有代码：**MIT**（见 [LICENSE](LICENSE)）。
`dict/` 下的 OpenCC 词库：**Apache-2.0**（见 [dict/LICENSE-OpenCC.txt](dict/LICENSE-OpenCC.txt)）。
其余第三方署名见 [THIRD_PARTY.md](THIRD_PARTY.md)。

---

## 免责声明 / Disclaimer

This project is intended solely for educational and demonstrative purposes and does not provide any actual resources. Please note that all content downloaded through this project should only be used for legal and legitimate purposes. The developers are not liable for any direct or indirect loss, damage, legal liability, or other consequences that may arise from the use of this project. Users assume all risks associated with the use of this project and must ensure compliance with all relevant laws and regulations. If anyone uses this project for any unauthorized or illegal activities, the developers bear no responsibility. Users are responsible for their own actions and should understand the risks involved in using this project.

"Blue Archive" is a registered trademark of NEXON Korea Corp. & NEXON GAMES Co., Ltd. All rights reserved.

该仓库仅供学习和展示用途，不托管任何实际资源。请注意，所有通过本项目下载的内容均应仅用于合法和正当的目的。开发者不对任何人因使用本项目而可能引发的直接或间接的损失、损害、法律责任或其他后果承担任何责任。用户在使用本项目时需自行承担风险，并确保遵守所有相关法律法规。如果有人使用本项目从事任何未经授权或非法的活动，开发者对此不承担任何责任。用户应对自身的行为负责，并了解使用本项目可能带来的任何风险。

“蔚蓝档案”是上海星啸网络科技有限公司的注册商标，版权所有。

「ブルーアーカイブ」は株式会社Yostarの登録商標です。著作権はすべて保有されています。
