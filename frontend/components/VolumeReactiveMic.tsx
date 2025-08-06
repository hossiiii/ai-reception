'use client';

interface VolumeReactiveMicProps {
  volume: number; // 0-1の範囲
  isActive: boolean;
  isRecording: boolean;
  status?: string; // ステータステキスト
  statusColor?: string; // ステータスの色クラス
}

export default function VolumeReactiveMic({ volume, isActive, isRecording, status, statusColor = 'text-gray-500' }: VolumeReactiveMicProps) {
  // 音量に基づいてサイズと色を計算
  const getSize = () => {
    const baseSize = 120;
    const sizeIncrease = volume * 20; // 拡大率を半分に
    return baseSize + sizeIncrease;
  };

  const getOpacity = () => {
    return 0.6 + (volume * 0.4);
  };

  const getColor = () => {
    if (!isRecording) return 'text-gray-400';
    if (volume > 0.7) return 'text-red-500';
    if (volume > 0.4) return 'text-yellow-500';
    if (volume > 0.1) return 'text-green-500';
    return 'text-blue-500';
  };

  const getGlowColor = () => {
    if (!isActive) return '';
    if (volume > 0.7) return 'shadow-red-500/50';
    if (volume > 0.4) return 'shadow-yellow-500/50';
    if (volume > 0.1) return 'shadow-green-500/50';
    return 'shadow-blue-500/50';
  };

  const size = getSize();

  return (
    <div className="flex flex-col items-center justify-center space-y-4">
      <div 
        className={`
          relative transition-all duration-200 ease-out rounded-full flex items-center justify-center
          ${isActive ? `shadow-2xl ${getGlowColor()}` : ''}
        `}
        style={{
          width: `${size}px`,
          height: `${size}px`,
          opacity: getOpacity()
        }}
      >
        {/* Outer ring for active state */}
        {isActive && (
          <div 
            className={`
              absolute inset-0 rounded-full border-2 animate-pulse
              ${getColor().replace('text-', 'border-')}
            `}
          />
        )}
        
        {/* Mic icon */}
        <svg
          className={`transition-all duration-200 ${getColor()}`}
          width={size * 0.5}
          height={size * 0.5}
          fill="currentColor"
          viewBox="0 0 24 24"
        >
          <path d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
        </svg>

        {/* Sound waves for active state */}
        {isActive && volume > 0.1 && (
          <>
            <div 
              className={`
                absolute rounded-full border-2 border-opacity-30 animate-ping
                ${getColor().replace('text-', 'border-')}
              `}
              style={{
                width: `${size + 20}px`,
                height: `${size + 20}px`,
                animationDuration: '1s'
              }}
            />
            {volume > 0.3 && (
              <div 
                className={`
                  absolute rounded-full border-2 border-opacity-20 animate-ping
                  ${getColor().replace('text-', 'border-')}
                `}
                style={{
                  width: `${size + 40}px`,
                  height: `${size + 40}px`,
                  animationDuration: '1.5s'
                }}
              />
            )}
            {volume > 0.5 && (
              <div 
                className={`
                  absolute rounded-full border-2 border-opacity-10 animate-ping
                  ${getColor().replace('text-', 'border-')}
                `}
                style={{
                  width: `${size + 60}px`,
                  height: `${size + 60}px`,
                  animationDuration: '2s'
                }}
              />
            )}
          </>
        )}
      </div>
      
      {/* Status label */}
      {status && (
        <div className={`text-lg font-medium transition-all duration-300 ${statusColor}`}>
          {status}
        </div>
      )}
    </div>
  );
}