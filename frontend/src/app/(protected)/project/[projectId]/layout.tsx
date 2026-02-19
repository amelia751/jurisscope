import { onAuthenticateUser } from '@/actions/user'
import { ProjectSidebar } from '@/components/global/project-sidebar'
import ProjectHeader from '@/components/global/project-header'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
import { redirect } from 'next/navigation'
import React from 'react'

type Props = {
  children: React.ReactNode
  params: Promise<{ projectId: string }>
}

const Layout = async ({ children, params }: Props) => {
  const checkUser = await onAuthenticateUser()

  if (!checkUser.user) {
    redirect('/sign-in')
  }

  const { projectId } = await params

  return (
    <SidebarProvider defaultOpen={false}>
      <ProjectSidebar
        user={checkUser.user}
        projectId={projectId}
      />
      <SidebarInset>
        <ProjectHeader user={checkUser.user} />
        <div className="p-4">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  )
}

export default Layout
