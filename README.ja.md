# deep-doc-review

[English](README.md) | 日本語

**deep-doc-review** は、技術文書の誤りを丁寧にチェックする [Claude Code](https://docs.claude.com/en/docs/claude-code) と [OpenAI Codex CLI](https://github.com/openai/codex) 用のプラグインです。設計書・仕様書・提案書・論文・契約書・報告書などを渡すと、見つかった問題を、場所・理由・修正案つきでまとめたレポートを返します。

Google Research の [Deep Review](https://research.google/blog/analyzing-technical-documents-with-deep-review/) で紹介された手法にもとづいています。文書を一度読んで終わりにするのではなく、区間に分け、複数のレビュアーが各区間を同時に深く調べ、最後に結果を突き合わせて再確認します。

## 見つけられること

- 計算ミス（合計・割合・単位・日付を読むだけでなく実際に計算し直します）
- 文書内の別々の箇所どうしの矛盾
- 論理の破綻や根拠のない主張
- 複数の意味に読める曖昧な表現

すべての指摘に、行番号、該当箇所の引用、根拠（再計算の結果や矛盾している箇所など）、修正案が付きます。重要な指摘は別のレビュアーがもう一度確かめるので、誤検出は取り除かれます。

コードレビューや、文体・文法の添削には向いていません。

## 必要なもの

Claude Code または Codex CLI を、インストールしてサインインした状態で使います。

## インストール

### Claude Code

Claude Code のセッションで次を実行します。

```text
/plugin marketplace add baneido/deep-doc-review
/plugin install deep-doc-review@deep-doc-review
/reload-plugins
```

### Codex CLI

ターミナルで次を実行し、Codex のセッションを新しく開きます。

```bash
codex plugin marketplace add baneido/deep-doc-review
codex plugin add deep-doc-review@deep-doc-review
```

## 使い方

文書があるフォルダで Claude Code か Codex を開き、レビューを頼みます。

```text
docs/design.md をディープレビューして
```

コマンドで直接呼び出すこともできます。

| Claude Code | Codex CLI |
|---|---|
| `/deep-doc-review:deep-doc-review docs/design.md` | `$deep-doc-review:deep-doc-review docs/design.md` |

## オプション

ファイル名のあとに書き添えます。例: `/deep-doc-review:deep-doc-review spec.pdf lang=en depth=thorough`

| オプション | 内容 | 既定 |
|---|---|---|
| `lang` | レポートの言語。`ja`（日本語）、`en`（英語）、`auto`（文書と同じ言語） | `ja` |
| `depth` | どこまで丁寧に調べるか。`quick`、`standard`、`thorough`。丁寧なほど時間がかかります | `standard` |
| `focus` | 重点的に見てほしい範囲や観点。例: `focus=第3章〜第5章の数値` | なし |
| `web` | 規格・価格・法令などの事実を Web 検索で確かめます。送るのは短い検索語だけで、文書の本文は送りません。`web=off` で無効にできます | `on` |

## 出力

作業フォルダに `.deep-doc-review/<文書名>-<日時>/` というフォルダが作られ、結果が保存されます。

- `report.md`: レビューレポート。最初に指摘の一覧表、続いて各指摘の詳細
- `findings.json`: 同じ指摘を機械処理しやすい形式で保存したもの

## しくみ

1. **準備**: 文書をテキストにして全行に番号を振ります。これで、指摘ごとに正確な行を示せます。
2. **分割**: 内容のまとまりごとに 4〜12 の区間に分けます。
3. **計画**: 区間ごとに難しさと重要度を見積もります。難しい区間ほど多くのレビュアーを割り当て、それぞれ違う観点（全体的なレビュー、全数値の再計算、懐疑的な専門家の目）から調べます。
4. **レビュー**: レビュアーが並行して作業します。各レビュアーは文書全体を読んだうえで、担当区間に集中します。
5. **統合と再確認**: 指摘をまとめ、区間をまたぐ矛盾を確認し、重複を取り除きます。重要な指摘は、それを出していない別のレビュアーが確かめ直し、成り立たないものは外します。
