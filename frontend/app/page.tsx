import Link from 'next/link';

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 flex items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl w-full">
        {/* Main card */}
        <div className="card-lg text-center">
          {/* Logo/Icon */}
          <div className="w-24 h-24 md:w-32 md:h-32 lg:w-40 lg:h-40 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-8">
            <svg
              className="w-12 h-12 md:w-16 md:h-16 lg:w-20 lg:h-20 text-primary-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857M8 9a3 3 0 116 0 3 3 0 01-6 0z"
              />
            </svg>
          </div>

          {/* Welcome message */}
          <h1 className="text-5xl md:text-6xl font-bold text-gray-900 mb-6">
            AI受付システム
          </h1>
          
          <p className="text-2xl md:text-3xl text-gray-600 mb-10 leading-relaxed">
            来訪者管理のためのタブレット型AIシステム
          </p>

          {/* Features list */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 md:gap-8 lg:gap-10 mb-10">
            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">スマートな対話</h3>
                <p className="text-base text-gray-600">AIが来訪者と自然な会話を行います</p>
              </div>
            </div>

            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a1 1 0 011-1h6a1 1 0 011 1v4h3a1 1 0 011 1v9a1 1 0 01-1 1H5a1 1 0 01-1-1V8a1 1 0 011-1h3z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">予約確認</h3>
                <p className="text-base text-gray-600">Googleカレンダーと連携した予約チェック</p>
              </div>
            </div>

            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">自動通知</h3>
                <p className="text-base text-gray-600">Slackへの対応ログ自動送信</p>
              </div>
            </div>

            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">タイプ別案内</h3>
                <p className="text-base text-gray-600">予約、営業、配達に応じた適切な対応</p>
              </div>
            </div>

            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-green-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">ビデオ通話対応</h3>
                <p className="text-base text-gray-600">リモートでの直接対応が可能</p>
              </div>
            </div>

            <div className="flex items-start space-x-4 md:space-x-6">
              <div className="flex-shrink-0 w-8 h-8 md:w-10 md:h-10 bg-indigo-100 rounded-lg flex items-center justify-center">
                <svg className="w-5 h-5 md:w-6 md:h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="text-left">
                <h3 className="text-lg font-semibold text-gray-900 mb-2">24時間対応</h3>
                <p className="text-base text-gray-600">いつでも利用可能なタブレット受付</p>
              </div>
            </div>
          </div>

          {/* Action buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/reception"
              className="btn-primary-lg group"
            >
              <span>受付を開始</span>
              <svg
                className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M13 7l5 5m0 0l-5 5m5-5H6"
                />
              </svg>
            </Link>

            <Link
              href="/video-call"
              className="inline-flex items-center justify-center px-8 py-4 text-lg font-medium text-white bg-green-600 border border-transparent rounded-lg shadow-lg hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-all duration-200 group"
            >
              <span>ビデオ通話で受付</span>
              <svg
                className="ml-2 w-5 h-5 group-hover:translate-x-1 transition-transform"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                />
              </svg>
            </Link>
          </div>

          {/* Status indicator */}
          <div className="mt-10 pt-8 border-t border-gray-200">
            <div className="flex items-center justify-center space-x-3 text-lg text-gray-500">
              <div className="w-4 h-4 bg-green-500 rounded-full"></div>
              <span>システム稼働中</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}