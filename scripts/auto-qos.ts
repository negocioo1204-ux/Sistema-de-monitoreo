#!/usr/bin/env tsx
import { appendFileSync, existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { config as loadEnv } from 'dotenv';

import { OmadaClient, type OmadaClientOptions } from '../src/omadaClient/index.js';

const __filename = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(__filename), '..');
const envPath = path.join(repoRoot, '.env');
const envLocalPath = path.join(repoRoot, '.env.local');

loadEnv({ path: envPath });
if (existsSync(envLocalPath)) {
    loadEnv({ path: envLocalPath, override: true });
}

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

const POLL_INTERVAL_MS = Number(process.env.AUTO_QOS_POLL_INTERVAL) || 60_000;
const BANDWIDTH_LIMIT_DOWN = Number(process.env.AUTO_QOS_LIMIT_DOWN) || 5120;
const BANDWIDTH_LIMIT_UP = Number(process.env.AUTO_QOS_LIMIT_UP) || 1024;
const MAX_RULES = Number(process.env.AUTO_QOS_MAX_RULES) || 10;
const LOG_FILE = process.env.AUTO_QOS_LOG_FILE || path.join(repoRoot, 'auto-qos.log');
const DRY_RUN = process.env.AUTO_QOS_DRY_RUN !== 'false';
const AUTONOMOUS = process.env.AUTO_QOS_AUTONOMOUS !== 'false';

// ---------------------------------------------------------------------------
// Logging
// ---------------------------------------------------------------------------

function log(msg: string, data?: unknown) {
    const timestamp = new Date().toISOString();
    const line = data ? `[${timestamp}] ${msg} ${JSON.stringify(data)}` : `[${timestamp}] ${msg}`;
    console.log(line);
    try {
        appendFileSync(LOG_FILE, line + '\n');
    } catch {
        // ignore
    }
}

// ---------------------------------------------------------------------------
// State tracking – avoid redundant API calls
// ---------------------------------------------------------------------------

let lastCongestionState: 'none' | 'wlan' | 'wan' | 'both' = 'none';
const clientRateLimitCache = new Map<string, number>();

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function nowUnix(): number {
    return Math.floor(Date.now() / 1000);
}

// ---------------------------------------------------------------------------
// Control Loop Phases
// ---------------------------------------------------------------------------

async function collect(client: OmadaClient, siteId: string) {
    const results: Record<string, unknown> = {};

    try {
        results.trafficDistribution = await client.getTrafficDistribution(siteId);
    } catch (e) {
        log('collect: getTrafficDistribution failed', { error: String(e) });
    }

    try {
        results.mostActiveClients = await client.listMostActiveClients(siteId);
    } catch (e) {
        log('collect: listMostActiveClients failed', { error: String(e) });
    }

    try {
        const end = nowUnix();
        const start = end - 300;
        results.retryAndDroppedRate = await client.getRetryAndDroppedRate(siteId, start, end);
    } catch (e) {
        log('collect: getRetryAndDroppedRate failed', { error: String(e) });
    }

    try {
        results.ispLoad = await client.getIspLoad(siteId, '5m');
    } catch (e) {
        log('collect: getIspLoad failed', { error: String(e) });
    }

    try {
        results.bandwidthControlRules = await client.listBandwidthControlRules(siteId);
    } catch (e) {
        log('collect: listBandwidthControlRules failed', { error: String(e) });
    }

    return results;
}

// ---------------------------------------------------------------------------
// ML: Gaussian Naive Bayes Classifier
// ---------------------------------------------------------------------------

type TrafficClass = 'critical' | 'interactive' | 'streaming' | 'bulk' | 'background';
const TRAFFIC_CLASSES: TrafficClass[] = ['critical', 'interactive', 'streaming', 'bulk', 'background'];

class GaussianNaiveBayes {
    private means = new Map<TrafficClass, number[]>();
    private vars = new Map<TrafficClass, number[]>();
    private priors = new Map<TrafficClass, number>();
    private readonly nFeatures = 6;

    constructor() {
        for (const cls of TRAFFIC_CLASSES) {
            this.means.set(cls, new Array(this.nFeatures).fill(0));
            this.vars.set(cls, new Array(this.nFeatures).fill(1));
            this.priors.set(cls, 1 / TRAFFIC_CLASSES.length);
        }
        this.seed();
    }

