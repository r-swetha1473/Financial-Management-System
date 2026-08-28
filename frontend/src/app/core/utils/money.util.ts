/** Decimal-safe money formatting — display only, no float arithmetic. */

export function formatCurrencyInr(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') {
    return '₹0.00';
  }

  const normalized = String(value).replace(/,/g, '');
  const negative = normalized.startsWith('-');
  const [wholePart, fractionPart = '00'] = normalized.replace('-', '').split('.');
  const paddedFraction = `${fractionPart}00`.slice(0, 2);
  const groupedWhole = wholePart.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  return `${negative ? '-' : ''}₹${groupedWhole}.${paddedFraction}`;
}

export function parseMoneyInput(value: string): string {
  const cleaned = value.replace(/[^0-9.-]/g, '');
  if (!cleaned || cleaned === '-' || cleaned === '.') {
    return '0.00';
  }
  const [whole, fraction = ''] = cleaned.split('.');
  return `${whole}.${`${fraction}00`.slice(0, 2)}`;
}

/** True when empty (optional) or a non-negative decimal. Rejects letters; does not strip them. */
export function isValidOptionalMoney(value: string): boolean {
  const trimmed = value.trim();
  if (!trimmed) {
    return true;
  }
  return /^\d+(\.\d{1,4})?$/.test(trimmed.replace(/,/g, ''));
}

function toMinor(val: string): number {
  const normalized = String(val).replace(/,/g, '');
  const negative = normalized.startsWith('-');
  const [whole, fraction = '00'] = normalized.replace('-', '').split('.');
  const minor = Number(whole || '0') * 100 + Number(`${fraction}00`.slice(0, 2));
  return negative ? -minor : minor;
}

function fromMinor(minor: number): string {
  const negative = minor < 0;
  const abs = Math.abs(minor);
  const whole = Math.floor(abs / 100);
  const fraction = String(abs % 100).padStart(2, '0');
  return `${negative ? '-' : ''}${whole}.${fraction}`;
}

export function compareMoney(a: string, b: string): number {
  return toMinor(a) - toMinor(b);
}

export function addMoney(a: string, b: string): string {
  return fromMinor(toMinor(a) + toMinor(b));
}

export function subtractMoney(a: string, b: string): string {
  return fromMinor(toMinor(a) - toMinor(b));
}
