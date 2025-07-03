'use client';

import dynamic from 'next/dynamic';
import { useState } from 'react';
import { RouteChat } from '@/components/RouteChat';

// Dynamically import the Map component with no SSR
const Map = dynamic(() => import('@/components/Map'), {
  ssr: false,
  loading: () => (
    <div className="fixed inset-0 w-full h-full bg-gradient-to-br from-green-50 to-emerald-100 flex items-center justify-center">
      <div className="text-center p-8 bg-white rounded-2xl shadow-2xl">
        <div className="animate-spin rounded-full h-16 w-16 border-4 border-green-500 border-t-transparent mx-auto mb-6"></div>
        <h3 className="text-xl font-semibold text-gray-800 mb-2">Loading safe-route</h3>
        <p className="text-gray-600">Preparing your safe route planner...</p>
      </div>
    </div>
  )
});

export default function RoutePage() {
  const [showChat, setShowChat] = useState(false);
  const [currentRoute, setCurrentRoute] = useState<any>(null);

  // Function to handle route updates from the Map component
  const handleRouteUpdate = (routeData: any) => {
    setCurrentRoute(routeData);
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50">
      {/* Compact Fixed Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm z-[9999] relative">
        <div className="px-4 py-2.5">
          <div className="flex items-center justify-between">
            {/* Logo and Brand */}
            <div className="flex items-center space-x-3">
              <div className="relative">
                <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-emerald-600 rounded-lg shadow-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
              </div>
              <div>
                <h1 className="text-lg font-bold bg-gradient-to-r from-green-600 to-emerald-600 bg-clip-text text-transparent">
                  safe-route
                </h1>
                <p className="text-xs text-gray-500 font-medium">Smart Route Planning</p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center space-x-2">
              <button
                onClick={() => setShowChat(!showChat)}
                className={`px-3 py-1.5 rounded-lg font-medium transition-all duration-200 flex items-center space-x-1.5 shadow-sm text-sm ${
                  showChat
                    ? 'bg-green-100 text-green-700 hover:bg-green-200'
                    : 'bg-green-600 text-white hover:bg-green-700 shadow-lg hover:shadow-xl'
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                <span>{showChat ? 'Hide' : 'AI'}</span>
              </button>
              
              <div className="w-px h-6 bg-gray-200"></div>
              
              <div className="flex items-center space-x-1.5 text-xs text-gray-500">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full animate-pulse"></div>
                <span className="font-medium">Live Data</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 relative overflow-hidden">
        {/* Map Container */}
        <div className="absolute inset-0">
          <Map onRouteUpdate={handleRouteUpdate} />
        </div>

        {/* AI Chat Overlay */}
        {showChat && (
          <div className="absolute top-16 right-4 z-[9998] w-80 max-h-[calc(100vh-140px)]">
            <div className="bg-white rounded-xl shadow-2xl border border-gray-200 overflow-hidden">
              <div className="bg-gradient-to-r from-green-500 to-emerald-600 px-4 py-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2.5">
                    <div className="w-6 h-6 bg-white/20 rounded-lg flex items-center justify-center">
                      <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-sm">Route Assistant</h3>
                      <p className="text-green-100 text-xs">AI-powered insights</p>
                    </div>
                  </div>
                  <button
                    onClick={() => setShowChat(false)}
                    className="text-white/80 hover:text-white transition-colors p-1"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>
              <div className="max-h-80 overflow-y-auto">
                <RouteChat routeData={currentRoute} />
              </div>
            </div>
          </div>
        )}

        {/* Compact Status Bar - moved to right side to avoid crime legend overlap */}
        <div className="absolute bottom-4 right-4 z-[9998]">
          <div className="bg-white/95 backdrop-blur-md rounded-lg px-3 py-2 shadow-lg border border-gray-200">
            <div className="flex items-center space-x-3 text-xs">
              <div className="flex items-center space-x-1.5">
                <div className="w-1.5 h-1.5 bg-green-400 rounded-full"></div>
                <span className="text-gray-600 font-medium">Ready to plan</span>
              </div>
              {currentRoute && (
                <>
                  <div className="w-px h-3 bg-gray-300"></div>
                  <div className="flex items-center space-x-1.5">
                    <svg className="w-3 h-3 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-gray-600">Route ready</span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
} 