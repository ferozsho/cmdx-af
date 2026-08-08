import { redirect } from 'next/navigation'

export default async function WorkspacePage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const resolvedParams = await params
  // SEO-friendly URLs live at /projects/[id]/[tab]; redirect the bare
  // project URL to the default Agents tab.
  redirect(
    `/projects/${encodeURIComponent(resolvedParams.id)}/agents`,
  )
}
