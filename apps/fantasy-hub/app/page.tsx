export default function Home() {
  const basePath = process.env.NODE_ENV === 'production' ? '/fantasy' : '';
  
  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="container mx-auto px-4 py-16">
        {/* Header */}
        <header className="text-center mb-16">
          <h1 className="text-6xl font-bold text-white mb-4">
            🏆 Fantasy Sports Hub
          </h1>
          <p className="text-2xl text-gray-300">
            Your complete toolkit for dominating fantasy sports
          </p>
        </header>

        {/* Apps Grid */}
        <div className="grid md:grid-cols-2 gap-8 max-w-6xl mx-auto">
          
          {/* Baseball Dashboard */}
          <a 
            href={`${basePath}/baseball/`}
            className="group block bg-white/10 backdrop-blur-lg rounded-2xl p-8 hover:bg-white/20 transition-all duration-300 hover:scale-105 hover:shadow-2xl border border-white/20"
          >
            <div className="flex items-center mb-6">
              <span className="text-6xl mr-4">⚾</span>
              <div>
                <h2 className="text-3xl font-bold text-white group-hover:text-blue-300 transition-colors">
                  Baseball Dashboard
                </h2>
                <p className="text-gray-300">Daily Fantasy Baseball Intelligence</p>
              </div>
            </div>
            
            <div className="space-y-3 mb-6">
              <div className="flex items-center text-gray-200">
                <span className="mr-3">📊</span>
                <span>Daily lineup recommendations</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">🎯</span>
                <span>Waiver wire value analysis</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">🔬</span>
                <span>Statcast breakout detection</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">⭐</span>
                <span>Keeper value optimizer</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-white/20">
              <span className="text-sm text-gray-400">Powered by MLB Stats API + Statcast</span>
              <span className="text-white group-hover:translate-x-2 transition-transform">→</span>
            </div>
          </a>

          {/* ESPN Recap */}
          <a 
            href={`${basePath}/recap/`}
            className="group block bg-white/10 backdrop-blur-lg rounded-2xl p-8 hover:bg-white/20 transition-all duration-300 hover:scale-105 hover:shadow-2xl border border-white/20"
          >
            <div className="flex items-center mb-6">
              <span className="text-6xl mr-4">🏈</span>
              <div>
                <h2 className="text-3xl font-bold text-white group-hover:text-green-300 transition-colors">
                  ESPN Recap Generator
                </h2>
                <p className="text-gray-300">AI-Powered Weekly Recaps</p>
              </div>
            </div>
            
            <div className="space-y-3 mb-6">
              <div className="flex items-center text-gray-200">
                <span className="mr-3">📝</span>
                <span>Weekly matchup recaps</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">🤖</span>
                <span>AI-generated commentary</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">📊</span>
                <span>League power rankings</span>
              </div>
              <div className="flex items-center text-gray-200">
                <span className="mr-3">💬</span>
                <span>Slack integration ready</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-4 border-t border-white/20">
              <span className="text-sm text-gray-400">Powered by Claude AI + ESPN API</span>
              <span className="text-white group-hover:translate-x-2 transition-transform">→</span>
            </div>
          </a>

        </div>

        {/* Features Banner */}
        <div className="mt-16 text-center">
          <div className="inline-flex items-center space-x-8 bg-white/10 backdrop-blur-lg rounded-full px-8 py-4 border border-white/20">
            <div className="flex items-center">
              <span className="text-2xl mr-2">📱</span>
              <span className="text-white font-semibold">Mobile Friendly</span>
            </div>
            <div className="flex items-center">
              <span className="text-2xl mr-2">🔒</span>
              <span className="text-white font-semibold">Free Forever</span>
            </div>
            <div className="flex items-center">
              <span className="text-2xl mr-2">⚡</span>
              <span className="text-white font-semibold">Real-time Data</span>
            </div>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-16 text-center text-gray-400">
          <p>Built with Next.js • Hosted on GitHub Pages</p>
          <p className="mt-2">Your year-round competitive advantage 🏆</p>
        </footer>
      </div>
    </main>
  );
}
