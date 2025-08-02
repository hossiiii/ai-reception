"""
LLMベースAI受付システムのテストフレームワーク

目的：
- 想定した挙動になっているかを定量的・定性的に判定
- 問題点と具体的な改善アクションを明確化
- 修正前後の比較による改善確認
"""

import pytest
import asyncio
import yaml
import re
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import statistics
from pathlib import Path

@dataclass
class ExtractionResult:
    """情報抽出結果"""
    name: Optional[str] = None
    company: Optional[str] = None
    visitor_type: Optional[str] = None
    purpose: Optional[str] = None
    confidence: float = 0.0

@dataclass
class TestEvidence:
    """テスト証跡"""
    test_id: str
    input_message: str
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    passed: bool
    issues: List[str]
    timestamp: str

@dataclass
class ImprovementSuggestion:
    """改善提案"""
    category: str  # "prompt", "logic", "config"
    problem: str
    evidence: List[str]
    suggested_fix: str
    file_to_modify: str
    priority: str  # "high", "medium", "low"

@dataclass
class TestResult:
    """テスト結果（詳細な判断基準付き）"""
    test_id: str
    scenario_name: str
    overall_success: bool
    confidence_score: float
    
    # 詳細評価
    extraction_scores: Dict[str, float]  # name: 1.0, company: 1.0, visitor_type: 0.0
    flow_scores: Dict[str, float]        # state_transition: 1.0, error_handling: 0.5
    quality_scores: Dict[str, float]     # politeness: 0.9, clarity: 0.8
    
    # 判断詳細
    judgements: Dict[str, str]           # "name_extraction": "✅ 正確"
    issues: List[str]                    # 具体的な問題点
    evidence: TestEvidence
    
    # 改善提案
    suggestions: List[ImprovementSuggestion]

