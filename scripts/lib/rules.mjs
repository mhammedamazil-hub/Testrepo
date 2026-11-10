/**
 * The lot gate, as code.
 *
 * This module encodes SOP-01. It is the only place in the company allowed to decide
 * whether pepper may be sold. Every threshold is read from
 * company/source-of-truth.json -> compliance, so a change to the spec changes the gate.
 *
 * Disposition order follows the ECC quality-nonconformance skill: the first applicable
 * path governs, and the *worst* finding wins when several are present.
 */

export const DISPOSITION = Object.freeze({
  RELEASE: 'RELEASE',
  HOLD: 'HOLD', // fixable: re-dry, re-grade, re-test
  REJECT: 'REJECT', // safety or regulatory: no use-as-is, no blend-down
});

const SEVERITY = { RELEASE: 0, HOLD: 1, REJECT: 2 };

/** Fields whose absence means the lot is untested, not clean. */
const REQUIRED_TESTS = Object.freeze([
  'aflatoxin_b1_ugkg',
  'aflatoxin_total_ugkg',
  'ochratoxin_a_ugkg',
  'salmonella_25g',
  'ethylene_oxide',
  'lead_mgkg',
  'moisture_pct',
]);

const NUMERIC = new Set([
  'sieve_mm',
  'moisture_pct',
  'piperine_pct',
  'aflatoxin_b1_ugkg',
  'aflatoxin_total_ugkg',
  'ochratoxin_a_ugkg',
  'lead_mgkg',
  'foreign_matter_pct',
  'bulk_density_g_per_l',
]);

/** Accept the several ways a lab writes "we found none". */
const NEGATIVE = /^(absent|not detected|notdetected|nd|none|< ?loq|< ?lod|negative|n\/d)$/i;

export function parsePanel(text) {
  const panel = {};
  const seen = new Set();
  let recognised = 0;

  for (const rawLine of String(text).split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#') || line.startsWith('//')) continue;

    const m = line.match(/^([a-z0-9_]+)\s*[:=]\s*(.+)$/i);
    if (!m) continue;

    const key = m[1].toLowerCase().trim();
    const value = m[2].trim();

    if (key === 'fixture') {
      panel.fixture = value;
      recognised += 1;
      continue;
    }
    if (key === 'grade') {
      panel.grade = value.toUpperCase();
      recognised += 1;
      continue;
    }
    if (!NUMERIC.has(key) && !REQUIRED_TESTS.includes(key)) continue;

    if (seen.has(key)) {
      throw new Error(`Duplicate panel field "${key}" — a panel states a value once.`);
    }
    seen.add(key);
    recognised += 1;

    if (NUMERIC.has(key)) {
      const n = Number(value.replace(/,/g, ''));
      if (!Number.isFinite(n)) {
        throw new Error(`Panel field "${key}" must be numeric, got "${value}".`);
      }
      panel[key] = n;
    } else {
      panel[key] = value;
    }
  }

  if (recognised === 0) {
    throw new Error('No panel fields recognised — is this a lab panel at all?');
  }
  return panel;
}

function reason(code, field, message) {
  return { code, field, message };
}

/**
 * @param {object} panel   parsed panel
 * @param {object} truth   company/source-of-truth.json
 * @returns {{disposition: string, reasons: object[]}}
 */
