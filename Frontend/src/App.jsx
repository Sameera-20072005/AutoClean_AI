import { lazy, Suspense } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { JobProvider } from './context/JobContext.jsx'
import AppLayout from './layouts/AppLayout.jsx'
const HomePage=lazy(()=>import('./pages/HomePage.jsx'))
const DashboardPage=lazy(()=>import('./pages/DashboardPage.jsx'))
const UploadPage=lazy(()=>import('./pages/UploadPage.jsx'))
const AnalysisPage=lazy(()=>import('./pages/AnalysisPage.jsx'))
const RepairPage=lazy(()=>import('./pages/RepairPage.jsx'))
const ValidationPage=lazy(()=>import('./pages/ValidationPage.jsx'))
const ReportsPage=lazy(()=>import('./pages/ReportsPage.jsx'))
const AboutPage=lazy(()=>import('./pages/AboutPage.jsx'))
function LoadingPage(){return <div className="card empty-state" role="status" aria-live="polite"><span className="badge">Loading page…</span></div>}
export default function App(){return <BrowserRouter><JobProvider><Suspense fallback={<LoadingPage/>}><Routes><Route element={<AppLayout/>}><Route index element={<HomePage/>}/><Route path="dashboard" element={<DashboardPage/>}/><Route path="upload" element={<UploadPage/>}/><Route path="analysis" element={<AnalysisPage/>}/><Route path="repair" element={<RepairPage/>}/><Route path="validation" element={<ValidationPage/>}/><Route path="reports" element={<ReportsPage/>}/><Route path="about" element={<AboutPage/>}/><Route path="*" element={<Navigate to="/" replace/>}/></Route></Routes></Suspense></JobProvider></BrowserRouter>}
