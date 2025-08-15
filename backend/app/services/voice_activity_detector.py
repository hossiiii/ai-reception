import asyncio
from dataclasses import dataclass

import numpy as np


@dataclass
class VADConfig:
    """Configuration for Voice Activity Detection"""
    sample_rate: int = 16000  # Standard sample rate for voice processing
    frame_duration_ms: int = 30  # Frame duration in milliseconds
    energy_threshold: float = 0.01  # Energy threshold for voice detection
    silence_duration_ms: int = 1500  # Duration of silence to consider speech ended
    min_speech_duration_ms: int = 500  # Minimum speech duration to be considered valid
    max_speech_duration_ms: int = 30000  # Maximum speech duration (30 seconds)


@dataclass
class VADResult:
    """Result of voice activity detection"""
    is_speech: bool
    energy_level: float
    speech_ended: bool
    confidence: float
    duration_ms: int


class VoiceActivityDetector:
    """Voice Activity Detector optimized for Japanese speech patterns"""

    def __init__(self, config: VADConfig | None = None):
        self.config = config or VADConfig()
        self.frame_size = int(self.config.sample_rate * self.config.frame_duration_ms / 1000)
        self.silence_frames = int(self.config.silence_duration_ms / self.config.frame_duration_ms)
        self.min_speech_frames = int(self.config.min_speech_duration_ms / self.config.frame_duration_ms)
        self.max_speech_frames = int(self.config.max_speech_duration_ms / self.config.frame_duration_ms)

        # State tracking
        self.reset_state()

        print(f"✅ VAD initialized (threshold: {self.config.energy_threshold}, "
              f"silence: {self.config.silence_duration_ms}ms)")

    def reset_state(self):
        """Reset VAD state for new session"""
        self.consecutive_silence_frames = 0
        self.consecutive_speech_frames = 0
        self.total_speech_frames = 0
        self.is_in_speech = False
        self.speech_started = False
        self.energy_history: list[float] = []

    def calculate_energy(self, audio_chunk: bytes) -> float:
        """Calculate energy level of audio chunk"""
        try:
            # Check if chunk has valid size for 16-bit PCM
            if len(audio_chunk) % 2 != 0:
                # Pad with zero if odd number of bytes
                audio_chunk = audio_chunk + b'\x00'

            # Convert bytes to numpy array (assuming 16-bit PCM)
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16)

            # Handle empty audio data
            if len(audio_data) == 0:
                return 0.0

            # Normalize to [-1, 1] range
            audio_data = audio_data.astype(np.float32) / 32768.0

            # Calculate RMS energy
            energy = np.sqrt(np.mean(audio_data ** 2))

            return float(energy)

        except Exception as e:
            print(f"⚠️ Energy calculation error: {e}")
            return 0.0

    def detect_voice_activity(self, audio_chunk: bytes) -> VADResult:
        """
        Detect voice activity in audio chunk

        Args:
            audio_chunk: Raw audio data (16-bit PCM)

        Returns:
            VADResult: Voice activity detection result
        """
        energy = self.calculate_energy(audio_chunk)
        self.energy_history.append(energy)

        # Keep only recent energy history (last 2 seconds)
        max_history = int(2000 / self.config.frame_duration_ms)
        if len(self.energy_history) > max_history:
            self.energy_history = self.energy_history[-max_history:]

        # Determine if current frame contains speech
        is_speech = energy > self.config.energy_threshold

        # Update state counters
        if is_speech:
            self.consecutive_speech_frames += 1
            self.consecutive_silence_frames = 0

            if not self.is_in_speech and self.consecutive_speech_frames >= 2:
                # Speech started
                self.is_in_speech = True
                self.speech_started = True
                self.total_speech_frames = 0
                print(f"🎤 Speech detected (energy: {energy:.4f})")

            if self.is_in_speech:
                self.total_speech_frames += 1
        else:
            self.consecutive_silence_frames += 1
            self.consecutive_speech_frames = 0

        # Check for speech end conditions
        speech_ended = False
        if self.is_in_speech:
            # End speech if silence threshold reached
            if self.consecutive_silence_frames >= self.silence_frames:
                if self.total_speech_frames >= self.min_speech_frames:
                    speech_ended = True
                    print(f"🔇 Speech ended (duration: {self.total_speech_frames * self.config.frame_duration_ms}ms)")
                else:
                    print(f"⚠️ Speech too short, ignoring ({self.total_speech_frames * self.config.frame_duration_ms}ms)")

                self.is_in_speech = False
                self.total_speech_frames = 0

            # End speech if maximum duration reached
            elif self.total_speech_frames >= self.max_speech_frames:
                speech_ended = True
                print("⏰ Maximum speech duration reached, ending speech")
                self.is_in_speech = False
                self.total_speech_frames = 0

        # Calculate confidence based on energy consistency
        confidence = self._calculate_confidence(energy, is_speech)

        # Calculate current speech duration
        duration_ms = self.total_speech_frames * self.config.frame_duration_ms

        return VADResult(
            is_speech=self.is_in_speech,
            energy_level=energy,
            speech_ended=speech_ended,
            confidence=confidence,
            duration_ms=duration_ms
        )

    def _calculate_confidence(self, current_energy: float, is_speech: bool) -> float:
        """Calculate confidence score for VAD decision"""
        if len(self.energy_history) < 5:
            return 0.5  # Low confidence with insufficient history

        # Calculate energy statistics
        recent_energies = self.energy_history[-10:]  # Last 10 frames
        np.mean(recent_energies)
        energy_variance = np.var(recent_energies)

        # Base confidence on energy level relative to threshold
        if is_speech:
            # Higher confidence for stronger signals above threshold
            energy_ratio = current_energy / self.config.energy_threshold
            confidence = min(0.9, 0.5 + 0.4 * (energy_ratio - 1))
        else:
            # Higher confidence for signals well below threshold
            energy_ratio = current_energy / self.config.energy_threshold
            confidence = min(0.9, 0.5 + 0.4 * (1 - energy_ratio))

        # Adjust confidence based on consistency (low variance = higher confidence)
        variance_factor = max(0.5, 1.0 - energy_variance * 10)
        confidence *= variance_factor

        return max(0.1, min(0.9, confidence))

    async def process_audio_stream(self, audio_chunks: list[bytes]) -> list[VADResult]:
        """
        Process a stream of audio chunks

        Args:
            audio_chunks: List of audio data chunks

        Returns:
            List[VADResult]: VAD results for each chunk
        """
        results = []

        for chunk in audio_chunks:
            result = self.detect_voice_activity(chunk)
            results.append(result)

            # Small delay to simulate real-time processing
            await asyncio.sleep(0.001)

        return results

    def get_current_state(self) -> dict:
        """Get current VAD state for debugging/monitoring"""
        return {
            "is_in_speech": self.is_in_speech,
            "consecutive_speech_frames": self.consecutive_speech_frames,
            "consecutive_silence_frames": self.consecutive_silence_frames,
            "total_speech_frames": self.total_speech_frames,
            "current_energy": self.energy_history[-1] if self.energy_history else 0.0,
            "mean_energy": np.mean(self.energy_history) if self.energy_history else 0.0
        }


# Factory function for easy instantiation
def create_vad(
    energy_threshold: float = 0.01,
    silence_duration_ms: int = 1500,
    min_speech_duration_ms: int = 500
) -> VoiceActivityDetector:
    """Create VAD instance with custom parameters"""
    config = VADConfig(
        energy_threshold=energy_threshold,
        silence_duration_ms=silence_duration_ms,
        min_speech_duration_ms=min_speech_duration_ms
    )
    return VoiceActivityDetector(config)