    private seed() {
        const seedData: Array<{ cls: TrafficClass; features: number[] }> = [
            { cls: 'critical', features: [0.8, 0.2, 0.25, 0.05, 0.7, 0.5] },
            { cls: 'critical', features: [0.7, 0.3, 0.43, 0.04, 0.6, 0.4] },
            { cls: 'interactive', features: [0.3, 0.7, 2.33, 0.15, 0.5, 0.6] },
            { cls: 'interactive', features: [0.4, 0.6, 1.5, 0.1, 0.4, 0.5] },
            { cls: 'streaming', features: [0.9, 0.1, 0.11, 0.02, 0.8, 0.7] },
            { cls: 'streaming', features: [0.95, 0.05, 0.05, 0.01, 0.9, 0.8] },
            { cls: 'bulk', features: [0.5, 0.5, 1.0, 0.4, 0.2, 0.2] },
            { cls: 'bulk', features: [0.6, 0.4, 0.67, 0.5, 0.1, 0.1] },
            { cls: 'background', features: [0.1, 0.9, 9.0, 0.8, 0.3, 0.1] },
            { cls: 'background', features: [0.2, 0.8, 4.0, 0.6, 0.2, 0.2] },
        ];
        for (const { cls, features } of seedData) {
            this.partialFit(features, cls);
        }
    }

    partialFit(features: number[], label: TrafficClass) {
        const m = this.means.get(label)!;
        const v = this.vars.get(label)!;
        const prior = this.priors.get(label)!;
        const n = prior * TRAFFIC_CLASSES.length;
        const newN = n + 1;
        for (let i = 0; i < this.nFeatures; i++) {
            const delta = features[i] - m[i];
            m[i] = m[i] + delta / newN;
            v[i] = v[i] + delta * (features[i] - m[i]);
        }
        this.priors.set(label, newN / (TRAFFIC_CLASSES.length + 1));
    }

    predict(features: number[]): TrafficClass {
        let best: TrafficClass = 'background';
        let bestScore = -Infinity;
        for (const cls of TRAFFIC_CLASSES) {
            const prior = this.priors.get(cls)!;
            const m = this.means.get(cls)!;
            const v = this.vars.get(cls)!;
            let logProb = Math.log(prior);
            for (let i = 0; i < this.nFeatures; i++) {
                const varI = Math.max(v[i], 1e-6);
                const diff = features[i] - m[i];
                logProb += -0.5 * Math.log(2 * Math.PI * varI) - (diff * diff) / (2 * varI);
            }
            if (logProb > bestScore) {
                bestScore = logProb;
                best = cls;
            }
        }
        return best;
    }

    getClassPriority(cls: TrafficClass): number {
        const map: Record<TrafficClass, number> = {
            critical: 4,
            interactive: 3,
            streaming: 2,
            bulk: 1,
            background: 0,
        };
        return map[cls];
    }
}

// ---------------------------------------------------------------------------
// ML: Online Anomaly Detector (rolling stats)
// ---------------------------------------------------------------------------

class OnlineAnomalyDetector {
    private count = 0;
    private mean = 0;
    private m2 = 0;

    update(value: number) {
        this.count++;
        const delta = value - this.mean;
        this.mean += delta / this.count;
        this.m2 += delta * (value - this.mean);
    }

    get stats() {
        const variance = this.count > 1 ? this.m2 / (this.count - 1) : 0;
        return { mean: this.mean, stddev: Math.sqrt(variance), n: this.count };
    }

    isAnomaly(value: number, threshold = 2.5): boolean {
        if (this.count < 5) return false;
        const { mean, stddev } = this.stats;
        if (stddev < 1e-6) return false;
        return Math.abs(value - mean) / stddev > threshold;
    }
}

// ---------------------------------------------------------------------------
// ML: Congestion Predictor (logistic regression with SGD)
// ---------------------------------------------------------------------------

class CongestionPredictor {
    private weights: number[];
    private readonly lr = 0.01;
    private readonly nFeatures = 5;

    constructor() {
        this.weights = new Array(this.nFeatures + 1).fill(0);
        for (let i = 0; i < this.weights.length; i++) {
            this.weights[i] = (Math.random() - 0.5) * 0.1;
        }
    }

    private sigmoid(z: number): number {
        return 1 / (1 + Math.exp(-Math.max(-20, Math.min(20, z))));
    }

    predict(features: number[]): number {
        let z = this.weights[0];
        for (let i = 0; i < features.length; i++) {
            z += this.weights[i + 1] * features[i];
        }
        return this.sigmoid(z);
    }

