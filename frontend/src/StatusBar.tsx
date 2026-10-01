import type { UsageStats } from '@wingman/client'
import { useEffect, useState } from 'react'
import { API_URL, api } from './api'

const POLL_MS = 5000

function formatDate(iso: string | null): string {
  return iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : 'now'
}

export function StatusBar() {
  const [stats, setStats] = useState<UsageStats | null>(null)
  const [offline, setOffline] = useState(false)
  const [showDetails, setShowDetails] = useState(false)

  useEffect(() => {
    let cancelled = false
    const fetchStats = async () => {
      try {
        const next = await api.usage()
        if (!cancelled) {
          setStats(next)
          setOffline(false)
        }
      } catch {
        if (!cancelled) setOffline(true)
      }
    }
    void fetchStats()
    const timer = setInterval(fetchStats, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [])

  if (offline) {
    return (
      <div className="border-t border-red-200 bg-red-50 px-4 py-2 text-sm text-red-700">
        Backend not reachable at {API_URL}. Start it with <code>python main.py</code> in the backend folder.
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="border-t border-slate-300 bg-slate-100 px-4 py-2">
        <p className="text-sm text-slate-600">Loading usage stats...</p>
      </div>
    )
  }

  return (
    <div className="border-t border-slate-300 bg-gradient-to-r from-blue-50 to-indigo-50 shadow-lg">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-2 text-left hover:bg-blue-100"
        onClick={() => setShowDetails((show) => !show)}
      >
        <div className="flex items-center gap-6 text-sm">
          <div>
            <span className="font-bold text-blue-600">${stats.total_cost_usd.toFixed(4)}</span>
            <span className="ml-2 text-slate-600">/ ₹{stats.total_cost_inr.toFixed(2)}</span>
            <span className="ml-2 text-xs text-slate-500">since {formatDate(stats.tracking_since)}</span>
          </div>
          <div className="text-slate-600">
            <span className="font-semibold">{stats.total_tokens.toLocaleString()}</span> tokens
          </div>
          <div className="text-slate-600">
            <span className="font-semibold">{stats.total_requests}</span> requests
          </div>
          <div className="text-xs text-slate-500">
            This session: ${stats.session.total_cost_usd.toFixed(4)} · {stats.session.requests} requests
          </div>
        </div>
        <span className="text-xs text-slate-500">{showDetails ? '▼ Hide details' : '▶ Show details'}</span>
      </button>

      {showDetails && (
        <div className="grid grid-cols-3 gap-4 border-t border-slate-200 bg-white px-4 py-3 text-sm text-slate-600">
          <div className="border-r border-slate-200 pr-4">
            <h4 className="mb-2 font-bold text-slate-800">All-time tokens</h4>
            <p>
              Input: <span className="font-semibold text-green-600">{stats.total_input_tokens.toLocaleString()}</span>
            </p>
            <p>
              Output: <span className="font-semibold text-orange-600">{stats.total_output_tokens.toLocaleString()}</span>
            </p>
            <p className="mt-2">
              Avg per request: <span className="font-semibold">{stats.average_tokens_per_request.toLocaleString()}</span>
            </p>
          </div>
          <div className="border-r border-slate-200 pr-4">
            <h4 className="mb-2 font-bold text-slate-800">All-time cost</h4>
            <p>
              Total: <span className="font-semibold text-red-600">${stats.total_cost_usd.toFixed(4)}</span> (₹
              {stats.total_cost_inr.toFixed(2)})
            </p>
            <p>
              Avg per request: <span className="font-semibold">${stats.average_cost_per_request.toFixed(6)}</span>
            </p>
            <p className="mt-2">
              This session: <span className="font-semibold">${stats.session.total_cost_usd.toFixed(4)}</span>,{' '}
              {stats.session.total_tokens.toLocaleString()} tokens
            </p>
          </div>
          <div>
            <h4 className="mb-2 font-bold text-slate-800">By model</h4>
            {stats.by_model.length === 0 && <p>No requests yet.</p>}
            {stats.by_model.map((m) => (
              <p key={m.model}>
                <span className="font-mono">{m.model}</span>: ${m.total_cost_usd.toFixed(4)} · {m.requests} requests
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="border-t border-blue-200 bg-blue-100 px-4 py-1 text-xs text-blue-700">
        Estimated from token counts. {stats.model}
        {stats.pricing_per_1k
          ? `: $${stats.pricing_per_1k.input} per 1K input tokens, $${stats.pricing_per_1k.output} per 1K output tokens`
          : ': no pricing configured, costs show as $0'}
      </div>
    </div>
  )
}
