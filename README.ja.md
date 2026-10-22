# deep-doc-review — Deep Review スキル（Claude Code / Codex CLI 対応）

[English](README.md) | 日本語

Claude Code と OpenAI Codex CLI に、技術文書（設計書・仕様書・提案書・論文・契約書・報告書など）を **マルチエージェントで深く検証** させるための Agent Skill です。
Google Research の [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/) の考え方（分割 → 適応的な予算配分 → 区間ごとの並列検証 → 全体統合と再検証）を、外部 API を使わずに **エージェント自身のサブエージェントで実行** します。

- 論理の破綻、計算ミス（合計・割合・単位・日付の再計算）、章をまたぐ矛盾、根拠のない主張、曖昧さを検出
- すべての指摘に行番号（`L0042`）・引用・根拠（再計算や矛盾箇所）・修正案を付与
- 重要な指摘は **別のサブエージェントが独立に再検証**し、誤検出を棄却
- 出力: `report.md`（既定は日本語）と `findings.json`（機械可読）
- コードレビューや文体の添削用ではありません

## 構成

```
.
├── install.sh                         # Claude Code / Codex へのインストール（冪等）
├── skills/deep-review/                # スキル本体（両プラットフォーム共通）
│   ├── SKILL.md                       # オーケストレーション手順（Stage 0–4）
│   ├── agents/openai.yaml             # Codex 用 UI メタデータ（Claude Code は無視）
│   ├── references/
│   │   ├── prompts.md                 # サブエージェント用プロンプト（レビュー/横断チェック/再検証）
│   │   ├── findings-schema.json       # 指摘 JSON のスキーマ
│   │   ├── report-template.md         # レポートのひな形
│   │   └── platform-notes.md          # Claude Code / Codex の違い（起動方法・並列数・権限）
│   └── scripts/                       # 任意の補助スクリプト（Python 3 標準ライブラリのみ）
│       ├── prepare_doc.py             # PDF/DOCX/MD → 行番号付きテキスト
│       ├── check_segments.py          # 分割が全行を網羅しているか確認
│       ├── merge_findings.py          # 指摘の検証・統合・ID 付与・根本原因グループ適用
│       └── finalize.py                # 再検証結果の反映と findings.json 出力
├── agents/
│   ├── claude/deep-review-reviewer.md # Claude Code 用サブエージェント定義
│   └── codex/deep_review_reviewer.toml# Codex 用カスタムエージェント定義
└── tests/                             # 誤りを仕込んだ合成文書と正解キー、採点スクリプト
```

## インストール

### install.sh（推奨）

```bash
git clone git@github.com:baneido/deep-doc-review.git
cd deep-doc-review
./install.sh                # 見つかった方（Claude Code / Codex）に両方インストール
./install.sh --claude-only  # Claude Code のみ
./install.sh --codex-only   # Codex のみ
./install.sh --codex-legacy # 旧 Codex 向けに ~/.codex/skills にもコピー
./install.sh --uninstall    # 削除
```

| 対象 | スキル | サブエージェント定義 |
|---|---|---|
| Claude Code | `~/.claude/skills/deep-review/` | `~/.claude/agents/deep-review-reviewer.md` |
| Codex CLI | `~/.agents/skills/deep-review/` | `~/.codex/agents/deep_review_reviewer.toml` |

更新は `git pull && ./install.sh` を再実行するだけです（上書きコピー）。

### 手動コピー

```bash
# Claude Code（個人用）
mkdir -p ~/.claude/skills ~/.claude/agents
cp -R skills/deep-review ~/.claude/skills/
cp agents/claude/deep-review-reviewer.md ~/.claude/agents/

# Codex CLI（個人用）
mkdir -p ~/.agents/skills ~/.codex/agents
cp -R skills/deep-review ~/.agents/skills/
cp agents/codex/deep_review_reviewer.toml ~/.codex/agents/
```

プロジェクト単位で共有したい場合は、リポジトリ内の `.claude/skills/deep-review/`（Claude Code）や `.agents/skills/deep-review/`（Codex）に置きます。
サブエージェント定義は任意です。無い場合、Claude Code は `general-purpose`、Codex は既定のサブエージェントを使います。

## 使い方

### Claude Code

```text
/deep-review docs/design.pdf
/deep-review docs/proposal.md lang=en depth=thorough
/deep-review spec.md focus=第3章〜第5章の数値 web=on
```

スラッシュコマンドを使わず「この設計書をディープレビューして: docs/design.md」と頼んでも起動します。
非対話で実行する例:

```bash
claude -p "/deep-review docs/design.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
```

### Codex CLI

```text
$deep-review docs/design.pdf
$deep-review docs/proposal.md depth=thorough でレビューして、各区間はサブエージェントで並列に検証して
```

`/skills` からも選択できます。非対話の例: `codex exec --sandbox workspace-write '$deep-review docs/design.md'`
（結果ファイルを書くため workspace-write 以上が必要です）。

### オプション（自由記述で指定）

| オプション | 値 | 既定 |
|---|---|---|
| `lang` | `ja` / `en` / `auto`（文書の言語） | `ja` |
| `depth` | `quick` / `standard` / `thorough` | `standard` |
| `focus` | 重点範囲や観点（例: 「数値のみ」「3〜5章」） | なし |
| `web` | `on` で外部情報による裏取り（文書本文は送らず短い検索語のみ） | オフ |

結果は作業ディレクトリの `.deep-review/<文書名>-<日時>/` に出力されます（`report.md`, `findings.json`, 中間ファイル）。元の文書は変更しません。

## パイプライン

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

## テスト

`tests/planted_design_doc.md` は誤りを 6 件（＋ボーナス 1 件）仕込んだ合成設計書、`tests/planted_errors.json` が正解キーです。
正しい計算も含まれており、誤検出しないかも確認できます。

```bash
cd tests
claude -p "/deep-review planted_design_doc.md" --permission-mode acceptEdits \
  --allowedTools "Read,Write,Edit,Glob,Grep,Agent,Bash(python3:*),Bash(mkdir:*),Bash(date:*)"
python3 score.py .deep-review/planted_design_doc-*/findings.json
```

## 補足

- 補助スクリプトは任意です。Python が無い環境でも、エージェントが同じ処理を手作業で行えるよう SKILL.md に記述しています。
- 外部 API でバッチ実行・モデル混在・コスト計測をしたい場合は、別途スタンドアロンの Python 版ツールを使う運用も可能です（本スキルの既定はエージェントネイティブ実行）。
