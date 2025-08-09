'use client';

interface VolumeReactiveMicProps {
  volume: number; // 0-1の範囲
  isActive: boolean;
  isRecording: boolean;
  status?: string; // ステータステキスト
  statusColor?: string; // ステータスの色クラス
  onClick?: () => void; // クリックハンドラー
  isClickable?: boolean; // クリック可能かどうか
}

export default function VolumeReactiveMic({ 
  volume, 
  isActive, 
  isRecording, 
  status, 
  statusColor = 'text-gray-500',
  onClick,
  isClickable = false
}: VolumeReactiveMicProps) {
  // 固定サイズに近い設定（ほぼ変化しない）
  const getSize = () => {
    const baseSize = 160; // ベースサイズ
    const sizeIncrease = volume * 5; // 音量による変化を最小限に（最大5px）
    return baseSize + sizeIncrease;
  };

  // 背景色で状態を表現
  const getBgColor = () => {
    if (!isRecording) return 'bg-gray-100';
    if (isActive) return 'bg-primary-100'; // 音声認識中は青系
    return 'bg-gray-100';
  };

  // ボーダー色で音声検出を表現
  const getBorderColor = () => {
    if (!isRecording) return 'border-gray-300';
    if (isActive && volume > 0.1) return 'border-primary-500 border-4'; // 音声検出時は太いボーダー
    if (isRecording) return 'border-primary-300 border-2'; // 待機中は細いボーダー
    return 'border-gray-300';
  };

  // アイコンの色
  const getIconColor = () => {
    if (!isRecording) return 'text-gray-400';
    if (isActive && volume > 0.1) return 'text-primary-600'; // 音声検出時は濃い青
    if (isRecording) return 'text-primary-500'; // 待機中は普通の青
    return 'text-gray-400';
  };

  const size = getSize();

  return (
    <div className="flex flex-col items-center justify-center space-y-6">
      <div className="relative">
        {/* メインの円形背景 */}
        <div 
          className={`
            relative transition-all duration-300 ease-out rounded-full flex items-center justify-center
            ${getBgColor()} ${getBorderColor()}
            ${isClickable ? 'cursor-pointer hover:shadow-lg' : ''}
          `}
          style={{
            width: `${size}px`,
            height: `${size}px`,
          }}
          onClick={isClickable ? onClick : undefined}
        >
          {/* 受付開始画面と同じアイコン */}
          <svg
            className={`transition-colors duration-300 ${getIconColor()}`}
            width={size * 0.4}
            height={size * 0.4}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
            />
          </svg>
        </div>

        {/* 音声認識中のアニメーション（パルス効果） */}
        {isActive && volume > 0.1 && (
          <div 
            className="absolute inset-0 rounded-full border-2 border-primary-400 animate-ping opacity-75"
            style={{
              animationDuration: '1.5s'
            }}
          />
        )}
      </div>
      
      {/* Status label */}
      {status && (
        <div className="text-center">
          <div className={`text-xl md:text-2xl font-semibold transition-all duration-300 ${statusColor}`}>
            {status}
          </div>
          {/* 補助テキスト */}
          {isRecording && (
            <div className="text-sm md:text-base text-gray-500 mt-2">
              {isActive && volume > 0.1 ? '音声を検出しています...' : 'お話しください'}
            </div>
          )}
        </div>
      )}
    </div>
  );
}