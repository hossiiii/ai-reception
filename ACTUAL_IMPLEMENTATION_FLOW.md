# AI受付システム - 実装フロー分析ドキュメント

## 📋 概要

このドキュメントは、AI受付システムの**実際のコード実装**に基づくフロー図と動作説明です。  
READMEに記載された設計フローと実装の差異も明記しています。

生成日: 2025-08-07

## 🔍 実装ファイル

- `backend/app/agents/nodes.py` - ノード実装
- `backend/app/agents/reception_graph.py` - グラフ定義とフロー制御

## 📊 実装フロー図（詳細版）

```mermaid
flowchart TD
    Start([セッション開始])
    
    Start --> greeting[greeting_node<br/>初回挨拶・情報収集依頼]
    
    greeting --> collect_all_info[collect_all_info_node<br/>AI情報抽出]
    
    collect_all_info --> info_check{全情報揃った？}
    
    info_check -->|いいえ| error_check{エラー回数 > 3？}
    error_check -->|いいえ| ask_missing[不足情報の<br/>再収集要求]
    error_check -->|はい| force_confirm[強制的に<br/>確認へ進む]
    
    ask_missing --> collect_all_info
    
    info_check -->|はい| confirmation_msg[確認メッセージ生成]
    force_confirm --> confirmation_msg
    
    confirmation_msg --> confirm_info[confirm_info_node<br/>情報確認]
    
    confirm_info --> user_response{ユーザー応答}
    
    user_response -->|確認OK| auto_type_detect[自動訪問タイプ判定<br/>purposeキーワード解析]
    user_response -->|修正要求| correction_flow[情報修正フロー]
    user_response -->|不明確| clarify_request[明確化要求]
    
    correction_flow --> collect_all_info
    clarify_request --> confirm_info
    
    auto_type_detect --> type_branch{訪問タイプ}
    
    type_branch -->|appointment| auto_calendar[🔄 自動実行<br/>check_appointment_node<br/>カレンダー確認]
    type_branch -->|sales| skip_calendar_sales[カレンダー確認スキップ]
    type_branch -->|delivery| skip_calendar_delivery[カレンダー確認スキップ]
    
    auto_calendar --> calendar_result{予約有無}
    
    calendar_result -->|予約あり| meeting_guidance[会議室案内生成]
    calendar_result -->|予約なし| no_appointment_guidance[予約なし案内生成]
    calendar_result -->|エラー| error_guidance[エラー案内生成]
    
    skip_calendar_sales --> sales_guidance[営業対応案内生成]
    skip_calendar_delivery --> delivery_guidance[配達対応案内生成]
    
    meeting_guidance --> auto_slack[🔄 自動実行<br/>send_slack_node<br/>Slack通知]
    no_appointment_guidance --> auto_slack
    error_guidance --> auto_slack
    sales_guidance --> auto_slack
    delivery_guidance --> auto_slack
    
    auto_slack --> End([セッション終了])
    
    style auto_type_detect fill:#ffe6e6
    style auto_calendar fill:#ffe6e6
    style auto_slack fill:#ffe6e6
```

## 🚀 自動実行される処理の詳細

### 1. confirm_info_node内の自動処理チェーン

```mermaid
flowchart LR
    subgraph "confirm_info_node内部"
        confirm[情報確認OK]
        
        confirm --> purpose_check{purpose<br/>設定済み？}
        
        purpose_check -->|はい| keyword_analysis[キーワード解析<br/>visitor_type自動判定]
        purpose_check -->|いいえ| ask_purpose[訪問目的質問]
        
        keyword_analysis --> type_set[visitor_type設定]
        
        type_set --> appointment_flow{type ==<br/>appointment？}
        
        appointment_flow -->|はい| exec_calendar[check_appointment_node<br/>即座に実行]
        appointment_flow -->|いいえ| exec_guidance[guide_visitor_node<br/>即座に実行]
        
        exec_calendar --> cal_complete[カレンダー確認完了]
        cal_complete --> exec_guidance2[guide_visitor_node<br/>即座に実行]
        
        exec_guidance --> slack_check{current_step ==<br/>complete？}
        exec_guidance2 --> slack_check
        
        slack_check -->|はい| exec_slack[send_slack_node<br/>即座に実行]
        slack_check -->|いいえ| return_state[状態を返す]
        
        exec_slack --> final_return[最終状態を返す]
    end
    
    style keyword_analysis fill:#ffcccc
    style exec_calendar fill:#ffcccc
    style exec_guidance fill:#ffcccc
    style exec_slack fill:#ffcccc
```

