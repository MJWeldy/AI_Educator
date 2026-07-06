export default function Placeholder({ title, note }: { title: string; note: string }) {
  return (
    <>
      <div className="page-kicker rise">Coming up</div>
      <h1 className="page-title rise rise-1">{title}</h1>
      <p className="page-sub rise rise-2">{note}</p>
    </>
  )
}
