import { Link } from 'react-router-dom'
import { ArrowRight, Info } from 'lucide-react'

export function PageHeader({eyebrow,title,description,action}){return <div className="page-head"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h1>{title}</h1><p>{description}</p></div>{action}</div>}
export function Panel({title,subtitle,action,children,className=''}){return <section className={`card card-pad ${className}`}><div className="card-title"><div><h2>{title}</h2>{subtitle&&<p>{subtitle}</p>}</div>{action}</div>{children}</section>}
export function EmptyState({icon:Icon=Info,title='Nothing to show yet',description='Upload a dataset to begin. Your results will appear here once processing is connected.',action}){return <div className="empty-state"><div className="empty-icon"><Icon size={19}/></div><h3>{title}</h3><p>{description}</p>{action&&<div style={{marginTop:15}}>{action}</div>}</div>}
export function Tooltip({text}){return <span className="tooltip" tabIndex="0" role="img" aria-label={text} data-tip={text}><Info size={14}/></span>}
export function PrimaryLink({to,children}){return <Link className="button primary" to={to}>{children}<ArrowRight size={14}/></Link>}