## 📝 訪問タイプ判定ロジック

### キーワードマッピング（nodes.py 346-355行目）

| 訪問タイプ | 判定キーワード | 処理フロー |
|------------|---------------|------------|
| **appointment** | 予約, 会議, 打ち合わせ, アポ, appointment, ミーティング | カレンダー確認 → 案内 → Slack |
| **sales** | 営業, 商談, 提案, sales, セールス | 案内 → Slack |
| **delivery** | 配達, 荷物, 宅配, delivery, 配送 | 案内 → Slack |
| **デフォルト** | 上記以外すべて | appointment扱い（カレンダー確認実行） |

## ⚠️ 実装上の問題点

### 1. 過度な自動実行

**問題箇所**: `confirm_info_node` (nodes.py 362-406行目)

```python
# 問題のコード構造
if visitor_type == "appointment":
    # カレンダー確認を自動実行
    calendar_result = await self.check_appointment_node(updated_state)
    # その後、案内も自動実行
    guidance_result = await self.guide_visitor_node(calendar_result)
    # さらにSlack通知も自動実行
    slack_result = await self.send_slack_node(guidance_result)
    return slack_result
```

**影響**:
- ユーザーが「はい」と確認しただけで、全処理が一気に完了
- 中間での確認や修正機会なし
- エラー時の回復が困難

### 2. 誤った自動処理の可能性

**シナリオ例**:
1. 配達業者が「荷物の配達で来ました」と言う
2. システムが正しく`delivery`と判定
3. しかし、デフォルト処理でカレンダー確認が実行される場合がある

### 3. process_visitor_type_nodeの到達不可能性

**問題**: 
- `confirm_info_node`で訪問タイプを自動判定し、即座に後続処理を実行
- `process_visitor_type_node`は実際には呼ばれない
- `reception_graph.py`のルーティングが機能していない

## 🔄 実際の処理フロー（簡略版）

```mermaid
stateDiagram-v2
    [*] --> greeting: 開始
    
    greeting --> collect_all_info: 情報収集
    
    collect_all_info --> collect_all_info: 情報不足（ループ）
    collect_all_info --> confirm_info: 情報完備
    
    confirm_info --> collect_all_info: 修正要求
    confirm_info --> AutoProcess: 確認OK
    
    state AutoProcess {
        [*] --> TypeDetect: 訪問タイプ自動判定
        TypeDetect --> CalendarCheck: appointment
        TypeDetect --> Guidance: sales/delivery
        CalendarCheck --> Guidance: 完了
        Guidance --> SlackNotify: 完了
        SlackNotify --> [*]
    }
    
    AutoProcess --> [*]: 完了
```

## 💡 改善提案

### 1. 段階的な確認フロー
- 各処理段階でユーザー確認を挟む
- 自動実行を減らし、対話的な処理に変更

### 2. 明確な訪問タイプ選択
- purposeからの自動判定に頼らず、明示的な選択を促す
- 判定後の確認ステップを追加

### 3. エラーリカバリーの強化
- 各段階でのキャンセル・修正機能
- タイムアウト処理の追加

## 📌 まとめ

現在の実装は、**確認完了後にすべての処理が自動実行される**設計になっています。これにより：

✅ **メリット**:
- 高速な処理完了
- 最小限のユーザー入力
- シームレスな体験

❌ **デメリット**:
- 誤判定時の修正困難
- 配達・営業でも不要なカレンダー確認の可能性
- ユーザーコントロールの欠如

設計図（README）と実装の主な相違点は、**自動実行の範囲**と**訪問タイプ判定の処理位置**にあります。