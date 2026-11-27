import { createContext, useContext, useMemo, useState } from 'react'

const JobContext = createContext(null)

export function JobProvider({ children }) {
  const [job, setJob] = useState(null)
  const value = useMemo(() => ({ job, setJob }), [job])
  return <JobContext.Provider value={value}>{children}</JobContext.Provider>
}

export function useJob() {
  const context = useContext(JobContext)
  if (!context) throw new Error('useJob must be used inside JobProvider')
  return context
}
