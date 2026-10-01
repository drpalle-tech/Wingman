import { useEffect, useState } from 'react'

interface User {
  id: string
  name: string
  email: string
}

export function UserProfile({ userId }: { userId: string }) {
  const [user, setUser] = useState<User | null>(null)

  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then((response) => response.json())
      .then((data: User) => setUser(data))
  }, [])

  if (!user) return <p>Loading...</p>
  return (
    <div>
      <h2>{user.name}</h2>
      <p>{user.email}</p>
    </div>
  )
}
