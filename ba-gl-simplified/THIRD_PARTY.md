# 第三方组件与署名 / Third-party notices

本仓库**不包含任何游戏素材**，本身只处理用户自己设备上已有的文件。
下面是开发过程中使用或参考过的第三方成果，按许可证要求逐项署名。

---

## 1. OpenCC 词库（已包含在仓库内）

| 项 | 内容 |
|---|---|
| 文件 | `dict/TSCharacters.txt`、`dict/TSPhrases.txt`、`dict/TWPhrasesRev.txt` |
| 来源 | [BYVoid/OpenCC](https://github.com/BYVoid/OpenCC) — `data/dictionary/` |
| 许可证 | **Apache License 2.0** |
| 使用方式 | **原样复制，未作修改** |
| 许可证全文 | [`dict/LICENSE-OpenCC.txt`](dict/LICENSE-OpenCC.txt) |

`tools/t2s.py` 只是这套词库的**读取与应用逻辑**（我们自己写的），词库数据本身版权归 OpenCC 项目所有。

---

## 2. TableCatalog 二进制布局（参考知识，代码为独立实现）

| 项 | 内容 |
|---|---|
| 来源 | [asfu222/BlueArchiveLocalizationTools](https://github.com/asfu222/BlueArchiveLocalizationTools) — `assistance/patch_table_catalog.py` |
| 许可证 | **MIT License**，Copyright (c) 2025 anon |
| 使用方式 | 参考其**条目字段顺序**（`i8 / i32 / name / i64 crc / bool / includes`）来定位 CRC 字段。 |
| 说明 | `tools/patch_catalog.py` 为**独立实现**（基于字节模式定位，而非顺序解析整个 catalog），未复制其源代码。 |

> MIT 许可证允许参考与再实现，要求保留版权与许可声明 —— 即本文件。

---

## 3. SQLCipher 参数与密钥（事实性信息，未包含其代码）

| 项 | 内容 |
|---|---|
| 参考来源 | [BlueArchive-Tools / BlueArchive-Tools-CLI](https://github.com/DelAD/delayboy) — `utils/sqlcipher.py` 等 |
| 许可证 | **AGPL-3.0** ⚠️ |
| 使用方式 | **仅作为参考**，用于确认 SQLCipher 4 的参数（页大小 4096、KDF 迭代 256000、HMAC-SHA512、保留区 80 字节）。 |
| 重要说明 | **本仓库不包含该项目的任何代码**，因此不受 AGPL-3.0 的传染性约束。数据库的打开/读写全部交给独立的第三方库 `sqlcipher3`。 |

我们自己的密钥校验器（仅用于开发期验证，**未包含在本仓库**）曾按该实现的逻辑重写，
过程中发现其 HMAC 子密钥长度参数为 32 —— 该参数属于 SQLCipher 的**接口事实**，不受版权保护。

### 关于密钥本身

`ef0aaca0…807bc4` 是社区**公开流传**的密钥值（上述项目及相关文档中均有记载）。
密钥属于**数据/事实**，不是受版权保护的表达；本仓库将其作为可覆盖的默认值提供
（`--key` / `BA_KEY`）。

---

## 4. 运行时依赖（未包含在仓库内，由用户自行安装）

| 包 | 许可证 | 用途 |
|---|---|---|
| [`sqlcipher3-wheels`](https://pypi.org/project/sqlcipher3-wheels/) | 见 PyPI 页面（SQLCipher 本体为 BSD 风格） | 打开/写入 SQLCipher 加密的 SQLite 库 |

安装方式见 `requirements.txt`。依赖的许可证随其发行包一并提供，本仓库不再重复分发。

---

## 5. 其他参考（思路借鉴，未使用其代码）

| 项目 | 许可证 | 借鉴内容 |
|---|---|---|
| [BAJP2CNPatch](https://github.com/) （BAJP2CNPatch-main） | MIT | 用代理替换资源文件的整体思路；以及"改 catalog 而非伪造文件"的做法 |
| [headless-bluearchive / SDK](https://github.com/) （SDK-main） | MIT | `Excel.zip` 口令的推导方式（纯分析用，未收录） |
| BlueArchive-Translator（相关文档） | 未声明 | 社区文档中关于密钥来源的说明 |

---

## 如果你要复用本仓库

- 本仓库自有代码：**MIT**（见 [`LICENSE`](LICENSE)）
- `dict/` 下词库：**Apache-2.0**（保留 `dict/LICENSE-OpenCC.txt` 即可）
- 上面第 2、3 项的署名请一并保留

如发现署名有遗漏或不当，欢迎提 Issue 或 PR 指出，我们会立刻更正。