    train(features: number[], actualCongestion: number) {
        const pred = this.predict(features);
        const error = pred - actualCongestion;
        this.weights[0] -= this.lr * error;
        for (let i = 0; i < features.length; i++) {
            this.weights[i + 1] -= this.lr * error * features[i];
        }
    }
}

// ---------------------------------------------------------------------------
// ML: Feature extraction
// ---------------------------------------------------------------------------

function extractTrafficFeatures(app: { name: string; rx: number; tx: number }, allApps: Array<{ name: string; rx: number; tx: number }>): number[] {
    const totalRx = allApps.reduce((s, a) => s + a.rx, 0) || 1;
    const _totalTx = allApps.reduce((s, a) => s + a.tx, 0) || 1;
    const total = totalRx + totalTx;
    const rxRatio = app.rx / totalRx;
    const txRatio = app.tx / totalTx;
    const rxtxRatio = app.tx > 0 ? app.rx / app.tx : 10;
    const pctTotal = (app.rx + app.tx) / total;
    const hour = new Date().getHours() / 24;
    const isWeekend = [0, 6].includes(new Date().getDay()) ? 1 : 0;
    return [rxRatio, txRatio, Math.min(rxtxRatio, 10), pctTotal, hour, isWeekend];
}

// ---------------------------------------------------------------------------
// ML State
// ---------------------------------------------------------------------------

const trafficClassifier = new GaussianNaiveBayes();
const retryDetector = new OnlineAnomalyDetector();
const droppedDetector = new OnlineAnomalyDetector();
const ispDetector = new OnlineAnomalyDetector();
const congestionPredictor = new CongestionPredictor();

// ---------------------------------------------------------------------------
// Analysis
// ---------------------------------------------------------------------------

interface AnalysisResult {
    congested: boolean;
    congestionType: 'wlan' | 'wan' | 'both' | 'none';
    bandwidthHogs: Array<{ name: string; mac: string; totalBytes: number }>;
    topProtocols: Array<{ name: string; rx: number; tx: number; trafficClass: TrafficClass; priority: number }>;
    retryRate: number;
    droppedRate: number;
    ispUsagePct: number;
    congestionProbability: number;
    anomalyFlags: string[];
    actionRequired: boolean;
    actions: string[];
}