class DetailedValidator:
    """詳細な判断基準を提供するバリデーター"""
    
    def __init__(self):
        self.extraction_patterns = self._load_extraction_patterns()
        self.quality_criteria = self._load_quality_criteria()
    
    def _load_extraction_patterns(self) -> Dict[str, Any]:
        """情報抽出パターンの定義"""
        return {
            "name_patterns": [
                r"([ぁ-んァ-ヶー一-龠]{2,10})(?:です|と申します|といいます)",
                r"私は([ぁ-んァ-ヶー一-龠]{2,10})",
                r"([ぁ-んァ-ヶー一-龠]{2,10})(?:さん|様|氏)",
            ],
            "company_patterns": [
                r"([ぁ-んァ-ヶーa-zA-Z0-9]{2,20})(?:株式会社|会社|商事|グループ|Corp|Inc)",
                r"([ぁ-んァ-ヶーa-zA-Z0-9]{2,20})(?:から|より)(?:来|参)",
            ],
            "visitor_type_keywords": {
                "appointment": ["会議", "ミーティング", "打ち合わせ", "面談", "アポイント", "予約", "時"],
                "sales": ["営業", "案内", "紹介", "提案", "商品", "サービス", "新規"],
                "delivery": ["配達", "お届け", "荷物", "宅配", "運輸", "便"]
            }
        }
    
    def _load_quality_criteria(self) -> Dict[str, Any]:
        """品質基準の定義"""
        return {
            "politeness_indicators": ["です", "ます", "ございます", "いたします", "させていただき"],
            "clarity_indicators": ["確認", "お聞かせ", "教えて", "について"],
            "forbidden_phrases": ["わからない", "むり", "だめ"],  # "できません"を削除（正当な使用もある）
            "max_response_length": 250,  # より現実的な長さに変更
            "min_response_length": 20
        }
    
    def validate_extraction(self, actual: ExtractionResult, expected: Dict[str, Any]) -> Tuple[Dict[str, float], Dict[str, str], List[str]]:
        """情報抽出の詳細評価"""
        scores = {}
        judgements = {}
        issues = []
        
        # 名前の評価
        if "name" in expected:
            expected_name = expected["name"]
            if actual.name:
                if self._names_match(actual.name, expected_name):
                    scores["name"] = 1.0
                    judgements["name_extraction"] = f"✅ 正確 ({actual.name})"
                else:
                    scores["name"] = 0.5
                    judgements["name_extraction"] = f"⚠️ 部分的 (期待:{expected_name}, 実際:{actual.name})"
                    issues.append(f"名前抽出: 期待「{expected_name}」vs実際「{actual.name}」")
            else:
                scores["name"] = 0.0
                judgements["name_extraction"] = "❌ 抽出失敗"
                issues.append("名前が抽出されていません")
        
        # 会社名の評価
        if "company" in expected:
            expected_company = expected["company"]
            if actual.company:
                if self._companies_match(actual.company, expected_company):
                    scores["company"] = 1.0
                    judgements["company_extraction"] = f"✅ 正確 ({actual.company})"
                else:
                    scores["company"] = 0.5
                    judgements["company_extraction"] = f"⚠️ 部分的 (期待:{expected_company}, 実際:{actual.company})"
                    issues.append(f"会社名抽出: 期待「{expected_company}」vs実際「{actual.company}」")
            else:
                scores["company"] = 0.0
                judgements["company_extraction"] = "❌ 抽出失敗"
                issues.append("会社名が抽出されていません")
        
        # 訪問者タイプの評価
        if "visitor_type" in expected:
            expected_type = expected["visitor_type"]
            if actual.visitor_type == expected_type:
                scores["visitor_type"] = 1.0
                judgements["visitor_type_classification"] = f"✅ 正確 ({actual.visitor_type})"
            else:
                scores["visitor_type"] = 0.0
                judgements["visitor_type_classification"] = f"❌ 誤分類 (期待:{expected_type}, 実際:{actual.visitor_type})"
                issues.append(f"訪問者タイプ分類: 期待「{expected_type}」vs実際「{actual.visitor_type}」")
        
        return scores, judgements, issues
    
    def validate_response_quality(self, response_text: str) -> Tuple[Dict[str, float], Dict[str, str], List[str]]:
        """応答品質の詳細評価"""
        scores = {}
        judgements = {}
        issues = []
        
        # 丁寧さの評価
        politeness_count = sum(1 for phrase in self.quality_criteria["politeness_indicators"] 
                             if phrase in response_text)
        politeness_score = min(1.0, politeness_count / 2)  # 2つ以上で満点
        scores["politeness"] = politeness_score
        
        if politeness_score >= 0.8:
            judgements["politeness"] = f"✅ 適切 (敬語表現{politeness_count}個)"
        elif politeness_score >= 0.5:
            judgements["politeness"] = f"⚠️ 改善の余地 (敬語表現{politeness_count}個)"
        else:
            judgements["politeness"] = f"❌ 不適切 (敬語表現{politeness_count}個)"
            issues.append("敬語表現が不足しています")
        
        # 明確さの評価
        length = len(response_text)
        if self.quality_criteria["min_response_length"] <= length <= self.quality_criteria["max_response_length"]:
            scores["clarity"] = 1.0
            judgements["clarity"] = f"✅ 適切な長さ ({length}文字)"
        elif length > self.quality_criteria["max_response_length"]:
            scores["clarity"] = 0.6
            judgements["clarity"] = f"⚠️ 長すぎる ({length}文字)"
            issues.append(f"応答が長すぎます ({length}文字 > {self.quality_criteria['max_response_length']}文字)")
        else:
            scores["clarity"] = 0.4
            judgements["clarity"] = f"⚠️ 短すぎる ({length}文字)"
            issues.append(f"応答が短すぎます ({length}文字 < {self.quality_criteria['min_response_length']}文字)")
        
        # 禁止フレーズチェック
        forbidden_found = [phrase for phrase in self.quality_criteria["forbidden_phrases"] 
                          if phrase in response_text]
        if forbidden_found:
            scores["appropriateness"] = 0.0
            judgements["appropriateness"] = f"❌ 不適切な表現 ({', '.join(forbidden_found)})"
            issues.append(f"不適切な表現が含まれています: {', '.join(forbidden_found)}")
        else:
            scores["appropriateness"] = 1.0
            judgements["appropriateness"] = "✅ 適切な表現"
        
        return scores, judgements, issues
    
    def _names_match(self, actual: str, expected: str) -> bool:
        """名前の一致判定"""
        # 正規化して比較
        actual_norm = re.sub(r'[　\s]', '', actual)
        expected_norm = re.sub(r'[　\s]', '', expected)
        return actual_norm == expected_norm
    
    def _companies_match(self, actual: str, expected: str) -> bool:
        """会社名の一致判定"""
        # 会社表記の正規化
        actual_norm = self._normalize_company(actual)
        expected_norm = self._normalize_company(expected)
        return actual_norm == expected_norm
    
    def _normalize_company(self, company: str) -> str:
        """会社名の正規化"""
        normalized = re.sub(r'株式会社|有限会社|\(株\)|\(有\)|Co\.|Corp\.|Inc\.', '', company)
        normalized = re.sub(r'[　\s]', '', normalized)
        return normalized.strip()

