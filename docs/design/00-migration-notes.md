# 削除候補ファイル

以下のファイルは新しい統合ドキュメントに置き換えられたため、削除を推奨します。

## 削除対象

| ファイル | 理由 |
|---------|------|
| `research-time-tracker-design-v5-compact.md` | v6.2に統合済み（Notion時代の古い設計） |
| `research-time-tracker-design-v6-compact.md` | v6.2に統合済み（2つ混在していた） |
| `research-time-tracker-design-v6_2-compact.md` | → `01-system-overview.md` に統合 |

## 新しいドキュメント構成

```
docs/
├── 01-system-overview.md      # システム概要・全体設計（v6.2ベースに統合）
├── 02-database-design.md      # データベース設計
├── 03-api-design.md           # API設計
└── 04-mcp-design.md           # MCP設計
```

## 移行手順

1. 新しい `docs/` ディレクトリをプロジェクトに配置
2. 古いファイル（上記3つ）を削除
3. `database-design.md`, `api-design.md`, `mcp-design.md` は `docs/` 内に移動済み

```bash
# 古いファイルを削除
rm research-time-tracker-design-v5-compact.md
rm research-time-tracker-design-v6-compact.md
rm research-time-tracker-design-v6_2-compact.md

# 既存の設計書をdocs/に移動（既にコピー済みなので削除でOK）
rm database-design.md
rm api-design.md
rm mcp-design.md
```