function analyze(state: Record<string, unknown>): AnalysisResult {
    const result: AnalysisResult = {
        congested: false,
        congestionType: 'none',
        bandwidthHogs: [],
        topProtocols: [],
        retryRate: 0,
        droppedRate: 0,
        ispUsagePct: 0,
        congestionProbability: 0,
        anomalyFlags: [],
        actionRequired: false,
        actions: [],
    };

    // --- 1. Extract raw metrics ---
    const rdr = state.retryAndDroppedRate as Record<string, unknown> | undefined;
    const rr = rdr ? Number(rdr.retryRate ?? rdr.retry ?? 0) : 0;
    const dr = rdr ? Number(rdr.droppedRate ?? rdr.dropped ?? 0) : 0;
    result.retryRate = rr;
    result.droppedRate = dr;

    const isp = state.ispLoad as Record<string, unknown> | undefined;
    const usage = isp ? Number(isp.usage ?? isp.utilization ?? isp.load ?? 0) : 0;
    result.ispUsagePct = usage;

    // --- 2. Update anomaly detectors (online learning) ---
    retryDetector.update(rr);
    droppedDetector.update(dr);
    ispDetector.update(usage);

    if (retryDetector.isAnomaly(rr)) result.anomalyFlags.push(`retry-spike:${rr.toFixed(1)}%`);
    if (droppedDetector.isAnomaly(dr)) result.anomalyFlags.push(`dropped-spike:${dr.toFixed(1)}%`);
    if (ispDetector.isAnomaly(usage)) result.anomalyFlags.push(`isp-spike:${usage.toFixed(1)}%`);

    // --- 3. Predict congestion probability with logistic regression ---
    const clients = (state.mostActiveClients ?? []) as Array<Record<string, unknown>>;
    const activeClientCount = clients.length;
    const avgBandwidth = activeClientCount > 0 ? clients.reduce((s, c) => s + Number(c.totalTraffic ?? 0), 0) / activeClientCount / 1_048_576 : 0;
    const congestionFeatures = [usage / 100, rr / 100, dr / 100, Math.min(activeClientCount / 50, 1), Math.min(avgBandwidth / 1000, 1)];
    result.congestionProbability = congestionPredictor.predict(congestionFeatures);

    const congestionThreshold = 0.5;
    if (result.congestionProbability > congestionThreshold) {
        result.congested = true;
        if (rr > 5 && usage > 50) result.congestionType = 'both';
        else if (usage > 50) result.congestionType = 'wan';
        else result.congestionType = 'wlan';
    }

    // --- 4. Classify traffic distribution with Naive Bayes ---
    const td = state.trafficDistribution as Record<string, unknown> | undefined;
    if (td) {
        const apps = (td.applications ?? td.protocols ?? td.list ?? []) as Array<Record<string, unknown>>;
        const parsed = apps.map((a) => ({
            name: String(a.name ?? a.app ?? 'unknown'),
            rx: Number(a.rx ?? a.down ?? 0),
            tx: Number(a.tx ?? a.up ?? 0),
        }));
        const _totalRx = parsed.reduce((s, a) => s + a.rx, 0) || 1;
        const _totalTx = parsed.reduce((s, a) => s + a.tx, 0) || 1;

        const classified = parsed.map((a) => {
            const features = extractTrafficFeatures(a, parsed);
            const trafficClass = trafficClassifier.predict(features);
            return { ...a, trafficClass, priority: trafficClassifier.getClassPriority(trafficClass) };
        });
        classified.sort((a, b) => b.rx + b.tx - (a.rx + a.tx));

        result.topProtocols = classified.slice(0, 10);

        const lowPriorityTraffic = classified.filter((a) => a.priority <= 1).reduce((s, a) => s + a.rx + a.tx, 0);
        const totalTraffic = classified.reduce((s, a) => s + a.rx + a.tx, 0) || 1;
        const lowPriorityRatio = lowPriorityTraffic / totalTraffic;

        // Online training signal: bulk/background traffic during congestion = confirm label
        if (result.congested) {
            for (const a of classified.slice(0, 5)) {
                if (a.trafficClass === 'bulk' || a.trafficClass === 'background') {
                    trafficClassifier.partialFit(extractTrafficFeatures(a, classified), a.trafficClass);
                }
            }
            congestionPredictor.train(congestionFeatures, 1);
        } else if (result.congestionProbability < 0.3) {
            congestionPredictor.train(congestionFeatures, 0);
        }

        if (result.congested && lowPriorityRatio > 0.3) {
            result.actions.push('throttle-non-critical');
        }
    }

    // --- 5. Detect bandwidth hogs via anomaly ---
    const hogDetector = new OnlineAnomalyDetector();
    const activeClients = clients
        .map((c) => ({
            name: String(c.name ?? c.clientName ?? 'unknown'),
            mac: String(c.mac ?? ''),
            totalBytes: Number(c.totalTraffic ?? c.traffic ?? 0),
        }))
        .sort((a, b) => b.totalBytes - a.totalBytes);

    for (const c of activeClients) {
        hogDetector.update(c.totalBytes / 1_048_576);
    }
    result.bandwidthHogs = activeClients.filter((c) => {
        const mbVal = c.totalBytes / 1_048_576;
        return hogDetector.isAnomaly(mbVal, 2.0) && mbVal > 100;
    });

    if (result.bandwidthHogs.length > 0) result.actions.push('rate-limit-hogs');

    // --- 6. AP utilization decision ---
    if (result.congestionType === 'wlan' && result.retryRate > 15) {
        result.actions.push('reduce-ap-utilization');
    }

    result.actionRequired = result.actions.length > 0;

    if (result.actionRequired) {
        log('ML analyze', {
            congestionProbability: result.congestionProbability.toFixed(3),
            congestionType: result.congestionType,
            anomalies: result.anomalyFlags,
            actions: result.actions,
            hogCount: result.bandwidthHogs.length,
            topTraffic: result.topProtocols.slice(0, 3).map((t) => `${t.name}(${t.trafficClass})`),
        });
    }

    return result;
}

// Export for online training in collect phase
function trainFromObservation(prevState: Record<string, unknown>, prevResult: AnalysisResult) {
    const rdr = prevState.retryAndDroppedRate as Record<string, unknown> | undefined;
    const isp = prevState.ispLoad as Record<string, unknown> | undefined;
    const rr = rdr ? Number(rdr.retryRate ?? 0) : 0;
    const dr = rdr ? Number(rdr.droppedRate ?? 0) : 0;
    const usage = isp ? Number(isp.usage ?? 0) : 0;
    const features = [usage / 100, rr / 100, dr / 100, 0, 0];
    const label = prevResult.congested ? 1 : 0;
    congestionPredictor.train(features, label);
}

