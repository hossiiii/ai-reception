#!/usr/bin/env python3
"""
データベースマイグレーション実行スクリプト

OpenAI Realtime API統合のためのデータベース拡張
"""

import sqlite3
import os
import sys
from pathlib import Path

def run_migration():
    """マイグレーションを実行"""
    
    # データベースパスとマイグレーションファイルパス
    db_path = "./data/realtime.db"
    migration_file = "./migrations/add_realtime_support.sql"
    
    # ディレクトリが存在しない場合は作成
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # マイグレーションファイルの存在確認
    if not os.path.exists(migration_file):
        print(f"❌ マイグレーションファイルが見つかりません: {migration_file}")
        return False
    
    try:
        # マイグレーションSQLを読み込み
        with open(migration_file, 'r', encoding='utf-8') as f:
            migration_sql = f.read()
        
        # SQLiteデータベースに接続してマイグレーションを実行
        with sqlite3.connect(db_path) as conn:
            # 実行日を置換
            from datetime import datetime
            migration_sql = migration_sql.replace("$(date)", datetime.now().isoformat())
            
            # SQLを分割して実行
            cursor = conn.cursor()
            
            # SQLを個別のステートメントに分割
            statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
            
            for i, statement in enumerate(statements):
                try:
                    cursor.execute(statement)
                    print(f"✅ Statement {i+1}/{len(statements)} executed successfully")
                except sqlite3.Error as e:
                    # テーブルやインデックスが既に存在する場合は警告として扱う
                    if "already exists" in str(e).lower():
                        print(f"⚠️ Statement {i+1}: {e} (continuing...)")
                    else:
                        print(f"❌ Statement {i+1} failed: {e}")
                        raise
            
            conn.commit()
            print(f"✅ マイグレーション完了: {db_path}")
            
            # テーブル一覧を表示
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"📋 作成されたテーブル: {[table[0] for table in tables]}")
            
            return True
            
    except Exception as e:
        print(f"❌ マイグレーション実行エラー: {e}")
        return False

def verify_database():
    """データベースの検証"""
    db_path = "./data/realtime.db"
    
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # 必要なテーブルの存在確認
            required_tables = [
                'sessions',
                'session_metrics',
                'system_metrics',
                'fallback_events',
                'function_call_logs',
                'feature_flags'
            ]
            
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [table[0] for table in cursor.fetchall()]
            
            missing_tables = []
            for table in required_tables:
                if table in existing_tables:
                    print(f"✅ テーブル確認: {table}")
                else:
                    print(f"❌ テーブル不足: {table}")
                    missing_tables.append(table)
            
            if missing_tables:
                print(f"❌ 不足しているテーブル: {missing_tables}")
                return False
            
            # フィーチャーフラグの初期データ確認
            cursor.execute("SELECT flag_name, enabled FROM feature_flags")
            flags = cursor.fetchall()
            
            if flags:
                print("📋 フィーチャーフラグ:")
                for flag_name, enabled in flags:
                    status = "有効" if enabled else "無効"
                    print(f"  - {flag_name}: {status}")
            else:
                print("⚠️ フィーチャーフラグが設定されていません")
            
            print("✅ データベース検証完了")
            return True
            
    except Exception as e:
        print(f"❌ データベース検証エラー: {e}")
        return False

def main():
    """メイン実行関数"""
    print("OpenAI Realtime API統合 - データベースマイグレーション")
    print("=" * 50)
    
    # カレントディレクトリを確認
    current_dir = os.getcwd()
    print(f"実行ディレクトリ: {current_dir}")
    
    # backendディレクトリに移動
    if not current_dir.endswith('backend'):
        backend_path = os.path.join(current_dir, 'backend')
        if os.path.exists(backend_path):
            os.chdir(backend_path)
            print(f"ディレクトリ変更: {backend_path}")
        else:
            print("❌ backendディレクトリが見つかりません")
            return False
    
    # マイグレーション実行
    print("\n1. マイグレーション実行中...")
    if not run_migration():
        print("❌ マイグレーションに失敗しました")
        return False
    
    # データベース検証
    print("\n2. データベース検証中...")
    if not verify_database():
        print("❌ データベース検証に失敗しました")
        return False
    
    print("\n🎉 データベースマイグレーションが正常に完了しました！")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)