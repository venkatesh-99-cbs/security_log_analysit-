/**
 * formatDate.ts — Timezone-aware date/time formatting utilities.
 *
 * NEVER hardcodes timestamps. All functions derive time from the
 * ISO string passed in and format using the browser's local timezone
 * via Intl.DateTimeFormat.
 */

/**
 * Returns the browser-detected timezone abbreviation (e.g. "IST", "EST", "UTC").
 */
export function getLocalTimezoneAbbr(): string {
  try {
    return new Intl.DateTimeFormat('en', { timeZoneName: 'short' })
      .formatToParts(new Date())
      .find((p) => p.type === 'timeZoneName')?.value ?? '';
  } catch {
    return '';
  }
}

/** Backend timestamps are UTC; older records may omit the trailing Z. */
export function parseServerDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`;
  const date = new Date(normalized);
  return isNaN(date.getTime()) ? null : date;
}

/**
 * Formats an ISO timestamp string to a human-readable local date+time string.
 * Example output: "16 Jul 2026, 02:15:43 PM IST"
 */
export function formatLocalDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const date = parseServerDate(isoString);
    if (!date) return isoString;

    const tz = getLocalTimezoneAbbr();

    const formatted = new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    }).format(date);

    return tz ? `${formatted} ${tz}` : formatted;
  } catch {
    return isoString ?? '—';
  }
}

/**
 * Formats an ISO timestamp string to time only: "14:22:13 IST"
 */
export function formatLocalTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const date = parseServerDate(isoString);
    if (!date) return isoString;

    const tz = getLocalTimezoneAbbr();

    const formatted = new Intl.DateTimeFormat('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    }).format(date);

    return tz ? `${formatted} ${tz}` : formatted;
  } catch {
    return isoString ?? '—';
  }
}

/**
 * Formats an ISO timestamp string as a relative time label.
 * Examples: "just now", "5m ago", "2h ago", "3d ago", "16 Jul 2026"
 */
export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '—';
  try {
    const date = parseServerDate(isoString);
    if (!date) return isoString;

    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffMs / 60_000);
    const diffHr  = Math.floor(diffMs / 3_600_000);
    const diffDay = Math.floor(diffMs / 86_400_000);

    if (diffSec < 30)  return 'just now';
    if (diffMin < 60)  return `${diffMin}m ago`;
    if (diffHr  < 24)  return `${diffHr}h ago`;
    if (diffDay < 7)   return `${diffDay}d ago`;

    return new Intl.DateTimeFormat('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    }).format(date);
  } catch {
    return isoString ?? '—';
  }
}

/**
 * Formats file size in bytes to a human-readable string.
 * Examples: "1.2 KB", "3.4 MB"
 */
export function formatFileSize(bytes: number | null | undefined): string {
  if (bytes == null || bytes <= 0) return '—';
  if (bytes < 1024)         return `${bytes} B`;
  if (bytes < 1024 * 1024)  return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}