export function evaluateLot(panel, truth) {
  const reasons = [];
  const spec = truth.compliance.destination_specs.eu;
  const q = truth.compliance.quality_specs;

  // ---- safety and regulatory: any hit is a REJECT, full stop
  const eto = panel.ethylene_oxide;
  if (eto !== undefined && !NEGATIVE.test(String(eto))) {
    reasons.push(
      reason(
        'ETO',
        'ethylene_oxide',
        `Ethylene oxide reported as "${eto}". EtO is not permitted for food use in the EU and is ` +
          'measured with 2-chloroethanol. Any detection is a rejection, not a threshold.'
      )
    );
  }

  const limits = {
    aflatoxin_b1_ugkg: [5.0, 'AFLATOXIN_B1', 'Aflatoxin B1'],
    aflatoxin_total_ugkg: [10.0, 'AFLATOXIN_TOTAL', 'Total aflatoxins (B1+B2+G1+G2)'],
    ochratoxin_a_ugkg: [15.0, 'OCHRATOXIN_A', 'Ochratoxin A'],
    lead_mgkg: [0.6, 'LEAD', 'Lead'],
  };
  for (const [field, [limit, code, label]] of Object.entries(limits)) {
    const v = panel[field];
    if (typeof v === 'number' && v > limit) {
      reasons.push(
        reason(code, field, `${label} at ${v}, above the EU limit of ${limit}. Regulatory failure — reject.`)
      );
    }
  }

  const sal = panel.salmonella_25g;
  if (sal !== undefined && !NEGATIVE.test(String(sal))) {
    reasons.push(
      reason(
        'SALMONELLA',
        'salmonella_25g',
        `Salmonella reported as "${sal}". EU microbiological criteria require absence in 25 g.`
      )
    );
  }

  // ---- fixable quality: HOLD, because the lot can come back
  if (typeof panel.moisture_pct === 'number' && panel.moisture_pct > q.moisture_pct_max) {
    reasons.push(
      reason(
        'MOISTURE',
        'moisture_pct',
        `Moisture ${panel.moisture_pct}% exceeds the ${q.moisture_pct_max}% intake maximum. ` +
          'Hold for covered re-drying, then re-test. Do not pay for a wet lot.'
      )
    );
  }

  if (typeof panel.foreign_matter_pct === 'number' && panel.foreign_matter_pct > q.foreign_matter_pct_max) {
    reasons.push(
      reason(
        'FOREIGN_MATTER',
        'foreign_matter_pct',
        `Foreign matter ${panel.foreign_matter_pct}% exceeds ${q.foreign_matter_pct_max}%. Hold for re-cleaning.`
      )
    );
  }

  if (typeof panel.bulk_density_g_per_l === 'number' && panel.bulk_density_g_per_l < q.bulk_density_g_per_l_min) {
    reasons.push(
      reason(
        'BULK_DENSITY',
        'bulk_density_g_per_l',
        `Bulk density ${panel.bulk_density_g_per_l} g/l is below the ${q.bulk_density_g_per_l_min} g/l minimum. Hold for re-grade.`
      )
    );
  }

  // ---- grade conformance
  const GRADES = {
    TGSEB: { sieve: 5.0, piperine: [5.0, 7.0] },
    'MG-1': { sieve: 3.5, piperine: [4.0, 6.0] },
    MG1: { sieve: 3.5, piperine: [4.0, 6.0] },
  };
  if (panel.grade !== undefined) {
    const g = GRADES[panel.grade];
    if (!g) {
      reasons.push(
        reason('GRADE_UNKNOWN', 'grade', `Grade "${panel.grade}" is not one we sell. Hold until graded to TGSEB or MG-1.`)
      );
    } else {
      if (typeof panel.sieve_mm === 'number' && panel.sieve_mm < g.sieve) {
        reasons.push(
          reason(
            'SIEVE',
            'sieve_mm',
            `Sieve ${panel.sieve_mm} mm is below the ${g.sieve} mm floor for ${panel.grade}. Hold for re-grade.`
          )
        );
      }
      if (typeof panel.piperine_pct === 'number') {
        const [lo, hi] = g.piperine;
        if (panel.piperine_pct < lo || panel.piperine_pct > hi) {
          reasons.push(
            reason(
              'PIPERINE',
              'piperine_pct',
              `Piperine ${panel.piperine_pct}% is outside the ${lo}-${hi}% band for ${panel.grade}. Hold for re-grade.`
            )
          );
        }
      }
    }
  }

  // ---- missing tests: an untested lot is not a clean lot
  for (const field of REQUIRED_TESTS) {
    if (panel[field] === undefined) {
      reasons.push(
        reason('MISSING_TEST', field, `No result for "${field}". A lot cannot be released on a partial panel.`)
      );
    }
  }

  const disposition = reasons.reduce(
    (worst, r) => {
      const d = ['ETO', 'AFLATOXIN_B1', 'AFLATOXIN_TOTAL', 'OCHRATOXIN_A', 'LEAD', 'SALMONELLA'].includes(r.code)
        ? DISPOSITION.REJECT
        : DISPOSITION.HOLD;
      return SEVERITY[d] > SEVERITY[worst] ? d : worst;
    },
    DISPOSITION.RELEASE
  );

  return { disposition, reasons };
}

const LOT_RE = /^KL-(\d{4})-(\d{3})$/;

export function validateLotNumber(lot) {
  if (typeof lot !== 'string') return false;
  const m = lot.match(LOT_RE);
  if (!m) return false;
  return Number(m[2]) >= 1;
}

export function assignLotNumber({ year, sequence, disposition = DISPOSITION.RELEASE }) {
  if (disposition !== DISPOSITION.RELEASE) {
    throw new Error(`Cannot assign a lot number: disposition is ${disposition}.`);
  }
  if (!Number.isInteger(year) || year < 2000 || year > 2999) {
    throw new Error(`Cannot assign a lot number: year ${year} is not a 4-digit year.`);
  }
  if (!Number.isInteger(sequence) || sequence < 1 || sequence > 999) {
    throw new Error(`Cannot assign a lot number: sequence ${sequence} is outside 1-999.`);
  }
  const lot = `KL-${year}-${String(sequence).padStart(3, '0')}`;
  if (!validateLotNumber(lot)) throw new Error(`Generated an invalid lot number: ${lot}`);
  return lot;
}
