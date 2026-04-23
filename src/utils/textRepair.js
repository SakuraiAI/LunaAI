const SUSPICIOUS_MOJIBAKE_PATTERN = /[\u00c2\u00c3\u00c4\u00c5\u00e2\u02c7\u02d8\u02db\ufffd]/;
const CZECH_DIACRITICS_PATTERN = /[\u00e1\u010d\u010f\u00e9\u011b\u00ed\u0148\u00f3\u0159\u0161\u0165\u00fa\u016f\u00fd\u017e\u00c1\u010c\u010e\u00c9\u011a\u00cd\u0147\u00d3\u0158\u0160\u0164\u00da\u016e\u00dd\u017d]/g;

const DIRECT_REPLACEMENTS = [
  ['\u00e2\u20ac\u2122', "'"],
  ['\u00e2\u20ac\u02dc', "'"],
  ['\u00e2\u20ac\u0153', '"'],
  ['\u00e2\u20ac\ufffd', '"'],
  ['\u00e2\u20ac\u201c', '-'],
  ['\u00e2\u20ac\u201d', '-'],
  ['\u00e2\u20ac\u00a6', '...'],
  ['\u00c2\u00a0', ' '],
  ['\u00c2', ''],
  ['\u0102\u02c7', '\u00e1'],
  ['\u00c4\u0164', '\u010d'],
  ['\u00c4\u0179', '\u010f'],
  ['\u00c4\u203a', '\u011b'],
  ['\u0102\u00ad', '\u00ed'],
  ['\u0139\u0088', '\u0148'],
  ['\u0139\u2122', '\u0159'],
  ['\u0139\u02c7', '\u0161'],
  ['\u0139\u0104', '\u0165'],
  ['\u0139\u017b', '\u016f'],
  ['\u0102\u02dd', '\u00fd'],
  ['\u0139\u013e', '\u017e'],
  ['\u0102\u0081', '\u00c1'],
  ['\u00c4\u015a', '\u010c'],
  ['\u00c4\u017d', '\u010e'],
  ['\u00c4\u0161', '\u011a'],
  ['\u0102\u0164', '\u00cd'],
  ['\u0139\u2021', '\u0147'],
  ['\u0102\u201c', '\u00d3'],
  ['\u0139\u0098', '\u0158'],
  ['\u0139\u00a0', '\u0160'],
  ['\u0139\u00a4', '\u0164'],
  ['\u0102\u0161', '\u00da'],
  ['\u0139\u00ae', '\u016e'],
  ['\u0102\u0165', '\u00dd'],
  ['\u0139\u02dd', '\u017d'],
  ['\u00c3\u00a1', '\u00e1'],
  ['\u00c3\u00a9', '\u00e9'],
  ['\u00c3\u00ad', '\u00ed'],
  ['\u00c3\u00b3', '\u00f3'],
  ['\u00c3\u00ba', '\u00fa'],
  ['\u00c3\u00bd', '\u00fd'],
  ['\u00c3\u0081', '\u00c1'],
  ['\u00c3\u008d', '\u00cd'],
  ['\u00c3\u0093', '\u00d3'],
  ['\u00c3\u009a', '\u00da'],
  ['\u00c3\u009d', '\u00dd'],
];

const UTF8_DECODER = new TextDecoder('utf-8', { fatal: false });
const UTF8_STRICT_DECODER = new TextDecoder('utf-8', { fatal: true });

function createSingleByteReverseMap(label) {
  try {
    const bytes = Uint8Array.from(Array.from({ length: 256 }, (_, index) => index));
    const decoded = new TextDecoder(label).decode(bytes);
    const reverseMap = new Map();
    Array.from(decoded).forEach((char, index) => {
      if (!reverseMap.has(char)) {
        reverseMap.set(char, index);
      }
    });
    return reverseMap;
  } catch {
    return null;
  }
}

const WINDOWS_1250_REVERSE_MAP = createSingleByteReverseMap('windows-1250');
const WINDOWS_1252_REVERSE_MAP = createSingleByteReverseMap('windows-1252');

function scoreText(value) {
  if (!value) return Number.POSITIVE_INFINITY;

  let score = 0;
  const suspiciousHits = value.match(SUSPICIOUS_MOJIBAKE_PATTERN);
  const czechHits = value.match(CZECH_DIACRITICS_PATTERN);

  score += (suspiciousHits ? suspiciousHits.length : 0) * 5;
  score -= (czechHits ? czechHits.length : 0) * 3;

  if (value.includes('\ufffd')) score += 12;
  if (/\u00c3[\u02c7\u00a1-\u00bf]/.test(value)) score += 8;
  if (/\u00c4[\u0159\u02c7\u010d]/.test(value)) score += 8;
  if (/\u00c5[\u2122\u00be\u00a1]/.test(value)) score += 8;

  return score;
}

function decodeUtf8(bytes) {
  try {
    return UTF8_STRICT_DECODER.decode(bytes);
  } catch {
    return UTF8_DECODER.decode(bytes);
  }
}

function encodeWithReverseMap(value, reverseMap) {
  if (!reverseMap) return null;

  const bytes = [];
  for (const char of value) {
    if (reverseMap.has(char)) {
      bytes.push(reverseMap.get(char));
      continue;
    }

    const codePoint = char.codePointAt(0);
    if (typeof codePoint === 'number' && codePoint >= 0 && codePoint <= 0x7f) {
      bytes.push(codePoint);
      continue;
    }

    return null;
  }

  return Uint8Array.from(bytes);
}

function tryUtf8Repair(value, reverseMap) {
  const bytes = encodeWithReverseMap(value, reverseMap);
  if (!bytes) return value;
  return decodeUtf8(bytes);
}

export function repairDisplayedText(value) {
  const original = String(value ?? '').replace(/\r\n/g, '\n');
  if (!original) return '';

  let replaced = original;
  for (const [source, target] of DIRECT_REPLACEMENTS) {
    replaced = replaced.split(source).join(target);
  }

  if (!SUSPICIOUS_MOJIBAKE_PATTERN.test(original) && !SUSPICIOUS_MOJIBAKE_PATTERN.test(replaced)) {
    return replaced;
  }

  const candidates = [
    original,
    replaced,
    tryUtf8Repair(original, WINDOWS_1250_REVERSE_MAP),
    tryUtf8Repair(original, WINDOWS_1252_REVERSE_MAP),
    tryUtf8Repair(replaced, WINDOWS_1250_REVERSE_MAP),
    tryUtf8Repair(replaced, WINDOWS_1252_REVERSE_MAP),
  ].filter(Boolean);

  let best = candidates[0] || original;
  let bestScore = scoreText(best);
  for (const candidate of candidates.slice(1)) {
    const candidateScore = scoreText(candidate);
    if (candidateScore < bestScore) {
      best = candidate;
      bestScore = candidateScore;
    }
  }

  return best;
}

export function normalizeTransportText(value) {
  return repairDisplayedText(value).replace(/\r\n/g, '\n');
}