class AnalysisEngine:
    """テスト結果の分析と改善提案エンジン"""
    
    def analyze_test_results(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """テスト結果の包括的分析"""
        analysis = {
            "overall_metrics": self._calculate_overall_metrics(test_results),
            "category_performance": self._analyze_by_category(test_results),
            "failure_patterns": self._identify_failure_patterns(test_results),
            "improvement_suggestions": self._generate_improvement_suggestions(test_results),
            "priority_actions": self._prioritize_actions(test_results)
        }
        return analysis
    
    def _calculate_overall_metrics(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """全体メトリクスの計算"""
        if not test_results:
            return {}
        
        success_rate = sum(1 for r in test_results if r.overall_success) / len(test_results)
        avg_confidence = statistics.mean(r.confidence_score for r in test_results)
        
        # カテゴリ別スコア
        extraction_scores = []
        quality_scores = []
        
        for result in test_results:
            if result.extraction_scores:
                extraction_scores.extend(result.extraction_scores.values())
            if result.quality_scores:
                quality_scores.extend(result.quality_scores.values())
        
        return {
            "total_tests": len(test_results),
            "success_rate": success_rate,
            "avg_confidence": avg_confidence,
            "avg_extraction_score": statistics.mean(extraction_scores) if extraction_scores else 0,
            "avg_quality_score": statistics.mean(quality_scores) if quality_scores else 0,
            "failed_tests": len(test_results) - sum(1 for r in test_results if r.overall_success)
        }
    
    def _analyze_by_category(self, test_results: List[TestResult]) -> Dict[str, Any]:
        """カテゴリ別の分析"""
        categories = {}
        
        for result in test_results:
            # テストIDからカテゴリを抽出 (例: APT-001 -> APT)
            category = result.test_id.split("-")[0] if "-" in result.test_id else "UNKNOWN"
            
            if category not in categories:
                categories[category] = {
                    "total": 0,
                    "success": 0,
                    "avg_confidence": 0.0,
                    "avg_extraction_score": 0.0,
                    "avg_quality_score": 0.0,
                    "test_ids": []
                }
            
            categories[category]["total"] += 1
            categories[category]["test_ids"].append(result.test_id)
            
            if result.overall_success:
                categories[category]["success"] += 1
            
            # スコアの累積
            categories[category]["avg_confidence"] += result.confidence_score
            
            if result.extraction_scores:
                avg_ext = statistics.mean(result.extraction_scores.values())
                categories[category]["avg_extraction_score"] += avg_ext
            
            if result.quality_scores:
                avg_qual = statistics.mean(result.quality_scores.values())
                categories[category]["avg_quality_score"] += avg_qual
        
        # 平均値を計算
        for category_data in categories.values():
            total = category_data["total"]
            if total > 0:
                category_data["success_rate"] = category_data["success"] / total
                category_data["avg_confidence"] /= total
                category_data["avg_extraction_score"] /= total
                category_data["avg_quality_score"] /= total
        
        return categories
    
    def _identify_failure_patterns(self, test_results: List[TestResult]) -> List[Dict[str, Any]]:
        """失敗パターンの特定"""
        patterns = {}
        
        for result in test_results:
            if not result.overall_success:
                for issue in result.issues:
                    if issue not in patterns:
                        patterns[issue] = {
                            "count": 0,
                            "test_ids": [],
                            "examples": []
                        }
                    patterns[issue]["count"] += 1
                    patterns[issue]["test_ids"].append(result.test_id)
                    patterns[issue]["examples"].append({
                        "input": result.evidence.input_message,
                        "expected": result.evidence.expected,
                        "actual": result.evidence.actual
                    })
        
        # 頻度順にソート
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1]["count"], reverse=True)
        
        return [
            {
                "pattern": pattern,
                "frequency": data["count"],
                "affected_tests": data["test_ids"],
                "examples": data["examples"][:3]  # 最大3例
            }
            for pattern, data in sorted_patterns
        ]
    
    def _generate_improvement_suggestions(self, test_results: List[TestResult]) -> List[ImprovementSuggestion]:
        """改善提案の生成"""
        suggestions = []
        
        # 全ての提案を収集
        for result in test_results:
            suggestions.extend(result.suggestions)
        
        # 重複除去と優先度付け
        unique_suggestions = {}
        for suggestion in suggestions:
            key = f"{suggestion.category}_{suggestion.problem}"
            if key not in unique_suggestions:
                unique_suggestions[key] = suggestion
            else:
                # 証拠を統合
                unique_suggestions[key].evidence.extend(suggestion.evidence)
        
        return list(unique_suggestions.values())