async function act(client: OmadaClient, siteId: string, analysis: AnalysisResult, state: Record<string, unknown>) {
    if (!analysis.actionRequired) {
        if (lastCongestionState !== 'none') {
            log('act: congestion cleared, removing temporary rules');
            await removeAllTempRules(client, siteId, state);
            lastCongestionState = 'none';
        }
        return;
    }

    if (DRY_RUN) {
        log('act: DRY RUN — would apply', { actions: analysis.actions });
        return;
    }

    lastCongestionState = analysis.congestionType;

    // Action 1: Rate-limit bandwidth hogs
    if (analysis.actions.includes('rate-limit-hogs') && analysis.bandwidthHogs.length > 0) {
        for (const hog of analysis.bandwidthHogs) {
            if (!hog.mac) {
                log('act: skipping hog without MAC', { name: hog.name });
                continue;
            }
            const lastLimit = clientRateLimitCache.get(hog.mac);
            if (lastLimit && Date.now() - lastLimit < 120_000) {
                continue;
            }
            try {
                await client.setClientRateLimit(hog.mac, BANDWIDTH_LIMIT_DOWN, BANDWIDTH_LIMIT_UP, siteId);
                clientRateLimitCache.set(hog.mac, Date.now());
                log('act: rate-limited client', { name: hog.name, mac: hog.mac, down: BANDWIDTH_LIMIT_DOWN, up: BANDWIDTH_LIMIT_UP });
            } catch (e) {
                log('act: setClientRateLimit failed', { mac: hog.mac, error: String(e) });
            }
        }
    }

    // Action 2: Throttle non-critical traffic via bandwidth control (ML-classified)
    if (analysis.actions.includes('throttle-non-critical') && analysis.topProtocols.length > 0) {
        const existingRules = (state.bandwidthControlRules ?? []) as Array<Record<string, unknown>>;
        const lowPriorityApps = analysis.topProtocols.filter((p) => p.priority <= 1).slice(0, 3);

        if (existingRules.length < MAX_RULES) {
            for (const app of lowPriorityApps) {
                try {
                    await client.createBandwidthCtrlRule(
                        {
                            name: `auto-qos-${app.name}-${Date.now()}`,
                            description: 'auto-qos: reduced priority during congestion',
                            downLimit: Math.floor(BANDWIDTH_LIMIT_DOWN / 2),
                            upLimit: Math.floor(BANDWIDTH_LIMIT_UP / 2),
                            protocolApps: [app.name],
                        },
                        siteId
                    );
                    log('act: throttled non-critical traffic', { app: app.name });
                } catch (e) {
                    log('act: createBandwidthCtrlRule failed', { app: app.name, error: String(e) });
                }
            }
        }
    }

    // Action 3: Reduce AP utilization (extreme WLAN congestion)
    if (analysis.actions.includes('reduce-ap-utilization') && AUTONOMOUS) {
        try {
            const devices = await client.listDevices(siteId);
            const aps = devices.filter((d) => d.type === 'ap' || d.type === 'eap');
            for (const ap of aps.slice(0, 3)) {
                try {
                    await client.setApQosConfig(ap.mac, {
                        downLink: Math.floor(BANDWIDTH_LIMIT_DOWN * 0.7),
                        upLink: Math.floor(BANDWIDTH_LIMIT_UP * 0.7),
                        downLinkEnabled: true,
                        upLinkEnabled: true,
                    });
                    log('act: reduced AP QoS', { ap: ap.name ?? ap.mac });
                } catch (e) {
                    log('act: setApQosConfig failed', { ap: ap.mac, error: String(e) });
                }
            }
        } catch (e) {
            log('act: listDevices failed', { error: String(e) });
        }
    }
}

async function removeAllTempRules(client: OmadaClient, siteId: string, state: Record<string, unknown>) {
    const rules = (state.bandwidthControlRules ?? []) as Array<Record<string, unknown>>;
    for (const rule of rules) {
        const desc = String(rule.description ?? '');
        const name = String(rule.name ?? '');
        if (desc.includes('auto-qos') || name.startsWith('auto-qos')) {
            try {
                await client.deleteBandwidthCtrlRule(String(rule.id), siteId);
                log('act: removed auto-qos rule', { id: rule.id, name });
            } catch (e) {
                log('act: deleteBandwidthCtrlRule failed', { id: rule.id, error: String(e) });
            }
        }
    }
}

