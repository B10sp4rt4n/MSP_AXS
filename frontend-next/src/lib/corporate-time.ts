// Corporate visit/event datetimes without an offset are UTC by API contract
// (datetime.utcnow in the backend). Never let Date interpret them as device time.
export function validTimeZone(zone: string): boolean {
  if (!zone.trim()) return false;
  try {
    new Intl.DateTimeFormat("es-MX", { timeZone: zone }).format(0);
    return true;
  } catch { return false; }
}

export function corporateTime(value: string, zone: string) {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})?$/.exec(value);
  if (!match) return null;
  const date = new Date(value + (match[3] ? "" : "Z"));
  if (!Number.isFinite(date.getTime())) return null;
  const timeZone = validTimeZone(zone) ? zone : "UTC";
  // Date has millisecond precision; retain the API's microseconds in the UTC
  // evidence shown to the user. Conversion never changes the persisted value.
  const fraction = (match[2]?.slice(1) ?? "").padEnd(3, "0");
  const utc = date.toISOString().replace(/\.\d{3}Z$/, `.${fraction}Z`);
  const local = new Intl.DateTimeFormat("es-MX", {
    timeZone, year: "numeric", month: "2-digit", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).format(date);
  return { local, utc, timeZone };
}
