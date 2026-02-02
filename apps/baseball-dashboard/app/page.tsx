export default function Home() {
  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
      <div className="container mx-auto px-4 py-8">
        <header className="mb-12 text-center">
          <h1 className="text-5xl font-bold text-gray-900 dark:text-white mb-4">
            ⚾ Fantasy Baseball Dashboard
          </h1>
          <p className="text-xl text-gray-600 dark:text-gray-300">
            Your year-round competitive advantage
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
          {/* Quick Stats Cards */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Today's Games
              </h3>
              <span className="text-3xl">📅</span>
            </div>
            <p className="text-3xl font-bold text-blue-600">12</p>
            <p className="text-sm text-gray-500">MLB games scheduled</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Roster
              </h3>
              <span className="text-3xl">👥</span>
            </div>
            <p className="text-3xl font-bold text-green-600">24</p>
            <p className="text-sm text-gray-500">Active players</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Breakouts
              </h3>
              <span className="text-3xl">🔥</span>
            </div>
            <p className="text-3xl font-bold text-orange-600">3</p>
            <p className="text-sm text-gray-500">STRONG signals</p>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Win Rate
              </h3>
              <span className="text-3xl">🏆</span>
            </div>
            <p className="text-3xl font-bold text-purple-600">72%</p>
            <p className="text-sm text-gray-500">Season performance</p>
          </div>
        </div>

        {/* Main Tools Grid */}
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-2">
          {/* Daily Lineup */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 hover:shadow-2xl transition-shadow">
            <div className="flex items-center mb-4">
              <span className="text-4xl mr-4">📊</span>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Daily Lineup
                </h2>
                <p className="text-gray-600 dark:text-gray-300">
                  Start/sit recommendations
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <span className="font-medium">🔥 Must Start</span>
                <span className="font-bold text-green-600">6 players</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <span className="font-medium">⚠️ Consider Benching</span>
                <span className="font-bold text-yellow-600">2 players</span>
              </div>
            </div>
            <button className="mt-6 w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors">
              View Full Lineup
            </button>
          </div>

          {/* Waiver Wire */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 hover:shadow-2xl transition-shadow">
            <div className="flex items-center mb-4">
              <span className="text-4xl mr-4">🎯</span>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Waiver Wire
                </h2>
                <p className="text-gray-600 dark:text-gray-300">
                  Value pickups available
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg">
                <span className="font-medium">✅ Strong Pickups</span>
                <span className="font-bold text-purple-600">8 available</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <span className="font-medium">💎 Keeper Value</span>
                <span className="font-bold text-blue-600">3 gems</span>
              </div>
            </div>
            <button className="mt-6 w-full bg-purple-600 hover:bg-purple-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors">
              Browse Waivers
            </button>
          </div>

          {/* Breakout Detector */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 hover:shadow-2xl transition-shadow">
            <div className="flex items-center mb-4">
              <span className="text-4xl mr-4">🔬</span>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Breakout Detector
                </h2>
                <p className="text-gray-600 dark:text-gray-300">
                  Statcast-powered analysis
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
                <span className="font-medium">🔥 STRONG</span>
                <span className="font-bold text-orange-600">3 players</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
                <span className="font-medium">⚡ EMERGING</span>
                <span className="font-bold text-yellow-600">5 players</span>
              </div>
            </div>
            <button className="mt-6 w-full bg-orange-600 hover:bg-orange-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors">
              Scan Free Agents
            </button>
          </div>

          {/* Keeper Analyzer */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8 hover:shadow-2xl transition-shadow">
            <div className="flex items-center mb-4">
              <span className="text-4xl mr-4">⭐</span>
              <div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Keeper Analyzer
                </h2>
                <p className="text-gray-600 dark:text-gray-300">
                  Optimize your keepers
                </p>
              </div>
            </div>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <span className="font-medium">💰 Top Value</span>
                <span className="font-bold text-green-600">Betts (R1)</span>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                <span className="font-medium">📈 Surplus</span>
                <span className="font-bold text-blue-600">+427 ADP</span>
              </div>
            </div>
            <button className="mt-6 w-full bg-green-600 hover:bg-green-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors">
              Analyze Keepers
            </button>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-12 text-center text-gray-600 dark:text-gray-400">
          <p>Built with Next.js • Powered by Statcast • Deployed on Vercel</p>
          <p className="mt-2">🏆 Your year-round competitive advantage</p>
        </footer>
      </div>
    </main>
  );
}