// ---------------------------------------------------------------------------
// CLI argument handling
// ---------------------------------------------------------------------------

function showHelp() {
    console.log(
        `
auto-qos.ts — AI-powered Dynamic QoS for Omada networks

Usage:
  npx tsx scripts/auto-qos.ts [options]

Options:
  --once       Run a single collection/analysis/action cycle and exit
  --help       Show this help

Environment Variables (AUTO_QOS_*):
  AUTO_QOS_POLL_INTERVAL      Polling interval in ms (default: 60000)
  AUTO_QOS_LIMIT_DOWN         Rate limit download Kbps (default: 5120)
  AUTO_QOS_LIMIT_UP           Rate limit upload Kbps (default: 1024)
  AUTO_QOS_MAX_RULES          Max auto-generated bandwidth control rules (default: 10)
  AUTO_QOS_LOG_FILE           Log file path (default: auto-qos.log in project root)
  AUTO_QOS_DRY_RUN            Log actions without applying them (default: true)
  AUTO_QOS_AUTONOMOUS         Allow autonomous AP QoS changes (default: true)

Reuses OMADA_* env vars for controller connection.
    `.trim()
    );
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
    if (process.argv.includes('--help')) {
        showHelp();
        process.exit(0);
    }

    const required = ['OMADA_BASE_URL', 'OMADA_CLIENT_ID', 'OMADA_CLIENT_SECRET', 'OMADA_OMADAC_ID'];
    for (const key of required) {
        if (!process.env[key]) {
            console.error(`ERROR: Missing required env var: ${key}`);
            process.exit(1);
        }
    }

    const clientOptions: OmadaClientOptions = {
        baseUrl: process.env.OMADA_BASE_URL!.replace(/\/$/, ''),
        clientId: process.env.OMADA_CLIENT_ID!,
        clientSecret: process.env.OMADA_CLIENT_SECRET!,
        omadacId: process.env.OMADA_OMADAC_ID!,
        siteId: process.env.OMADA_SITE_ID,
        strictSsl: process.env.OMADA_STRICT_SSL !== 'false',
        requestTimeout: Number(process.env.OMADA_TIMEOUT) || 30000,
    };

    log('auto-qos starting', {
        pollInterval: `${POLL_INTERVAL_MS}ms`,
        dryRun: DRY_RUN,
        autonomous: AUTONOMOUS,
        classifiers: 'GaussianNB(6-features) + LogisticRegression(5-features) + AnomalyDetector(Welford)',
        limitDown: `${BANDWIDTH_LIMIT_DOWN}Kbps`,
        limitUp: `${BANDWIDTH_LIMIT_UP}Kbps`,
    });

    const client = new OmadaClient(clientOptions);

    // Resolve default site if not set
    let siteId = clientOptions.siteId ?? '';
    if (!siteId) {
        try {
            const sites = await client.listSites();
            if (sites.length === 0) {
                log('ERROR: No sites found');
                process.exit(1);
            }
            siteId = sites[0].id;
            log(`auto-qos: using site "${sites[0].name}" (${siteId})`);
        } catch (e) {
            log('ERROR: Failed to list sites', { error: String(e) });
            process.exit(1);
        }
    }

    const runOnce = process.argv.includes('--once');

    // Control loop
    let iteration = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
        iteration++;
        const cycleStart = Date.now();
        log(`--- cycle ${iteration} ---`);

        const collected = await collect(client, siteId);
        const analysis = analyze(collected);

        if (analysis.actionRequired) {
            log(`actions: ${analysis.actions.join(', ')}`);
            await act(client, siteId, analysis, collected);
        } else {
            log('all clear — no action needed');
        }

        if (runOnce) {
            log('--once specified, exiting');
            process.exit(0);
        }

        trainFromObservation(collected, analysis);
        const elapsed = Date.now() - cycleStart;
        const wait = Math.max(1000, POLL_INTERVAL_MS - elapsed);
        log(`cycle done in ${elapsed}ms, next in ${wait}ms\n`);
        await new Promise((r) => setTimeout(r, wait));
    }
}

main().catch((e) => {
    log('FATAL', { error: String(e) });
    process.exit(1);
});
