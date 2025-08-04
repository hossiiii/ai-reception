'use client';

import { useEffect, useRef, useState } from 'react';

export interface AudioVisualizerProps {
  isActive: boolean;
  energy: number; // 0-100
  volume: number; // 0-100
  confidence: number; // 0-1
  isRecording: boolean;
  isPlaying: boolean;
  className?: string;
}

export default function AudioVisualizer({
  isActive,
  energy,
  volume,
  confidence,
  isRecording,
  isPlaying,
  className = ''
}: AudioVisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | null>(null);
  const [waveData, setWaveData] = useState<number[]>(new Array(50).fill(0));

  // Update wave data based on volume
  useEffect(() => {
    if (isRecording || isPlaying) {
      setWaveData(prev => {
        const newData = [...prev.slice(1), volume];
        return newData;
      });
    }
  }, [volume, isRecording, isPlaying]);

  // Animation loop for drawing waveform
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const draw = () => {
      const { width, height } = canvas;
      
      // Clear canvas
      ctx.clearRect(0, 0, width, height);

      // Set canvas size to match display size
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);

      const canvasWidth = rect.width;
      const canvasHeight = rect.height;

      // Draw background
      const bgColor = isActive ? 'rgba(16, 185, 129, 0.1)' : 'rgba(156, 163, 175, 0.1)';
      ctx.fillStyle = bgColor;
      ctx.fillRect(0, 0, canvasWidth, canvasHeight);

      // Draw center line
      ctx.strokeStyle = 'rgba(156, 163, 175, 0.3)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(0, canvasHeight / 2);
      ctx.lineTo(canvasWidth, canvasHeight / 2);
      ctx.stroke();

      // Draw waveform
      if (isRecording || isPlaying) {
        const barWidth = canvasWidth / waveData.length;
        
        for (let i = 0; i < waveData.length; i++) {
          const barHeight = (waveData[i] / 100) * (canvasHeight * 0.8);
          const x = i * barWidth;
          
          // Color based on activity and confidence
          let barColor = 'rgba(156, 163, 175, 0.6)'; // Gray default
          
          if (isPlaying) {
            barColor = 'rgba(59, 130, 246, 0.8)'; // Blue for playback
          } else if (isActive && confidence > 0.5) {
            barColor = 'rgba(16, 185, 129, 0.8)'; // Green for confident speech
          } else if (isActive) {
            barColor = 'rgba(245, 158, 11, 0.8)'; // Yellow for uncertain speech
          }

          ctx.fillStyle = barColor;
          ctx.fillRect(
            x + barWidth * 0.1,
            (canvasHeight - barHeight) / 2,
            barWidth * 0.8,
            barHeight
          );
        }
      }

      // Draw energy indicator (circular meter)
      if (isRecording) {
        const centerX = canvasWidth - 40;
        const centerY = 30;
        const radius = 20;

        // Background circle
        ctx.strokeStyle = 'rgba(156, 163, 175, 0.3)';
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.stroke();

        // Energy arc
        const energyAngle = (energy / 100) * 2 * Math.PI;
        const energyColor = isActive ? 'rgba(16, 185, 129, 0.8)' : 'rgba(245, 158, 11, 0.8)';
        
        ctx.strokeStyle = energyColor;
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -Math.PI / 2, -Math.PI / 2 + energyAngle);
        ctx.stroke();

        // Center dot
        ctx.fillStyle = isActive ? 'rgba(16, 185, 129, 1)' : 'rgba(156, 163, 175, 0.8)';
        ctx.beginPath();
        ctx.arc(centerX, centerY, 4, 0, 2 * Math.PI);
        ctx.fill();
      }

      animationRef.current = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [waveData, isActive, energy, confidence, isRecording, isPlaying]);

  // Generate pulse animation for recording state
  const pulseScale = isRecording && isActive ? 1 + (confidence * 0.1) : 1;

  return (
    <div className={`relative ${className}`}>
      {/* Main visualizer canvas */}
      <div 
        className="relative border border-gray-200 rounded-lg bg-gray-50 overflow-hidden transition-all duration-200"
        style={{ transform: `scale(${pulseScale})` }}
      >
        <canvas
          ref={canvasRef}
          className="w-full h-24"
          style={{ display: 'block' }}
        />
        
        {/* Status overlay */}
        <div className="absolute top-2 left-2 flex items-center space-x-2">
          {isRecording && (
            <div className="flex items-center space-x-1">
              <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500' : 'bg-yellow-500'} animate-pulse`} />
              <span className="text-xs text-gray-600 font-medium">
                {isActive ? 'Speaking' : 'Listening'}
              </span>
            </div>
          )}
          
          {isPlaying && (
            <div className="flex items-center space-x-1">
              <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse" />
              <span className="text-xs text-gray-600 font-medium">Playing</span>
            </div>
          )}
          
          {!isRecording && !isPlaying && (
            <span className="text-xs text-gray-400">Ready</span>
          )}
        </div>
      </div>

      {/* Stats display */}
      <div className="mt-2 grid grid-cols-3 gap-2 text-xs">
        <div className="text-center">
          <div className="text-gray-500">Volume</div>
          <div className="font-mono text-gray-700">{Math.round(volume)}</div>
        </div>
        <div className="text-center">
          <div className="text-gray-500">Energy</div>
          <div className="font-mono text-gray-700">{Math.round(energy)}</div>
        </div>
        <div className="text-center">
          <div className="text-gray-500">Confidence</div>
          <div className="font-mono text-gray-700">{Math.round(confidence * 100)}%</div>
        </div>
      </div>

      {/* Level meters */}
      <div className="mt-2 space-y-1">
        {/* Volume meter */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 w-12">Vol</span>
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-100"
              style={{ width: `${volume}%` }}
            />
          </div>
        </div>

        {/* Energy meter */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 w-12">Energy</span>
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all duration-100 ${
                isActive ? 'bg-green-500' : 'bg-yellow-500'
              }`}
              style={{ width: `${energy}%` }}
            />
          </div>
        </div>

        {/* Confidence meter */}
        <div className="flex items-center space-x-2">
          <span className="text-xs text-gray-500 w-12">Conf</span>
          <div className="flex-1 bg-gray-200 rounded-full h-2">
            <div 
              className="bg-purple-500 h-2 rounded-full transition-all duration-100"
              style={{ width: `${confidence * 100}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}