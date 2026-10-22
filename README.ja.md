# deep-doc-review — Deep Review プラグイン（Claude Code / Codex CLI 対応）

[English](README.md) | 日本語

Claude Code と OpenAI Codex CLI に、技術文書（設計書・仕様書・提案書・論文・契約書・報告書など）を **マルチエージェントで深く検証** させるためのプラグインです。
Google Research の [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/) の考え方（分割 → 適応的な予算配分 → 区間ごとの並列検証 → 全体統合と再検証）を、外部 API を使わずに **エージェント自身のサブエージェントで実行** します。

- 論理の破綻、計算ミス（合計・割合・単位・日付の再計算）、章をまたぐ矛盾、根拠のない主張、曖昧さを検出
- すべての指摘に行番号（`L0042`）・引用・根拠（再計算や矛盾箇所）・修正案を付与
- 重要な指摘は **別のサブエージェントが独立に再検証**し、誤検出を棄却
- 出力: `report.md`（既定は日本語）と `findings.json`（機械可読）
- コードレビューや文体の添削用ではありません

## インストール

> **非公開リポジトリです。** GitHub の `baneido/deep-doc-review` への読み取り権限が必要です。また、手元の git がパスワード入力なしでこのリポジトリを clone できる状態にしておいてください（例: `gh auth login` のあと `gh auth setup-git`、または GitHub に登録済みの SSH 鍵）。どちらの CLI もパスワードを尋ねません。

### Claude Code

Claude Code のセッション内で:

```text
/plugin marketplace add baneido/deep-doc-review
/plugin install deep-review@deep-doc-review
/reload-plugins
```

シェルから実行する場合:

```bash
claude plugin marketplace add baneido/deep-doc-review
claude plugin install deep-review@deep-doc-review      # 既定はユーザースコープ。--scope project で .claude/settings.json 経由の共有
```

`claude plugin list` または `claude plugin details deep-review@deep-doc-review` で確認できます。

### Codex CLI

```bash
codex plugin marketplace add baneido/deep-doc-review   # SSH の場合: git@github.com:baneido/deep-doc-review.git
codex plugin add deep-review@deep-doc-review
codex plugin list --marketplace deep-doc-review        # 「installed, enabled」と表示されれば完了
```

TUI の `/plugins` から `deep-doc-review` マーケットプレイスを選び、**deep-review** をインストールすることもできます。インストール後は新しいセッションを開始してください。

## 更新

```bash
# Claude Code
claude plugin marketplace update deep-doc-review
claude plugin update deep-review@deep-doc-review       # または /plugin → Installed → deep-review → Update now

# Codex CLI
codex plugin marketplace upgrade deep-doc-review       # マーケットプレイスとインストール済みプラグインを更新
```

## アンインストール

```bash
# Claude Code
claude plugin uninstall deep-review@deep-doc-review
claude plugin marketplace remove deep-doc-review       # 任意: マーケットプレイスの登録も削除

# Codex CLI
codex plugin remove deep-review@deep-doc-review
codex plugin marketplace remove deep-doc-review        # 任意
```

## 使い方

### Claude Code

プラグインのスキルには名前空間が付くため、コマンドは `/deep-review:deep-review` です。

```text
/deep-review:deep-review docs/design.pdf
/deep-review:deep-review docs/proposal.md lang=en depth=thorough
/deep-review:deep-review spec.md focus=第3章〜第5章の数値 web=on
```

スラッシュコマンドを使わず「この設計書をディープレビューして: docs/design.md」と頼んでも起動します。
非対話で実行する例:

```bash
claude -p "/deep-review:deep-review docs/design.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
```

### Codex CLI

スキルは `deep-review:deep-review` という名前で登録されます。

```text
$deep-review:deep-review docs/design.pdf
$deep-review:deep-review docs/proposal.md depth=thorough でレビューして、各区間はサブエージェントで並列に検証して
```

`/skills` から選ぶか、普通に頼んでも起動します。非対話の例: `codex exec --sandbox workspace-write '$deep-review:deep-review docs/design.md'`
（結果ファイルを書くため workspace-write 以上が必要です）。

### オプション（自由記述で指定）

| オプション | 値 | 既定 |
|---|---|---|
| `lang` | `ja` / `en` / `auto`（文書の言語） | `ja` |
| `depth` | `quick` / `standard` / `thorough` | `standard` |
| `focus` | 重点範囲や観点（例: 「数値のみ」「3〜5章」） | なし |
| `web` | `on` で外部情報による裏取り（文書本文は送らず短い検索語のみ） | オフ |

結果は作業ディレクトリの `.deep-review/<文書名>-<日時>/` に出力されます（`report.md`, `findings.json`, 中間ファイル）。元の文書は変更しません。

## 仕組み

1. **準備（Stage 0）**: 文書をテキスト化し `L0001| …` 形式の行番号付きファイルを作成。非常に長い文書は範囲を絞る。
2. **分割（Stage 1）**: 意味のまとまりで 4〜12 区間に分割（表は解釈する本文と同じ区間に）。全行の網羅をチェック。
3. **適応的予算配分（Stage 2）**: 区間ごとに難易度 1〜5 を付け、パス数（1〜3）と思考の深さを決める。
   パスの観点は A=総合レビュー、B=全数値の再計算と他箇所との照合、C=懐疑的な専門家による反論。
4. **並列の深い検証（Stage 3）**: 「区間 × パス」ごとに新しいサブエージェントを起動（最大 8 並列のウェーブ）。
   各レビュアーは **文書全体を読んだうえで担当区間に集中** し、厳密な JSON で指摘をファイルに書き出す。
   サブエージェントが使えない環境では、オーケストレーターが同じ手順を逐次実行する。
5. **全体統合（Stage 4）**: 指摘の統合 → 章をまたぐ矛盾の横断チェック（専用サブエージェント）→ 根本原因ごとの重複排除 →
   critical / major の指摘を **書いていないサブエージェントが独立に再検証**（confirmed / rejected / uncertain）→
   （任意）Web による裏取り → `findings.json` と `report.md` を出力。
