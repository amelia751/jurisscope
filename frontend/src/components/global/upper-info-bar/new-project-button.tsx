'use client';
import { Button } from '@/components/ui/button'
import { Plus } from '@/icons/Plus';
import { User } from '@prisma/client';
import { useRouter } from 'next/navigation'
import React from 'react'


function NewProjectButton({user}:{user:User}) {
  const router = useRouter();
  return (
    <Button
    size={"lg"}
    className="rounded-lg font-semibold"
    onClick={() => router.push("/create-page")}
  >
    <Plus />
    New Project
  </Button>
  )
}

export default NewProjectButton