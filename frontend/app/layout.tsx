import type { Metadata, Viewport } from 'next';
import Link from 'next/link';
import './globals.css';

export const metadata: Metadata = {
  title: 'AI Reception System',
  description: 'Tablet-based AI reception system for visitor management',
  keywords: ['AI', 'reception', 'visitor', 'management', 'tablet'],
  authors: [{ name: 'AI Reception Team' }],
  creator: 'AI Reception System',
  publisher: 'AI Reception System',
  formatDetection: {
    email: false,
    address: false,
    telephone: false,
  },
  manifest: '/manifest.json',
  icons: {
    icon: '/favicon.ico',
    apple: '/apple-touch-icon.png',
  },
  robots: {
    index: false,
    follow: false,
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: 'cover',
  themeColor: '#1f2937',
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="ja" className="h-full">
      <head>
        {/* Preconnect to external resources */}
        <link rel="preconnect" href="https://api.openai.com" />
        <link rel="preconnect" href="https://hooks.slack.com" />
        
        {/* Prevent zoom on double tap for tablet usage */}
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
        
        {/* PWA settings for tablet */}
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Reception" />
        
        {/* Disable text selection and context menus for kiosk mode */}
        <style dangerouslySetInnerHTML={{
          __html: `
            * {
              -webkit-touch-callout: none;
              -webkit-user-select: none;
              -khtml-user-select: none;
              -moz-user-select: none;
              -ms-user-select: none;
              user-select: none;
            }
            
            /* Allow text selection in input fields */
            input, textarea {
              -webkit-user-select: text;
              -moz-user-select: text;
              -ms-user-select: text;
              user-select: text;
            }
            
            /* Disable context menu */
            body {
              -webkit-touch-callout: none;
              -webkit-user-select: none;
              -khtml-user-select: none;
              -moz-user-select: none;
              -ms-user-select: none;
              user-select: none;
            }
            
            /* Hide scrollbars but keep scrolling functional */
            ::-webkit-scrollbar {
              display: none;
            }
            
            * {
              -ms-overflow-style: none;
              scrollbar-width: none;
            }
          `
        }} />
      </head>
      <body className="h-full bg-gray-50 antialiased">
        {/* Screen reader accessibility */}
        <a 
          href="#main-content" 
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 bg-primary-600 text-white px-4 py-2 rounded-md z-50"
        >
          メインコンテンツへスキップ
        </a>
        
        {/* Main application container */}
        <div id="main-content" className="h-full">
          {children}
        </div>
        
        {/* Global error boundary fallback - removed onClick for NextJS 15 compatibility */}
        <div id="error-fallback" className="hidden fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-2xl p-8 max-w-md mx-4 text-center">
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              システムエラーが発生しました
            </h2>
            <p className="text-gray-600 mb-6">
              申し訳ございません。システムでエラーが発生しました。<br />
              ページを再読み込みしてください。
            </p>
            <Link 
              href="/"
              className="inline-block bg-primary-600 text-white px-6 py-3 rounded-xl font-medium hover:bg-primary-700 transition-colors"
            >
              ホームに戻る
            </Link>
          </div>
        </div>
        
        {/* Development tools (only in development) */}
        {process.env.NODE_ENV === 'development' && (
          <div className="fixed bottom-4 right-4 z-40">
            <div className="bg-black bg-opacity-50 text-white text-xs px-2 py-1 rounded">
              Development Mode
            </div>
          </div>
        )}
      </body>
    </html>
  );
}