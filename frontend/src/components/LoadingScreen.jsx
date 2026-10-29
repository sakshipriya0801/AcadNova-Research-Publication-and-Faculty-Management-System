export default function LoadingScreen({ message = 'Loading…' }) {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p className="loading-screen__text">{message}</p>
    </div>
  )
}
