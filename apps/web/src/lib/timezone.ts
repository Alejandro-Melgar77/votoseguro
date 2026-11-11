/**
 * Utilidades de formato de fechas y sincronización horaria para VotoSeguro
 */

export function formatElectoralDateTime(
  dateInput: string | Date,
  timeZone: string = 'America/La_Paz'
): string {
  if (!dateInput) return '—';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return 'Fecha inválida';

  return new Intl.DateTimeFormat('es-BO', {
    timeZone,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date);
}

export function formatDateTimeLocalInput(dateInput: string | Date): string {
  if (!dateInput) return '';
  const date = typeof dateInput === 'string' ? new Date(dateInput) : dateInput;
  if (isNaN(date.getTime())) return '';

  const pad = (n: number) => n.toString().padStart(2, '0');
  const yyyy = date.getFullYear();
  const MM = pad(date.getMonth() + 1);
  const dd = pad(date.getDate());
  const hh = pad(date.getHours());
  const mm = pad(date.getMinutes());

  return `${yyyy}-${MM}-${dd}T${hh}:${mm}`;
}

export function calculateRemainingSeconds(
  targetDateInput: string | Date,
  serverOffsetMs: number = 0
): number {
  const targetDate = typeof targetDateInput === 'string' ? new Date(targetDateInput) : targetDateInput;
  const nowWithOffset = Date.now() + serverOffsetMs;
  return Math.max(0, Math.floor((targetDate.getTime() - nowWithOffset) / 1000));
}
