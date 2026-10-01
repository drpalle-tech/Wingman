import { useEffect, useState } from 'react'

export function Countdown({ seconds }: { seconds: number }) {
  const [remaining, setRemaining] = useState(seconds)

  useEffect(() => {
    setInterval(() => {
      setRemaining(remaining - 1)
    }, 1000)
  }, [])

  return <span>{remaining}s left</span>
}
