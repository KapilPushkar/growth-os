import { LeadsBoard } from '../../components/Leads'
import { ReportView } from '../../components/ReportView'
import { Async, Avatar, ClientStatusBadge, Health, Link } from '../../components/ui'
import { api } from '../../lib/api'
import { date } from '../../lib/format'
import { useApi } from '../../lib/useApi'
import { BrandTab } from './workspace/BrandTab'
import { CampaignsTab } from './workspace/CampaignsTab'
import { ContentTab } from './workspace/ContentTab'
import { OnboardingTab } from './workspace/OnboardingTab'
import { OverviewTab } from './workspace/OverviewTab'
import { SeoTab } from './workspace/SeoTab'

const TABS = [
  { key: '', label: 'Overview' },
  { key: 'content', label: 'Content' },
  { key: 'campaigns', label: 'Campaigns' },
  { key: 'leads', label: 'Leads' },
  { key: 'seo', label: 'SEO & GEO' },
  { key: 'brand', label: 'Brand profile' },
  { key: 'onboarding', label: 'Onboarding' },
  { key: 'report', label: 'Report' },
]

export function ClientWorkspace({ clientId, tab }: { clientId: number; tab: string }) {
  const state = useApi(() => api.clients.get(clientId), [clientId])

  return (
    <Async state={state} label="Loading client…">
      {(client) => (
        <>
          <header className="page-header no-print">
            <div className="row" style={{ gap: 16, alignItems: 'center' }}>
              <Avatar name={client.name} size="lg" />
              <div>
                <div className="eyebrow">
                  <Link to="/clients">Clients</Link> / {client.company}
                </div>
                <h1>{client.name}</h1>
                <div className="row wrap" style={{ marginTop: 6 }}>
                  <span className="muted">
                    {client.title}
                    {client.title ? ', ' : ''}
                    {client.company} · {client.industry}
                  </span>
                  <ClientStatusBadge status={client.status} />
                  <Health score={client.health} />
                </div>
              </div>
            </div>
            <div className="stack tight subtle" style={{ textAlign: 'right' }}>
              <span>Account manager: {client.account_manager?.name ?? 'Unassigned'}</span>
              <span>{client.start_date ? `Live since ${date(client.start_date)}` : `Onboarding ${client.onboarding_pct}% complete`}</span>
              {client.website ? (
                <a href={client.website} target="_blank" rel="noreferrer">
                  {client.website.replace(/^https?:\/\//, '')}
                </a>
              ) : null}
            </div>
          </header>

          <nav className="tabs" aria-label="Client sections">
            {TABS.map((item) => (
              <Link key={item.key} to={`/clients/${client.id}${item.key ? `/${item.key}` : ''}`} exact>
                {item.label}
              </Link>
            ))}
          </nav>

          {tab === '' ? <OverviewTab client={client} /> : null}
          {tab === 'content' ? <ContentTab client={client} /> : null}
          {tab === 'campaigns' ? <CampaignsTab client={client} /> : null}
          {tab === 'leads' ? <LeadsBoard clientId={client.id} /> : null}
          {tab === 'seo' ? <SeoTab client={client} /> : null}
          {tab === 'brand' ? <BrandTab client={client} onSaved={(updated) => state.setData(updated)} /> : null}
          {tab === 'onboarding' ? <OnboardingTab client={client} onChanged={(updated) => state.setData(updated)} /> : null}
          {tab === 'report' ? <ReportView clientId={client.id} /> : null}
        </>
      )}
    </Async>
  )
}
