/**
 * src/lib/format.js
 * Formatting helpers, shared so CarCard and CarCatalog can never drift apart.
 */

export const fmtPrice = (p) => {
  if (p == null) return '—';
  if (p >= 10000000) return `${(p / 10000000).toFixed(2)} crore`;
  if (p >= 100000) return `${(p / 100000).toFixed(1)} lakh`;
  return p.toLocaleString('en-PK');
};

export const fmtKm = (km) => {
  if (!km && km !== 0) return '—';
  return km >= 1000 ? `${Math.round(km / 1000)}k km` : `${km} km`;
};

export const carYear = (car) => car.model_year ?? car.year;

export const carTitle = (car) =>
  [carYear(car), car.make, car.model, car.variant].filter(Boolean).join(' ');

export const carMileage = (car) => car.mileage_km ?? car.mileage;

export const placeholderImg = (car) =>
  `https://placehold.co/640x400/121822/2E3B4D?text=${encodeURIComponent(
    `${car.make ?? ''} ${car.model ?? ''}`.trim() || 'Car'
  )}`;

/** True if the string contains Arabic-script characters (Urdu). */
export const isUrdu = (text = '') => /[\u0600-\u06FF]/.test(text);

/**
 * Build the message that handlers.parse_ask_ai_message() can actually parse.
 *
 * Its regex is strict:
 *   tell me about this car ... : YYYY Make Model Variant (id N), N km,
 *   Transmission, Color, City, Rs N.NN lac
 *
 * make / transmission / color / city are matched with \w+, so each must be a
 * single word — hence the firstWord() squeeze. Price must be in lac, because
 * the parser multiplies by 10,000,000 the moment it sees "crore" anywhere in
 * the string.
 *
 * The old App.jsx sent "Show details and options for ..." which never matched,
 * so the catalog button silently fell through to a generic search.
 */
const firstWord = (v, fallback) =>
  String(v ?? '').trim().split(/\s+/)[0].replace(/[^\w-]/g, '') || fallback;

export const buildAskAiMessage = (car) => {
  const year = carYear(car) ?? 2000;
  const make = firstWord(car.make, 'Unknown');
  const model = String(car.model ?? '').trim();
  const variant = String(car.variant ?? '').trim();
  const name = [model, variant].filter(Boolean).join(' ') || 'Unknown';
  const km = Math.round(Number(carMileage(car)) || 0);
  const transmission = firstWord(car.transmission, 'Manual');
  const color = firstWord(car.color, 'Other');
  const city = firstWord(car.city, 'Lahore');
  const lac = ((Number(car.price) || 0) / 100000).toFixed(2);

  return (
    'Tell me about this car and answer my questions about it: ' +
    `${year} ${make} ${name} (id ${car.id}), ${km} km, ` +
    `${transmission}, ${color}, ${city}, Rs ${lac} lac.`
  );
};

/** Download an .ics so a booked inspection lands in the user's calendar. */
export const downloadIcs = ({ title, description, date, time }) => {
  const parsed = parseWhen(date, time);
  if (!parsed) return false;
  const end = new Date(parsed.getTime() + 60 * 60 * 1000);
  const stamp = (d) => d.toISOString().replace(/[-:]/g, '').split('.')[0] + 'Z';

  const ics = [
    'BEGIN:VCALENDAR',
    'VERSION:2.0',
    'PRODID:-//PakWheels Assistant//EN',
    'BEGIN:VEVENT',
    `UID:${Date.now()}@pakwheels-assistant`,
    `DTSTAMP:${stamp(new Date())}`,
    `DTSTART:${stamp(parsed)}`,
    `DTEND:${stamp(end)}`,
    `SUMMARY:${title}`,
    `DESCRIPTION:${description}`,
    'END:VEVENT',
    'END:VCALENDAR',
  ].join('\r\n');

  const url = URL.createObjectURL(new Blob([ics], { type: 'text/calendar' }));
  const a = document.createElement('a');
  a.href = url;
  a.download = 'car-inspection.ics';
  a.click();
  URL.revokeObjectURL(url);
  return true;
};

function parseWhen(date, time) {
  if (!date) return null;
  const now = new Date();
  const guess = new Date(`${date} ${now.getFullYear()} ${time || '10:00'}`);
  if (!Number.isNaN(guess.getTime())) return guess;
  const plain = new Date(date);
  return Number.isNaN(plain.getTime()) ? null : plain;
}
