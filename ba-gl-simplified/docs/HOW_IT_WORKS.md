# 原理与踩坑记录

本文记录整个汉化链路的**逆向结论**，方便以后版本更新时快速复用。

---

## 一、数据存在哪

国际服安卓客户端把表数据放在外部存储：

```
/sdcard/Android/data/com.nexon.bluearchive/files/PUB/Resource/
├── Preload/TableBundles/
│   ├── ExcelDB.db            ← 所有文本 + 数值表（约 330 MB，SQLCipher 加密）
│   ├── Excel.zip             ← 只有 62 张玩法常量表，没有任何文本表
│   └── *DBSchema.db          ← 3 个同样加密的附属库
└── Catalog/TableBundles/
    └── TableCatalog.bytes    ← 资源清单（含每个文件的 CRC32）
```

> 早期想走 `Excel.zip` 替換的路子——**死路**。它里面只有 `animationblend`、`bossphase` 之类的常量表，
> `LocalizeExcel` / `CharacterDialogExcel` / `ScenarioScriptExcel` 这些全是文本的库**只存在于 ExcelDB.db**。

`ExcelDB.db` 是 **SQLCipher 4** 加密的 SQLite：

| 参数 | 值 |
|---|---|
| 页大小 | 4096 |
| KDF | PBKDF2-HMAC-SHA512，256000 次 |
| 保留区 | 80 字节（16 IV + 64 HMAC-SHA512） |
| 原始密钥 | 32 字节（直接当 AES-256 key 用） |

表结构（424 张表全都一样）：

```sql
CREATE TABLE LocalizeDBSchema (Key INTEGER, Bytes BLOB)
```

`Bytes` 是 **FlatBuffer**，真正的文本在里面。
（列名不一定叫 `Key`，有的表是 `Id`/`StringId`，所以我们统一用 `rowid` 操作。）

---

## 二、密钥

```
ef0aaca06f34b4a4be3172a75a3ea565e815f9ece35b1fb12b7a166ba0807bc4
```

- 这是社区工具（delayboy / BlueArchive-Tools）里公开的那把
- **PC 端和安卓端是同一把**（网上流传的"两端密钥不同"是错的）
- 服务端每期活动可能轮换，轮换后需要重新获取（`Queuing_GetCryptoKeys` 接口需要已登录会话）

### ⚠️ 最大的坑：HMAC 子密钥长度是 32，不是 64

SQLCipher 校验页头的 HMAC 时，子密钥是这么来的：

```
hmac_key = PBKDF2-HMAC-SHA512(encryption_key, salt[i] ^ 0x3A, 2 iterations, dklen=32)
                                                                                  ^^^^^^
```

**`dklen` 固定为 32**（SQLCipher 源码里的 `KEY_SIZE`），**不是 SHA512 的摘要长度 64**。

我一开始写成 64，结果是：**密钥完全正确，但所有校验都返回"不匹配"** —— 白白找了几小时。

一个不依赖 AES 的快速校验器（只用 `hashlib`/`hmac`）：

```python
salt   = page[:16]
msg    = page[16:4016] + page[4016:4032] + (1).to_bytes(4, 'little')   # 密文 + IV + 页号
stored = page[4032:4096]
hmac_key = hashlib.pbkdf2_hmac('sha512', raw_key, bytes(b ^ 0x3A for b in salt), 2, dklen=32)
assert hmac.compare_digest(stored, hmac.new(hmac_key, msg, 'sha512').digest())
```

（`reserve = 80` ⇒ `ciphertext_end = 4096 - 80 = 4016`。）

---

## 三、转换策略：等长替换

FlatBuffer 里全是相对偏移，**只要 blob 长度不变，结构就绝对不会坏**。

繁→简绝大多数情况是 **3 字节 UTF-8 汉字互换**：

```
學 U+5B78 (e5 ad b8)  →  学 U+5B66 (e5 ad a6)     长度都是 3
檔 U+6A94 (e6 aa 94)  →  档 U+6863 (e6 a1 a3)     长度都是 3
```

所以：扫 blob 里连续的 3 字节 CJK 区段 → 整段做繁简转换 → **长度一致才写回**，
不一致就退化成逐字替换（仍要求等长）。长度会变的字符直接跳过。

这样做的额外好处：**不需要 FlatData schema**，不用管每个表的字段名和版本差异。

### 转换用词

`tools/t2s.py` 用 OpenCC 词库，`tw2sp` 模式按顺序叠三层：

1. `TWPhrasesRev.txt` —— 台湾用词（`網路` → `网络`、`伺服器` → `服务器`）
2. `TSPhrases.txt` —— 词组级简繁（避免"一简对多繁"拆错）
3. `TSCharacters.txt` —— 单字兜底

