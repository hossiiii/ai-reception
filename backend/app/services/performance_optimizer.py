"""
パフォーマンス最適化サービス

Phase 3の最適化機能:
1. 音声処理レイテンシ最小化
2. メモリ使用量最適化
3. CPU効率改善
4. ネットワーク帯域幅最適化
"""

import asyncio
import time
import psutil
import gc
import threading
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque
import numpy as np
from concurrent.futures import ThreadPoolExecutor
import weakref


@dataclass
class PerformanceMetrics:
    """パフォーマンスメトリクス"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    audio_latency_ms: float
    processing_time_ms: float
    active_sessions: int
    queue_size: int


@dataclass
class AudioBuffer:
    """最適化された音声バッファ"""
    data: bytes
    timestamp: float
    session_id: str
    chunk_id: int
    compressed: bool = False
    
    def __post_init__(self):
        self.size = len(self.data)


class AudioBufferPool:
    """音声バッファプール（メモリ最適化）"""
    
    def __init__(self, max_buffers: int = 100, max_buffer_size: int = 64 * 1024):
        self.max_buffers = max_buffers
        self.max_buffer_size = max_buffer_size
        self.available_buffers: deque = deque()
        self.active_buffers: weakref.WeakSet = weakref.WeakSet()
        self._lock = threading.Lock()
        
    def get_buffer(self, session_id: str, data: bytes) -> AudioBuffer:
        """バッファを取得（再利用最適化）"""
        with self._lock:
            if self.available_buffers and len(data) <= self.max_buffer_size:
                # 既存バッファを再利用
                buffer = self.available_buffers.popleft()
                buffer.data = data
                buffer.session_id = session_id
                buffer.timestamp = time.time()
                buffer.chunk_id = getattr(buffer, 'chunk_id', 0) + 1
            else:
                # 新しいバッファを作成
                buffer = AudioBuffer(
                    data=data,
                    session_id=session_id,
                    timestamp=time.time(),
                    chunk_id=0
                )
            
            self.active_buffers.add(buffer)
            return buffer
    
    def return_buffer(self, buffer: AudioBuffer):
        """バッファを返却（再利用のため）"""
        with self._lock:
            if len(self.available_buffers) < self.max_buffers:
                buffer.data = b''  # データをクリア
                buffer.session_id = ''
                self.available_buffers.append(buffer)
            
            self.active_buffers.discard(buffer)
    
    def cleanup(self):
        """古いバッファのクリーンアップ"""
        current_time = time.time()
        cleanup_threshold = 300  # 5分
        
        with self._lock:
            # 古いバッファを削除
            active_buffers_copy = list(self.active_buffers)
            for buffer in active_buffers_copy:
                if current_time - buffer.timestamp > cleanup_threshold:
                    self.active_buffers.discard(buffer)


class AdaptiveAudioProcessor:
    """適応的音声処理（レイテンシ最適化）"""
    
    def __init__(self):
        self.processing_times = deque(maxlen=100)
        self.optimal_chunk_size = 16 * 1024  # 初期値
        self.min_chunk_size = 4 * 1024
        self.max_chunk_size = 64 * 1024
        self.target_latency_ms = 100
        
    def optimize_chunk_size(self, current_latency_ms: float) -> int:
        """レイテンシに基づいてチャンクサイズを最適化"""
        self.processing_times.append(current_latency_ms)
        
        if len(self.processing_times) < 10:
            return self.optimal_chunk_size
        
        avg_latency = sum(self.processing_times) / len(self.processing_times)
        
        if avg_latency > self.target_latency_ms * 1.5:
            # レイテンシが高い場合、チャンクサイズを小さくする
            self.optimal_chunk_size = max(
                self.min_chunk_size,
                int(self.optimal_chunk_size * 0.8)
            )
        elif avg_latency < self.target_latency_ms * 0.7:
            # レイテンシが低い場合、チャンクサイズを大きくする
            self.optimal_chunk_size = min(
                self.max_chunk_size,
                int(self.optimal_chunk_size * 1.2)
            )
        
        return self.optimal_chunk_size
    
    def process_audio_optimized(self, audio_data: bytes, session_id: str) -> Tuple[List[bytes], float]:
        """最適化された音声処理"""
        start_time = time.time()
        
        # チャンクサイズに基づいて分割
        chunk_size = self.optimal_chunk_size
        chunks = []
        
        for i in range(0, len(audio_data), chunk_size):
            chunk = audio_data[i:i + chunk_size]
            chunks.append(chunk)
        
        processing_time = (time.time() - start_time) * 1000
        self.optimize_chunk_size(processing_time)
        
        return chunks, processing_time


class MemoryManager:
    """メモリ管理最適化"""
    
    def __init__(self, memory_threshold_percent: float = 80.0):
        self.memory_threshold = memory_threshold_percent
        self.cleanup_interval = 60  # 60秒間隔
        self.last_cleanup = time.time()
        
    def check_memory_usage(self) -> Dict[str, Any]:
        """メモリ使用量チェック"""
        memory = psutil.virtual_memory()
        
        return {
            "total_mb": memory.total / 1024 / 1024,
            "used_mb": memory.used / 1024 / 1024,
            "available_mb": memory.available / 1024 / 1024,
            "percent": memory.percent,
            "needs_cleanup": memory.percent > self.memory_threshold
        }
    
    def force_garbage_collection(self) -> Dict[str, Any]:
        """強制ガベージコレクション"""
        before_objects = len(gc.get_objects())
        before_memory = psutil.virtual_memory().used / 1024 / 1024
        
        # ガベージコレクション実行
        collected = gc.collect()
        
        after_objects = len(gc.get_objects())
        after_memory = psutil.virtual_memory().used / 1024 / 1024
        
        return {
            "collected_objects": collected,
            "objects_before": before_objects,
            "objects_after": after_objects,
            "memory_freed_mb": before_memory - after_memory,
            "memory_before_mb": before_memory,
            "memory_after_mb": after_memory
        }
    
    def should_cleanup(self) -> bool:
        """クリーンアップが必要かチェック"""
        current_time = time.time()
        memory_info = self.check_memory_usage()
        
        return (
            memory_info["needs_cleanup"] or
            current_time - self.last_cleanup > self.cleanup_interval
        )
    
    def perform_cleanup(self) -> Dict[str, Any]:
        """メモリクリーンアップ実行"""
        if not self.should_cleanup():
            return {"skipped": True, "reason": "cleanup_not_needed"}
        
        cleanup_result = self.force_garbage_collection()
        self.last_cleanup = time.time()
        
        return cleanup_result


class CPUOptimizer:
    """CPU最適化"""
    
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or min(8, psutil.cpu_count())
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.cpu_usage_history = deque(maxlen=60)  # 1分間の履歴
        
    def get_cpu_usage(self) -> float:
        """CPU使用率取得"""
        cpu_percent = psutil.cpu_percent(interval=0.1)
        self.cpu_usage_history.append(cpu_percent)
        return cpu_percent
    
    def is_cpu_under_pressure(self) -> bool:
        """CPU負荷が高いかチェック"""
        if len(self.cpu_usage_history) < 10:
            return False
        
        recent_usage = list(self.cpu_usage_history)[-10:]
        avg_usage = sum(recent_usage) / len(recent_usage)
        
        return avg_usage > 70.0  # 70%を閾値とする
    
    def get_optimal_concurrency(self) -> int:
        """最適な並行処理数を計算"""
        if self.is_cpu_under_pressure():
            return max(1, self.max_workers // 2)
        else:
            return self.max_workers
    
    async def process_async_with_optimization(self, func, *args, **kwargs):
        """最適化された非同期処理"""
        loop = asyncio.get_event_loop()
        
        if self.is_cpu_under_pressure():
            # CPU負荷が高い場合は順次処理
            return func(*args, **kwargs)
        else:
            # 通常時は並行処理
            return await loop.run_in_executor(self.executor, func, *args, **kwargs)


class NetworkOptimizer:
    """ネットワーク最適化"""
    
    def __init__(self):
        self.compression_threshold = 1024  # 1KB以上で圧縮検討
        self.bandwidth_history = deque(maxlen=30)
        
    def estimate_bandwidth(self, data_size: int, transfer_time: float) -> float:
        """帯域幅推定"""
        if transfer_time <= 0:
            return 0
        
        bandwidth_bps = (data_size * 8) / transfer_time  # bits per second
        bandwidth_mbps = bandwidth_bps / 1024 / 1024
        
        self.bandwidth_history.append(bandwidth_mbps)
        return bandwidth_mbps
    
    def should_compress_audio(self, audio_size: int) -> bool:
        """音声データを圧縮すべきかチェック"""
        if audio_size < self.compression_threshold:
            return False
        
        if len(self.bandwidth_history) < 5:
            return audio_size > 10 * 1024  # 10KB以上で圧縮
        
        avg_bandwidth = sum(self.bandwidth_history) / len(self.bandwidth_history)
        
        # 帯域幅が低い場合は積極的に圧縮
        return avg_bandwidth < 1.0 or audio_size > 50 * 1024
    
    def optimize_chunk_transmission(self, data: bytes, target_latency_ms: float = 100) -> List[bytes]:
        """チャンク転送最適化"""
        if len(self.bandwidth_history) < 3:
            # 初期状態では標準チャンクサイズ
            chunk_size = 16 * 1024
        else:
            avg_bandwidth = sum(self.bandwidth_history) / len(self.bandwidth_history)
            
            # 帯域幅に基づいてチャンクサイズを調整
            if avg_bandwidth > 10:  # 高帯域
                chunk_size = 64 * 1024
            elif avg_bandwidth > 1:  # 中帯域
                chunk_size = 32 * 1024
            else:  # 低帯域
                chunk_size = 8 * 1024
        
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        
        return chunks


class PerformanceOptimizer:
    """統合パフォーマンス最適化サービス"""
    
    def __init__(self):
        self.buffer_pool = AudioBufferPool()
        self.audio_processor = AdaptiveAudioProcessor()
        self.memory_manager = MemoryManager()
        self.cpu_optimizer = CPUOptimizer()
        self.network_optimizer = NetworkOptimizer()
        
        # メトリクス収集
        self.metrics_history = deque(maxlen=1000)
        self.optimization_enabled = True
        
        print("✅ PerformanceOptimizer initialized")
    
    async def optimize_audio_processing(self, audio_data: bytes, session_id: str) -> Dict[str, Any]:
        """音声処理最適化"""
        start_time = time.time()
        
        try:
            # メモリチェック
            if self.memory_manager.should_cleanup():
                cleanup_result = self.memory_manager.perform_cleanup()
                print(f"🧹 Memory cleanup: freed {cleanup_result.get('memory_freed_mb', 0):.2f}MB")
            
            # 音声データの最適化処理
            buffer = self.buffer_pool.get_buffer(session_id, audio_data)
            
            # CPUの状態に応じて処理方法を選択
            if self.cpu_optimizer.is_cpu_under_pressure():
                # 高負荷時はシンプルな処理
                chunks, processing_time = await self._simple_audio_processing(audio_data)
            else:
                # 通常時は最適化処理
                chunks, processing_time = await self._optimized_audio_processing(audio_data, session_id)
            
            # ネットワーク最適化
            if self.network_optimizer.should_compress_audio(len(audio_data)):
                chunks = await self._compress_audio_chunks(chunks)
                compression_applied = True
            else:
                compression_applied = False
            
            # バッファ返却
            self.buffer_pool.return_buffer(buffer)
            
            total_time = (time.time() - start_time) * 1000
            
            # メトリクス記録
            await self._record_performance_metrics(total_time, len(audio_data))
            
            return {
                "success": True,
                "chunks": chunks,
                "processing_time_ms": total_time,
                "audio_processing_time_ms": processing_time,
                "compression_applied": compression_applied,
                "chunk_count": len(chunks),
                "optimization_level": "high" if not self.cpu_optimizer.is_cpu_under_pressure() else "conservative"
            }
            
        except Exception as e:
            print(f"❌ Audio processing optimization error: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_processing": True
            }
    
    async def _simple_audio_processing(self, audio_data: bytes) -> Tuple[List[bytes], float]:
        """シンプルな音声処理（高負荷時）"""
        start_time = time.time()
        
        # 単純な固定サイズ分割
        chunk_size = 16 * 1024
        chunks = []
        for i in range(0, len(audio_data), chunk_size):
            chunks.append(audio_data[i:i + chunk_size])
        
        processing_time = (time.time() - start_time) * 1000
        return chunks, processing_time
    
    async def _optimized_audio_processing(self, audio_data: bytes, session_id: str) -> Tuple[List[bytes], float]:
        """最適化された音声処理"""
        return await self.cpu_optimizer.process_async_with_optimization(
            self.audio_processor.process_audio_optimized,
            audio_data,
            session_id
        )
    
    async def _compress_audio_chunks(self, chunks: List[bytes]) -> List[bytes]:
        """音声チャンクの圧縮"""
        # 簡単な圧縮実装（実際のプロダクションではより高度な圧縮を使用）
        import zlib
        
        compressed_chunks = []
        for chunk in chunks:
            if len(chunk) > 512:  # 小さなチャンクは圧縮しない
                try:
                    compressed = zlib.compress(chunk, level=1)  # 高速圧縮
                    if len(compressed) < len(chunk) * 0.9:  # 圧縮効果があるなら使用
                        compressed_chunks.append(compressed)
                    else:
                        compressed_chunks.append(chunk)
                except:
                    compressed_chunks.append(chunk)
            else:
                compressed_chunks.append(chunk)
        
        return compressed_chunks
    
    async def _record_performance_metrics(self, processing_time_ms: float, audio_size: int):
        """パフォーマンスメトリクス記録"""
        try:
            memory_info = self.memory_manager.check_memory_usage()
            cpu_usage = self.cpu_optimizer.get_cpu_usage()
            
            metrics = PerformanceMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_usage,
                memory_percent=memory_info["percent"],
                memory_mb=memory_info["used_mb"],
                audio_latency_ms=processing_time_ms,
                processing_time_ms=processing_time_ms,
                active_sessions=len(self.buffer_pool.active_buffers),
                queue_size=len(self.buffer_pool.available_buffers)
            )
            
            self.metrics_history.append(metrics)
            
        except Exception as e:
            print(f"⚠️ Metrics recording error: {e}")
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """パフォーマンス要約取得"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = list(self.metrics_history)[-10:]  # 最新10件
        
        avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
        avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
        avg_latency = sum(m.audio_latency_ms for m in recent_metrics) / len(recent_metrics)
        
        return {
            "timestamp": time.time(),
            "optimization_enabled": self.optimization_enabled,
            "performance": {
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_memory_percent": round(avg_memory, 2),
                "avg_audio_latency_ms": round(avg_latency, 2),
                "current_chunk_size": self.audio_processor.optimal_chunk_size,
                "active_buffers": len(self.buffer_pool.active_buffers),
                "cpu_under_pressure": self.cpu_optimizer.is_cpu_under_pressure()
            },
            "memory": self.memory_manager.check_memory_usage(),
            "network": {
                "bandwidth_history_count": len(self.network_optimizer.bandwidth_history),
                "compression_threshold": self.network_optimizer.compression_threshold
            },
            "optimizations_applied": {
                "adaptive_chunk_sizing": True,
                "memory_pooling": True,
                "cpu_load_balancing": True,
                "network_compression": True
            }
        }
    
    async def adjust_optimization_level(self, level: str) -> Dict[str, Any]:
        """最適化レベル調整"""
        if level == "aggressive":
            self.audio_processor.target_latency_ms = 50
            self.memory_manager.memory_threshold = 90.0
            self.network_optimizer.compression_threshold = 512
            
        elif level == "balanced":
            self.audio_processor.target_latency_ms = 100
            self.memory_manager.memory_threshold = 80.0
            self.network_optimizer.compression_threshold = 1024
            
        elif level == "conservative":
            self.audio_processor.target_latency_ms = 200
            self.memory_manager.memory_threshold = 70.0
            self.network_optimizer.compression_threshold = 2048
            
        return {
            "success": True,
            "optimization_level": level,
            "settings": {
                "target_latency_ms": self.audio_processor.target_latency_ms,
                "memory_threshold": self.memory_manager.memory_threshold,
                "compression_threshold": self.network_optimizer.compression_threshold
            }
        }
    
    async def cleanup_resources(self):
        """リソースクリーンアップ"""
        try:
            # バッファプールクリーンアップ
            self.buffer_pool.cleanup()
            
            # メモリクリーンアップ
            cleanup_result = self.memory_manager.perform_cleanup()
            
            # CPU最適化のシャットダウン
            self.cpu_optimizer.executor.shutdown(wait=False)
            
            print(f"🧹 Performance optimizer cleanup completed")
            return {
                "success": True,
                "memory_freed_mb": cleanup_result.get("memory_freed_mb", 0)
            }
            
        except Exception as e:
            print(f"❌ Cleanup error: {e}")
            return {"success": False, "error": str(e)}


# グローバルインスタンス
performance_optimizer = PerformanceOptimizer()


async def get_performance_optimizer() -> PerformanceOptimizer:
    """パフォーマンス最適化サービス取得"""
    return performance_optimizer