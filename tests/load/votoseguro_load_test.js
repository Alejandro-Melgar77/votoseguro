/**
 * VotoSeguro v3.0.0 — Official k6 Load & Concurrency Test Suite (S3-04)
 * 
 * Non-Functional Requirement (Section 12):
 * - Sub-2-second atomic ballot emission (p(95) < 2000ms) under 1,000 concurrent Virtual Users (VUs)
 * - Zero plaintext leakage (Paillier homomorphic encryption + HMAC nullifiers + Hash chain)
 * - Error rate < 1% (http_req_failed rate < 0.01)
 * 
 * Execution:
 *   k6 run tests/load/votoseguro_load_test.js
 *   k6 run -e BASE_URL=https://votoseguro-api.onrender.com/api/v1 tests/load/votoseguro_load_test.js
 */

import http from 'k6/http';
import execution from 'k6/execution';
import { check, sleep } from 'k6';
import { SharedArray } from 'k6/data';
import { Trend, Counter, Rate } from 'k6/metrics';

// Custom Metrics
const ballotCastDuration = new Trend('ballot_cast_duration', true);
const successfulVotes = new Counter('successful_votes');
const failedVotes = new Counter('failed_votes');
const ballotErrorRate = new Rate('ballot_error_rate');

// 1. Load Pre-provisioned Voters Credentials
const voters = new SharedArray('voters credentials', function () {
  try {
    const raw = open('./voters_credentials.json');
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed) && parsed.length > 0) {
      return parsed;
    }
  } catch (e) {
    // Fallback when credentials file is located in adjacent directory
    try {
      const rawAlt = open('../tests/load/voters_credentials.json');
      const parsedAlt = JSON.parse(rawAlt);
      if (Array.isArray(parsedAlt) && parsedAlt.length > 0) {
        return parsedAlt;
      }
    } catch (e2) {
      // Graceful fallback to synthetic data if not yet generated
    }
  }

  throw new Error('Genere primero voters_credentials.json con credenciales reales del entorno de carga.');
});

// 2. Concurrency Stages & Strict Quality Gates
export const options = {
  scenarios: {
    unique_voters: {
      executor: 'shared-iterations',
      vus: Math.min(Number(__ENV.VUS || 1000), voters.length),
      iterations: voters.length,
      maxDuration: '10m',
    },
  },
  thresholds: {
    // Non-functional requirement Section 12: Sub-2-second p95 for atomic cast
    'http_req_duration{endpoint:ballot_cast}': ['p(95)<2000'],
    // Full request failure rate must be under 1%
    'http_req_failed': ['rate<0.01'],
    // Custom error rate for ballot casting
    'ballot_error_rate': ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/api/v1';

export default function () {
  // Distribute unique voter records among VUs and iterations
  const vuIndex = execution.scenario.iterationInTest;
  const voter = voters[vuIndex];

  // Distribute virtual IPs to prevent single-IP rate-limiting bottlenecks
  const clientIp = `10.50.${(__VU % 250) + 1}.${(__ITER % 250) + 1}`;
  const commonHeaders = {
    'Content-Type': 'application/json',
  };

  // ---------------------------------------------------------------------------
  // STEP 1: Voter Authentication (POST /api/v1/voter/login)
  // ---------------------------------------------------------------------------
  const loginPayload = JSON.stringify({
    document_id: voter.document_id,
    credential_code: voter.credential_code,
  });

  const loginRes = http.post(`${BASE_URL}/voter/login`, loginPayload, {
    headers: commonHeaders,
    tags: { endpoint: 'voter_login' },
  });

  const loginOk = check(loginRes, {
    'login status is 200': (r) => r.status === 200,
    'access_token returned': (r) => {
      try {
        const body = JSON.parse(r.body);
        return typeof body.access_token === 'string' && body.access_token.length > 20;
      } catch (e) {
        return false;
      }
    },
  });

  if (!loginOk) {
    ballotErrorRate.add(1);
    failedVotes.add(1);
    sleep(0.5);
    return;
  }

  const token = JSON.parse(loginRes.body).access_token;
  const authHeaders = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
    'X-Forwarded-For': clientIp,
  };

  // ---------------------------------------------------------------------------
  // STEP 2: Automatic Ballot Resolution (GET /api/v1/ballot)
  // ---------------------------------------------------------------------------
  const ballotRes = http.get(`${BASE_URL}/ballot`, {
    headers: authHeaders,
    tags: { endpoint: 'get_ballot' },
  });

  const ballotOk = check(ballotRes, {
    'ballot status is 200': (r) => r.status === 200,
    'ballot has sections': (r) => {
      try {
        const b = JSON.parse(r.body);
        return Array.isArray(b.contests) && b.contests.length > 0;
      } catch (e) {
        return false;
      }
    },
  });

  if (!ballotOk) {
    ballotErrorRate.add(1);
    failedVotes.add(1);
    sleep(0.5);
    return;
  }

  // Extract contest and candidate details from dynamic ballot response if available
  let castSelections = [];
  try {
    const ballotData = JSON.parse(ballotRes.body);
    castSelections = ballotData.contests.map(contest => {
      const candidateId = contest.candidates?.length ? contest.candidates[vuIndex % contest.candidates.length].id : null;
      return { contest_id: contest.contest_id, constituency_id: contest.constituency_id,
        choice_type: candidateId ? 'CANDIDATE' : 'BLANK', candidate_id: candidateId };
    });
  } catch (err) {
    // Fallback to voter object specification
    castSelections.push({
      contest_id: voter.contest_id,
      constituency_id: voter.constituency_id,
      choice_type: voter.choice_type || 'CANDIDATE',
      candidate_id: voter.candidate_id,
    });
  }

  // ---------------------------------------------------------------------------
  // STEP 3: Atomic Ballot Cast with Paillier Homomorphic Encryption (POST /api/v1/ballot/cast)
  // ---------------------------------------------------------------------------
  const castPayload = JSON.stringify({
    selections: castSelections,
  });

  const castStartTime = new Date().getTime();
  const castRes = http.post(`${BASE_URL}/ballot/cast`, castPayload, {
    headers: authHeaders,
    tags: { endpoint: 'ballot_cast' },
  });
  const castDurationMs = new Date().getTime() - castStartTime;
  ballotCastDuration.add(castDurationMs);

  const castOk = check(castRes, {
    'cast status is 201': (r) => r.status === 201,
    'receipt_hash returned': (r) => {
      try {
        const b = JSON.parse(r.body);
        return typeof b.receipt_hash === 'string' && b.receipt_hash.length >= 32;
      } catch (e) {
        return false;
      }
    },
  });

  if (!castOk) {
    ballotErrorRate.add(1);
    failedVotes.add(1);
    sleep(0.5);
    return;
  }

  successfulVotes.add(1);
  ballotErrorRate.add(0);
  const receiptHash = JSON.parse(castRes.body).receipt_hash;

  // ---------------------------------------------------------------------------
  // STEP 4: Public Receipt Verification (GET /api/v1/receipts/{receipt_hash})
  // ---------------------------------------------------------------------------
  const receiptRes = http.get(`${BASE_URL}/receipts/${receiptHash}`, {
    headers: commonHeaders,
    tags: { endpoint: 'verify_receipt' },
  });

  check(receiptRes, {
    'receipt status is 200': (r) => r.status === 200,
    'receipt is verified': (r) => {
      try {
        const b = JSON.parse(r.body);
        return (b.found === true || b.verified === true) && b.receipt_hash === receiptHash;
      } catch (e) {
        return false;
      }
    },
  });

  // Short pause simulating realistic human transition between booth and exit
  sleep(0.2);
}