实测改动 **267,036 行 / 1,775,029 字**。

---

## 四、catalog：为什么还要改它

客户端启动时会拿 `TableCatalog.bytes` 校验每个资源文件的 **CRC32**。
库被我们改过 → CRC 变了 → 它会认为文件损坏 → 重新下载，汉化白做。

所以要把 catalog 里那一条的 CRC 改掉。**国际服（GL）的条目结构里只有 CRC，没有 Size**
（日服那条是 Size + CRC，别照抄日服的解析器）：

```
offset 28: 0a 00 00 00  "ExcelDB.db"        ← 名称（长度前缀）
offset 42: f0 83 5d ee 00 00 00 00         ← i64 CRC32（这库原始值正好是 0xEE5D83F0）
offset 50: 01                              ← bool
offset 51: ff ff ff ff                     ← includes（-1 = 空）
```

条目定位方式：全文件搜 `ExcelDB.db`，其前 4 字节应为 `0a 00 00 00`（长度 10），
再往后按 `i8 / i32 / 名称` 偏移过去，紧跟的 8 字节就是 CRC（高 4 字节为 0）。
**用"这个值是否等于原库的 CRC32"来确认定位正确**，非常稳。

改完 CR C后客户端校验通过、不触发重下，**catalog 的其它部分一律不动**。

> 另一种思路（社区日服补丁用的）：给库补长到原大小、再用 CRC32 的线性性质解出末尾 4 字节使整体 CRC 不变。
> 那样连 catalog 都不用改。但需要改动库的**真实数据区末尾 4 字节**，有损坏风险，我们没走这条。

---

## 五、走过但没用的路（别再重复踩）

| 尝试 | 结论 |
|---|---|
| **扫内存找密钥** | ❌ 客户端读完库就释放页缓存。全进程内存扫描（含文件映射）只有 `libsqlcipher.so` 自己的常量字符串，没有任何解密后的 `SQLite format 3` 页 |
| **等它打开库的瞬间连拍内存** | ❌ 对比前后快照、只搜变化字节（138 MB、步长 1 全扫）——也没有 |
| **在客户端 DB 里找明文** | ❌ 磁盘上 4 个库全是密文，没有解密临时文件 |
| **重签 APK** | ❌ 文本不在 APK 里，表数据全是从 CDN 下的 |
| **`Excel.zip`** | ❌ 62 张表全是玩法常量，没有文本表 |
| **走 gateway 接口要密钥** | ⚠️ 加上 `mx: 2` 请求头后 `Queuing_GetCryptoKeys` 会返回 200，但需要**已登录会话**才有内容 |
| **不 root 的手机取内存** | ❌ 读别的进程内存需要 root 或 ptrace 权限；Shizuku / adb 只到 shell（uid 2000）级别，达不到 |
| **IDA 断点抓 key** | 汉化者建议的路子，能做但是几十小时级工程量（**最后没用上**：密钥本来就是公开的） |

**教训**：先花 10 分钟验证"我的校验器对不对"，再去花 5 小时搜内存。
那次把 `dklen` 写成 64，让所有搜索都成了假阴性。

---

## 六、手工命令（脚本内部做的事）

```bash
# 1. 拉文件（原文件就是备份）
adb pull /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Resource/Preload/TableBundles/ExcelDB.db .
adb pull /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Resource/Catalog/TableBundles/TableCatalog.bytes .

# 2. 繁转简（等长替换）
python tools/patch_db.py --in ExcelDB.db --out ExcelDB.cn.db

# 3. 按新库的 CRC32 改 catalog
python tools/patch_catalog.py --catalog TableCatalog.bytes --db ExcelDB.cn.db \
       --out TableCatalog.cn.bytes --expect-crc-db ExcelDB.db

# 4. 推回（先停游戏）
adb shell am force-stop com.nexon.bluearchive
adb push ExcelDB.cn.db      /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Resource/Preload/TableBundles/ExcelDB.db
adb push TableCatalog.cn.bytes /sdcard/Android/data/com.nexon.bluearchive/files/PUB/Resource/Catalog/TableBundles/TableCatalog.bytes
```

Android 11–16 实测：`adb push` 写 `/sdcard/Android/data/<包名>/` **不需要 root**。

---

## 七、已知限制

1. **只有 GL（繁中）能用**。日服 / 韩服 / 国服的库、文本表、catalog 结构都不同
2. **图片上的文字改不了**（立绘、活动 banner、部分 logo 是烘焙进图的），只改**文本表**
3. 少数用词可能仍然偏台式（词库覆盖面有限），欢迎 PR 补词
4. 游戏大版本更新后要重跑（脚本会自动重新拉最新库再转）
