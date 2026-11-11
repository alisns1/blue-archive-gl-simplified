# dict/ — OpenCC 词库 / third-party data

这三个文件取自 [OpenCC](https://github.com/BYVoid/OpenCC) 的 `data/dictionary/`，
**原样复制、未作任何修改**，遵循 **Apache License 2.0**。

| 文件 | 用途 |
|---|---|
| `TWPhrasesRev.txt` | 台湾用词 → 大陆用词（`網路` → `网络`、`伺服器` → `服务器`） |
| `TSPhrases.txt` | 词组级繁→简（处理"一简对多繁"，避免拆错） |
| `TSCharacters.txt` | 单字繁→简兜底 |

`tools/t2s.py` 按上表顺序叠加应用（前面的词典改过的部分，后面的不再覆盖），
在改写数据库 blob 时**不做任何会改变长度的替换**。

只想要字形转换的话，`TSCharacters.txt` 单独就够；两个词组表用于提升用词质量。

## 许可证

- 许可证全文：[`LICENSE-OpenCC.txt`](LICENSE-OpenCC.txt)（Apache License 2.0）
- 上游项目：https://github.com/BYVoid/OpenCC
- 版权归 OpenCC 项目及其贡献者所有

如果再分发本仓库，请保留 `LICENSE-OpenCC.txt` 与本文件
（Apache-2.0 §4 要求随附许可证副本并保留署名声明）。
