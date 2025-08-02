# AI受付システム LLMテストフレームワーク

LLMベースのAI受付システムの品質を定量的・定性的に評価し、具体的な改善提案を生成するテストフレームワークです。

## 🎯 テストの目的

- **想定挙動の確認**: 設計通りの動作をしているかを判定
- **改善点の特定**: 何が問題で、どこを修正すべきかを明確化
- **品質の継続監視**: 修正前後の比較による改善確認

## 📁 ファイル構成

```
backend/tests/
├── llm_test_framework.py      # テストフレームワーク本体
├── llm_test_runner.py         # API連携とテスト実行
├── test_llm_integration.py    # pytest実行可能なテスト
├── test_scenarios.yaml        # テストシナリオ定義
└── README_LLM_TESTING.md      # このファイル
```

## 🚀 使用方法

### 1. 基本テスト実行

```bash
# 全テストスイートの実行
pytest test_llm_integration.py -v

# 特定カテゴリのテスト
pytest test_llm_integration.py::TestLLMIntegration::test_appointment_scenarios -v

# 詳細レポート付きで実行
pytest test_llm_integration.py --llm-report
```

### 2. 個別シナリオテスト

```python
from llm_test_runner import LLMTestRunner

# 特定シナリオのみテスト
runner = LLMTestRunner()
await runner.run_and_report(["APT-001", "SALES-001"])
```

### 3. カスタムテストシナリオ

`test_scenarios.yaml`を編集して独自のテストケースを追加:

```yaml
test_scenarios:
  custom_cases:
    - id: "CUSTOM-001"
      name: "カスタムテストケース"
      conversation:
        - step: 1
          user_input: "テスト用の入力"
          expected:
            visitor_type: "appointment"
            extracted_info:
              name: "期待される名前"
```

## 📊 判定基準とメトリクス

### 成功/失敗の判定

各テストは以下の基準で評価されます：

| 項目 | 基準 | 重要度 |
|------|------|--------|
| 情報抽出精度 | 80%以上 | 高 |
| 応答品質 | 80%以上 | 高 |
| 会話フロー | 90%以上 | 中 |
| キーワード含有 | 100% | 中 |

### 品質スコア

- **丁寧さ**: 敬語表現の使用率
- **明確さ**: 応答の長さと理解しやすさ
- **適切性**: 不適切な表現の回避

## 📈 テスト結果の見方

### 1. 個別テスト結果

```
✅ APT-001: 標準的な予約来客
   信頼度: 0.95
   詳細判定:
   - name_extraction: ✅ 正確 (田中太郎)
   - company_extraction: ✅ 正確 (ABC商事)
   - visitor_type_classification: ✅ 正確 (appointment)
```

### 2. 全体サマリー

```
📊 エグゼクティブサマリー
- 全体成功率: 87% (26/30)
- 平均信頼度: 0.84
- 情報抽出精度: 91%
- 応答品質: 88%
```

### 3. 改善提案

```
🎯 具体的改善提案
1. 営業・予約の分類精度向上
   修正対象: app/agents/nodes.py
   提案内容: システムプロンプトに具体例を追加
```

## 🔧 カスタマイズ

### 1. 新しいバリデーターの追加

```python
class CustomValidator(BaseValidator):
    def validate(self, response, expected) -> TestResult:
        # カスタム検証ロジック
        pass

# フレームワークに追加
validator = DetailedValidator()
validator.custom_validators["my_check"] = CustomValidator()
```

### 2. 改善提案ルールの追加

`test_scenarios.yaml`の`improvement_rules`セクションを編集:

```yaml
improvement_rules:
  custom_issues:
    - pattern: "新しい問題パターン"
      category: "prompt"
      suggested_fix: "具体的な修正提案"
      file: "修正対象ファイル"
```

## 📋 テストシナリオの追加

### 1. 基本構造

```yaml
- id: "NEW-001"
  name: "新しいテストケース"
  priority: "high"  # high, medium, low
  conversation:
    - step: 1
      user_input: "ユーザーの入力"
      expected:
        visitor_type: "期待する訪問者タイプ"
        extracted_info:
          name: "期待する名前"
          company: "期待する会社名"
        must_include_keywords: ["必須キーワード"]
        quality_checks:
          check_politeness: true
          max_length: 150
```

### 2. 複数ステップの会話

```yaml
conversation:
  - step: 1
    user_input: "最初の入力"
    expected: {...}
  
  - step: 2
    user_input: "2番目の入力"
    system_event: "calendar_not_found"  # システムイベント
    expected: {...}
```

## 🐛 トラブルシューティング

### 1. API接続エラー

```bash
# バックエンドサーバーが起動していることを確認
curl http://localhost:8000/api/health

# 環境変数の確認
echo $OPENAI_API_KEY
```

### 2. テスト失敗時の調査

```python
# デバッグモードでテスト実行
runner = LLMTestRunner()
result = await runner.run_single_scenario("APT-001", api_client)

# 詳細な結果を確認
print(f"Issues: {result.issues}")
print(f"Suggestions: {result.suggestions}")
```

### 3. YAML構文エラー

```bash
# YAML構文チェック
python -c "import yaml; yaml.safe_load(open('test_scenarios.yaml'))"
```

## 📚 継続的改善のワークフロー

1. **テスト実行**: 定期的に全テストスイートを実行
2. **結果分析**: 失敗パターンと改善提案を確認
3. **修正実装**: 提案に基づいてコードやプロンプトを修正
4. **効果確認**: 修正後に同じテストを再実行
5. **新規テスト**: 新機能や問題ケースを追加

## 🎯 成功基準

プロダクション運用の目安：

- **全体成功率**: 90%以上
- **情報抽出精度**: 95%以上  
- **応答品質**: 85%以上
- **エラー回復率**: 80%以上

## 🔄 CI/CDとの統合

```yaml
# GitHub Actions例
name: LLM Quality Check
on: [push, pull_request]
jobs:
  llm-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run LLM tests
        run: |
          pip install -r requirements.txt
          pytest backend/tests/test_llm_integration.py --llm-report
```

このフレームワークにより、LLMベースシステムの品質を継続的に監視し、データ駆動型の改善を実現できます。