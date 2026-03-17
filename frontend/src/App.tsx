import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import LiveGames from './pages/LiveGames'
import TradeHistory from './pages/TradeHistory'
import Simulation from './pages/Simulation'
import Settings from './pages/Settings'

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/games" element={<LiveGames />} />
        <Route path="/trades" element={<TradeHistory />} />
        <Route path="/simulation" element={<Simulation />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}