class TestReportGenerator:
    """テスト結果レポート生成器"""
    
    def generate_detailed_report(self, analysis: Dict[str, Any], test_results: List[TestResult]) -> str:
        """詳細レポートの生成"""
        report = []
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # ヘッダー
        report.append("# AI受付システム LLMテスト結果レポート")
        report.append(f"生成日時: {timestamp}\n")
        
        # エグゼクティブサマリー
        metrics = analysis["overall_metrics"]
        report.append("## 📊 エグゼクティブサマリー")
        report.append(f"- **全体成功率**: {metrics['success_rate']:.1%} ({metrics['total_tests'] - metrics['failed_tests']}/{metrics['total_tests']})")
        report.append(f"- **平均信頼度**: {metrics['avg_confidence']:.2f}")
        report.append(f"- **情報抽出精度**: {metrics['avg_extraction_score']:.1%}")
        report.append(f"- **応答品質**: {metrics['avg_quality_score']:.1%}")
        report.append("")
        
        # カテゴリ別パフォーマンス
        if "category_performance" in analysis:
            report.append("## 📈 カテゴリ別パフォーマンス")
            for category, perf in analysis["category_performance"].items():
                status = "✅" if perf["success_rate"] > 0.9 else "⚠️" if perf["success_rate"] > 0.7 else "❌"
                report.append(f"- {status} **{category}**: {perf['success_rate']:.1%}")
            report.append("")
        
        # 主要問題
        report.append("## ⚠️ 主要問題と改善アクション")
        for i, pattern in enumerate(analysis["failure_patterns"][:5], 1):
            report.append(f"### {i}. {pattern['pattern']} (発生回数: {pattern['frequency']})")
            report.append("**影響を受けたテスト:**")
            for test_id in pattern["affected_tests"][:3]:
                report.append(f"- {test_id}")
            if len(pattern["affected_tests"]) > 3:
                report.append(f"- ...他{len(pattern['affected_tests']) - 3}件")
            report.append("")
        
        # 改善提案
        report.append("## 🎯 具体的改善提案")
        high_priority = [s for s in analysis["improvement_suggestions"] if s.priority == "high"]
        for i, suggestion in enumerate(high_priority, 1):
            report.append(f"### {i}. {suggestion.problem}")
            report.append(f"**カテゴリ**: {suggestion.category}")
            report.append(f"**修正対象**: {suggestion.file_to_modify}")
            report.append(f"**提案内容**: {suggestion.suggested_fix}")
            report.append(f"**証拠**: {len(suggestion.evidence)}件のテストで確認")
            report.append("")
        
        # 詳細テスト結果
        report.append("## 📋 詳細テスト結果")
        for result in test_results:
            status = "✅" if result.overall_success else "❌"
            report.append(f"### {status} {result.test_id}: {result.scenario_name}")
            report.append(f"**信頼度**: {result.confidence_score:.2f}")
            
            # 判定詳細
            report.append("**詳細判定:**")
            for key, judgement in result.judgements.items():
                report.append(f"- {key}: {judgement}")
            
            if result.issues:
                report.append("**問題点:**")
                for issue in result.issues:
                    report.append(f"- {issue}")
            
            report.append("")
        
        return "\n".join(report)

# 使用例とテスト実行
async def run_example_test():
    """実行例"""
    validator = DetailedValidator()
    analyzer = AnalysisEngine()
    reporter = TestReportGenerator()
    
    # サンプルテスト結果
    sample_results = [
        TestResult(
            test_id="APT-001",
            scenario_name="標準的な予約来客",
            overall_success=True,
            confidence_score=0.95,
            extraction_scores={"name": 1.0, "company": 1.0, "visitor_type": 1.0},
            flow_scores={"state_transition": 1.0},
            quality_scores={"politeness": 0.9, "clarity": 0.8},
            judgements={
                "name_extraction": "✅ 正確 (田中太郎)",
                "company_extraction": "✅ 正確 (ABC商事)",
                "visitor_type_classification": "✅ 正確 (appointment)"
            },
            issues=[],
            evidence=TestEvidence(
                test_id="APT-001",
                input_message="田中太郎です。ABC商事から14時の山田部長との会議で来ました。",
                expected={"name": "田中太郎", "company": "ABC商事", "visitor_type": "appointment"},
                actual={"name": "田中太郎", "company": "ABC商事", "visitor_type": "appointment"},
                passed=True,
                issues=[],
                timestamp=datetime.now().isoformat()
            ),
            suggestions=[]
        )
    ]
    
    # 分析実行
    analysis = analyzer.analyze_test_results(sample_results)
    
    # レポート生成
    report = reporter.generate_detailed_report(analysis, sample_results)
    
    return report

if __name__ == "__main__":
    report = asyncio.run(run_example_test())
    print(report)