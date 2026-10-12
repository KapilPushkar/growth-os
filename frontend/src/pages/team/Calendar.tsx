import { MonthCalendar } from '../../components/MonthCalendar'
import { PageHeader } from '../../components/ui'

export function Calendar() {
  return (
    <>
      <PageHeader
        eyebrow="Content calendar"
        title="Calendar"
        description="Scheduled and published posts across every client."
      />
      <MonthCalendar />
    </>
  )
}
