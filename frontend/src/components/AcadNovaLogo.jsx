import { useId } from 'react'

/**
 * AcadNova brand logo.
 *
 * The mark is an original geometric "Nova": a faceted prism (four gradient
 * facets forming a diamond) representing structured knowledge, encircled by a
 * partial orbit with a discovery node — a symbol of research and discovery.
 *
 * Props:
 *  - variant: 'full' | 'compact' | 'symbol'
 *  - size: 'sm' | 'md' | 'lg'
 *  - showTagline: boolean (only meaningful with variant="full")
 *  - tone: 'auto' | 'light' | 'dark' (dark = for dark backgrounds)
 *  - className: extra class names
 */
export default function AcadNovaLogo({
  variant = 'compact',
  size = 'md',
  showTagline = false,
  tone = 'auto',
  className = '',
  ...rest
}) {
  const rawId = useId().replace(/:/g, '')
  const gid = (name) => `acadnova-${name}-${rawId}`

  const symbolOnly = variant === 'symbol'
  const withTagline = showTagline && variant === 'full'

  return (
    <span
      className={`acadnova-logo acadnova-logo--${size}${className ? ` ${className}` : ''}`}
      data-tone={tone}
      {...rest}
    >
      <svg
        className="acadnova-logo__symbol"
        viewBox="0 0 48 48"
        role={symbolOnly ? 'img' : undefined}
        aria-label={symbolOnly ? 'AcadNova' : undefined}
        aria-hidden={symbolOnly ? undefined : 'true'}
        focusable="false"
      >
        <defs>
          <linearGradient id={gid('top')} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#818cf8" />
            <stop offset="100%" stopColor="#4f46e5" />
          </linearGradient>
          <linearGradient id={gid('right')} x1="1" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
          <linearGradient id={gid('bottom')} x1="0" y1="1" x2="1" y2="0">
            <stop offset="0%" stopColor="#1e3a8a" />
            <stop offset="100%" stopColor="#1e40af" />
          </linearGradient>
          <linearGradient id={gid('left')} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4f46e5" />
            <stop offset="100%" stopColor="#4338ca" />
          </linearGradient>
          <linearGradient id={gid('orbit')} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#4f46e5" />
            <stop offset="100%" stopColor="#2563eb" />
          </linearGradient>
        </defs>

        {/* Discovery orbit with a gap + node */}
        <circle
          cx="24"
          cy="24"
          r="21.5"
          fill="none"
          stroke={`url(#${gid('orbit')})`}
          strokeWidth="1.7"
          strokeLinecap="round"
          pathLength="100"
          strokeDasharray="74 26"
          transform="rotate(-90 24 24)"
          opacity="0.9"
        />
        <circle cx="24" cy="2.5" r="2.4" fill="#4f46e5" />

        {/* Faceted prism (structured knowledge) */}
        <polygon points="24,7 38,24 24,24" fill={`url(#${gid('top')})`} />
        <polygon points="38,24 24,41 24,24" fill={`url(#${gid('right')})`} />
        <polygon points="24,41 10,24 24,24" fill={`url(#${gid('bottom')})`} />
        <polygon points="10,24 24,7 24,24" fill={`url(#${gid('left')})`} />
        <circle cx="24" cy="24" r="2.1" fill="#ffffff" opacity="0.92" />
      </svg>

      {!symbolOnly ? (
        <span className="acadnova-logo__text">
          <span className="acadnova-logo__word">
            <span className="acadnova-logo__acad">Acad</span>
            <span className="acadnova-logo__accent">Nova</span>
          </span>
          {withTagline ? (
            <span className="acadnova-logo__tagline">A New Era of Research.</span>
          ) : null}
        </span>
      ) : null}
    </span>
  )
}
