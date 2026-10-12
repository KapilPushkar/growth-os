import { useState } from 'react'
import { LeadsBoard } from '../../components/Leads'
import { PageHeader } from '../../components/ui'
import { api } from '../../lib/api'
import { useApi } from '../../lib/useApi'

export function Leads() {
  const [clientId, setClientId] = useState<number | ''>('')
  const clients = useApi(() => api.clients.list({ status: 'active' }), [])

  return (
    <>
      <PageHeader
        eyebrow="Lead generation"
        title="Lead pipeline"
        description="Every lead across clients, from first touch to won."
        actions={
          <select
            className="select"
            style={{ width: 220 }}
            value={clientId}
            onChange={(e) => setClientId(e.target.value ? Number(e.target.value) : '')}
            aria-label="Filter by client"
          >
            <option value="">All clients</option>
            {(clients.data ?? []).map((client) => (
              <option key={client.id} value={client.id}>
                {client.name}
              </option>
            ))}
          </select>
        }
      />
      <LeadsBoard clientId={clientId || undefined} showClient={!clientId} />
    </>
  )
}
