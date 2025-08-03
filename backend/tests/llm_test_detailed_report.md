# AI受付システム LLMテスト結果レポート
生成日時: 2025-08-03 16:19:03

## 📊 エグゼクティブサマリー
- **全体成功率**: 64.3% (9/14)
- **平均信頼度**: 0.96
- **情報抽出精度**: 81.8%
- **応答品質**: 100.0%

## 📈 カテゴリ別パフォーマンス
- ❌ **APT**: 66.7%
- ❌ **SALES**: 66.7%
- ❌ **DEL**: 50.0%
- ❌ **ERR**: 66.7%
- ❌ **COMP**: 66.7%

## ⚠️ 主要問題と改善アクション
### 1. 必須キーワード「受付」が応答に含まれていません (発生回数: 2)
**影響を受けたテスト:**
- APT-003
- DEL-001

### 2. 必須キーワード「確認」が応答に含まれていません (発生回数: 2)
**影響を受けたテスト:**
- SALES-003
- COMP-001

### 3. 必須キーワード「担当者」が応答に含まれていません (発生回数: 1)
**影響を受けたテスト:**
- APT-003

### 4. 訪問者タイプ分類: 期待「sales」vs実際「appointment」 (発生回数: 1)
**影響を受けたテスト:**
- SALES-003

### 5. 必須キーワード「荷物」が応答に含まれていません (発生回数: 1)
**影響を受けたテスト:**
- DEL-001

## 🎯 具体的改善提案
## 📋 詳細テスト結果
### ✅ APT-001: 標準的な予約来客（時間・担当者明記）
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (appointment)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (154文字)
- appropriateness: ✅ 適切な表現

### ✅ APT-002: 時間指定なしの予約
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (appointment)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (168文字)
- appropriateness: ✅ 適切な表現

### ❌ APT-003: 予約が見つからないケース
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (appointment)
- politeness: ✅ 適切 (敬語表現4個)
- clarity: ✅ 適切な長さ (195文字)
- appropriateness: ✅ 適切な表現
**問題点:**
- 必須キーワード「担当者」が応答に含まれていません
- 必須キーワード「受付」が応答に含まれていません

### ✅ SALES-001: 標準的な営業訪問
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (sales)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (145文字)
- appropriateness: ✅ 適切な表現

### ✅ SALES-002: 商品紹介での営業訪問
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (sales)
- politeness: ✅ 適切 (敬語表現2個)
- clarity: ✅ 適切な長さ (115文字)
- appropriateness: ✅ 適切な表現

### ❌ SALES-003: 曖昧な営業表現
**信頼度**: 0.75
**詳細判定:**
- visitor_type_classification: ❌ 誤分類 (期待:sales, 実際:appointment)
- politeness: ✅ 適切 (敬語表現4個)
- clarity: ✅ 適切な長さ (102文字)
- appropriateness: ✅ 適切な表現
**問題点:**
- 訪問者タイプ分類: 期待「sales」vs実際「appointment」
- 必須キーワード「確認」が応答に含まれていません

### ❌ DEL-001: 標準的な配達
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (delivery)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (101文字)
- appropriateness: ✅ 適切な表現
**問題点:**
- 必須キーワード「荷物」が応答に含まれていません
- 必須キーワード「受付」が応答に含まれていません
- 必須キーワード「サイン」が応答に含まれていません

### ✅ DEL-002: 個人名なしの配達
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (delivery)
- politeness: ✅ 適切 (敬語表現5個)
- clarity: ✅ 適切な長さ (111文字)
- appropriateness: ✅ 適切な表現

### ❌ ERR-001: 情報不足による段階的エラー
**信頼度**: 1.00
**詳細判定:**
- politeness: ✅ 適切 (敬語表現4個)
- clarity: ✅ 適切な長さ (194文字)
- appropriateness: ✅ 適切な表現

### ✅ ERR-002: 情報訂正フロー
**信頼度**: 1.00
**詳細判定:**
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (142文字)
- appropriateness: ✅ 適切な表現

### ✅ ERR-003: 部分的な情報提供
**信頼度**: 1.00
**詳細判定:**
- politeness: ✅ 適切 (敬語表現4個)
- clarity: ✅ 適切な長さ (131文字)
- appropriateness: ✅ 適切な表現

### ❌ COMP-001: 複数の用件
**信頼度**: 0.75
**詳細判定:**
- visitor_type_classification: ❌ 誤分類 (期待:appointment, 実際:delivery)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (88文字)
- appropriateness: ✅ 適切な表現
**問題点:**
- 訪問者タイプ分類: 期待「appointment」vs実際「delivery」
- 必須キーワード「確認」が応答に含まれていません
- 必須キーワード「メイン」が応答に含まれていません
- 必須キーワード「主要」が応答に含まれていません

### ✅ COMP-002: 敬語なしの来客
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (appointment)
- politeness: ✅ 適切 (敬語表現3個)
- clarity: ✅ 適切な長さ (111文字)
- appropriateness: ✅ 適切な表現

### ✅ COMP-003: 長い説明の来客
**信頼度**: 1.00
**詳細判定:**
- visitor_type_classification: ✅ 正確 (appointment)
- politeness: ✅ 適切 (敬語表現2個)
- clarity: ✅ 適切な長さ (175文字)
- appropriateness: ✅ 適切な表現
