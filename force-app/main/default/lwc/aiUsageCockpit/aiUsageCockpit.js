import { LightningElement, wire } from 'lwc';
import { refreshApex } from '@salesforce/apex';
import getCockpitData from '@salesforce/apex/AiUsageCockpitController.getCockpitData';

// --- Custom Labels (EN source; FR handled downstream via fr.translation-meta.xml) ---
import Title from '@salesforce/label/c.AI_Cockpit_Title';
import Subtitle from '@salesforce/label/c.AI_Cockpit_Subtitle';
import TotalTokens from '@salesforce/label/c.AI_Cockpit_TotalTokens';
import EstimatedFc from '@salesforce/label/c.AI_Cockpit_EstimatedFc';
import Interactions from '@salesforce/label/c.AI_Cockpit_Interactions';
import ActiveFeatures from '@salesforce/label/c.AI_Cockpit_ActiveFeatures';
import UsageOverTime from '@salesforce/label/c.AI_Cockpit_UsageOverTime';
import UsageOverTimeCaption from '@salesforce/label/c.AI_Cockpit_UsageOverTimeCaption';
import ByCategory from '@salesforce/label/c.AI_Cockpit_ByCategory';
import ByCategoryCaption from '@salesforce/label/c.AI_Cockpit_ByCategoryCaption';
import ColCategory from '@salesforce/label/c.AI_Cockpit_ColCategory';
import ColAction from '@salesforce/label/c.AI_Cockpit_ColAction';
import ColCalls from '@salesforce/label/c.AI_Cockpit_ColCalls';
import ColTokens from '@salesforce/label/c.AI_Cockpit_ColTokens';
import TopUsers from '@salesforce/label/c.AI_Cockpit_TopUsers';
import TopUsersCaption from '@salesforce/label/c.AI_Cockpit_TopUsersCaption';
import MeteredSplit from '@salesforce/label/c.AI_Cockpit_MeteredSplit';
import Billable from '@salesforce/label/c.AI_Cockpit_Billable';
import Included from '@salesforce/label/c.AI_Cockpit_Included';
import Metered from '@salesforce/label/c.AI_Cockpit_Metered';
import MeteredFootnote from '@salesforce/label/c.AI_Cockpit_MeteredFootnote';
import TokensUnit from '@salesforce/label/c.AI_Cockpit_TokensUnit';
import FcUnit from '@salesforce/label/c.AI_Cockpit_FcUnit';
import LoadingMsg from '@salesforce/label/c.AI_Cockpit_LoadingMsg';
import EmptyTitle from '@salesforce/label/c.AI_Cockpit_EmptyTitle';
import EmptyMsg from '@salesforce/label/c.AI_Cockpit_EmptyMsg';
import EmptySection from '@salesforce/label/c.AI_Cockpit_EmptySection';
import ErrorTitle from '@salesforce/label/c.AI_Cockpit_ErrorTitle';
import ErrorMsg from '@salesforce/label/c.AI_Cockpit_ErrorMsg';
import Retry from '@salesforce/label/c.AI_Cockpit_Retry';
import LiveBadge from '@salesforce/label/c.AI_Cockpit_LiveBadge';
import ShareOfTotal from '@salesforce/label/c.AI_Cockpit_ShareOfTotal';

// Brand palette used for the donut slices — cycled in order. Kept in sync with
// the CSS custom properties so JS-driven SVG and CSS-driven chrome match.
const SLICE_COLORS = ['#12d8fa', '#ffd84d', '#6ea8ff', '#a855f7', '#38f9c3', '#ff8a5c'];

// Area chart viewBox geometry (unitless SVG user units; scales responsively).
const CHART_W = 640;
const CHART_H = 220;
const PAD_L = 8;
const PAD_R = 8;
const PAD_T = 24;
const PAD_B = 28;

// Donut geometry.
const DONUT_R = 60; // radius of the stroke centre-line
const DONUT_C = 2 * Math.PI * DONUT_R; // circumference

export default class AiUsageCockpit extends LightningElement {
    label = {
        Title,
        Subtitle,
        TotalTokens,
        EstimatedFc,
        Interactions,
        ActiveFeatures,
        UsageOverTime,
        UsageOverTimeCaption,
        ByCategory,
        ByCategoryCaption,
        ColCategory,
        ColAction,
        ColCalls,
        ColTokens,
        TopUsers,
        TopUsersCaption,
        MeteredSplit,
        Billable,
        Included,
        Metered,
        MeteredFootnote,
        TokensUnit,
        FcUnit,
        LoadingMsg,
        EmptyTitle,
        EmptyMsg,
        EmptySection,
        ErrorTitle,
        ErrorMsg,
        Retry,
        LiveBadge,
        ShareOfTotal
    };

    data;
    error;
    isLoading = true;
    _wiredResult; // retained for refreshApex

    @wire(getCockpitData)
    wiredCockpit(result) {
        this._wiredResult = result;
        const { data, error } = result;
        if (data) {
            this.data = data;
            this.error = undefined;
            this.isLoading = false;
        } else if (error) {
            this.error = error;
            this.data = undefined;
            this.isLoading = false;
        }
    }

    handleRetry() {
        this.isLoading = true;
        this.error = undefined;
        refreshApex(this._wiredResult).finally(() => {
            // Always clear the spinner: if the cached wire never re-emits (data
            // unchanged) the wire callback won't fire, so relying on it alone
            // would leave the spinner stuck forever. Whatever data/error we
            // already hold is the correct state to fall back to.
            this.isLoading = false;
        });
    }

    // ---------------------------------------------------------------------
    // State getters
    // ---------------------------------------------------------------------

    get showLoading() {
        return this.isLoading;
    }

    get showError() {
        return !this.isLoading && this.error;
    }

    get showEmpty() {
        return !this.isLoading && !this.error && !this.hasAnyData;
    }

    get showContent() {
        return !this.isLoading && !this.error && this.hasAnyData;
    }

    get hasAnyData() {
        if (!this.data || !this.data.kpis) {
            return false;
        }
        const k = this.data.kpis;
        return (
            this._num(k.totalTokens) > 0 ||
            this._num(k.totalInteractions) > 0 ||
            (this.data.topUsers && this.data.topUsers.length > 0)
        );
    }

    // ---------------------------------------------------------------------
    // KPI cards
    // ---------------------------------------------------------------------

    get kpiCards() {
        const k = (this.data && this.data.kpis) || {};
        return [
            {
                key: 'tokens',
                label: this.label.TotalTokens,
                value: this._formatInt(k.totalTokens),
                accent: 'cyan',
                isTokens: true
            },
            {
                key: 'fc',
                label: this.label.EstimatedFc,
                value: this._formatDecimal(k.totalEstimatedFc, 2),
                accent: 'yellow',
                isFc: true
            },
            {
                key: 'interactions',
                label: this.label.Interactions,
                value: this._formatInt(k.totalInteractions),
                accent: 'blue',
                isInteractions: true
            },
            {
                key: 'features',
                label: this.label.ActiveFeatures,
                value: this._formatInt(k.distinctFeatures),
                accent: 'violet',
                isFeatures: true
            }
        ];
    }

    // ---------------------------------------------------------------------
    // Usage over time — SVG area + line, computed from data
    // ---------------------------------------------------------------------

    get hasUsageOverTime() {
        return this.usagePoints.length > 0;
    }

    get usagePoints() {
        return (this.data && this.data.usageOverTime) || [];
    }

    /** Full geometry object for the area chart, computed in one pass. */
    get areaChart() {
        const pts = this.usagePoints;
        const innerW = CHART_W - PAD_L - PAD_R;
        const innerH = CHART_H - PAD_T - PAD_B;
        const baseline = PAD_T + innerH;

        const values = pts.map((p) => this._num(p.tokens));
        const maxVal = Math.max(1, ...values);

        // X positions: single point sits centred so it never looks like a bug.
        const xFor = (i) => {
            if (pts.length === 1) {
                return PAD_L + innerW / 2;
            }
            return PAD_L + (innerW * i) / (pts.length - 1);
        };
        const yFor = (v) => PAD_T + innerH - (innerH * v) / maxVal;

        const coords = pts.map((p, i) => ({
            x: xFor(i),
            y: yFor(this._num(p.tokens)),
            day: p.day,
            tokens: this._num(p.tokens),
            tokensLabel: this._formatInt(p.tokens),
            dayLabel: this._shortDate(p.day)
        }));

        // Build the line path (smoothed via mid-point quadratic curves).
        let linePath = '';
        if (coords.length === 1) {
            // Draw a short flat segment so the single point reads as a line.
            const c = coords[0];
            linePath = `M ${PAD_L} ${c.y} L ${CHART_W - PAD_R} ${c.y}`;
        } else {
            linePath = `M ${coords[0].x} ${coords[0].y}`;
            for (let i = 1; i < coords.length; i++) {
                const prev = coords[i - 1];
                const cur = coords[i];
                const midX = (prev.x + cur.x) / 2;
                linePath += ` Q ${prev.x} ${prev.y} ${midX} ${(prev.y + cur.y) / 2}`;
                linePath += ` T ${cur.x} ${cur.y}`;
            }
        }

        // Area path closes down to the baseline.
        let areaPath = '';
        if (coords.length === 1) {
            const c = coords[0];
            areaPath = `M ${PAD_L} ${c.y} L ${CHART_W - PAD_R} ${c.y} L ${CHART_W - PAD_R} ${baseline} L ${PAD_L} ${baseline} Z`;
        } else {
            areaPath =
                linePath +
                ` L ${coords[coords.length - 1].x} ${baseline}` +
                ` L ${coords[0].x} ${baseline} Z`;
        }

        // X-axis labels: show first, middle, last to avoid clutter.
        const labelIdx = new Set([0, Math.floor((coords.length - 1) / 2), coords.length - 1]);
        const xLabels = coords
            .map((c, i) => ({ ...c, key: `xl-${i}` }))
            .filter((_, i) => labelIdx.has(i));

        const totalTokens = values.reduce((sum, v) => sum + v, 0);
        const ariaLabel = `${this.label.UsageOverTime}: ${this._formatInt(totalTokens)} ${this.label.TokensUnit} across ${coords.length} day(s).`;

        return {
            viewBox: `0 0 ${CHART_W} ${CHART_H}`,
            areaPath,
            linePath,
            points: coords.map((c, i) => ({ ...c, key: `pt-${i}` })),
            xLabels,
            baseline,
            width: CHART_W,
            ariaLabel,
            gridLines: this._gridLines(innerH, baseline)
        };
    }

    _gridLines(innerH, baseline) {
        // 4 horizontal guide lines at 25/50/75/100% for a keynote grid feel.
        const fractions = [0.25, 0.5, 0.75, 1];
        return fractions.map((f, i) => ({
            key: `grid-${i}`,
            y: baseline - innerH * f,
            x1: PAD_L,
            x2: CHART_W - PAD_R
        }));
    }

    // ---------------------------------------------------------------------
    // By category — same donut geometry as "by feature", grouped one level
    // finer (Coworker search / Agentforce action / in-flow feature), plus a
    // detail table listing the explicit action/prompt label behind each slice.
    // ---------------------------------------------------------------------

    get categoryRows() {
        return (this.data && this.data.categoryBreakdown) || [];
    }

    get hasCategoryData() {
        return this.categoryRows.length > 0;
    }

    /** Donut geometry, built by summing the detail rows per category. */
    get categoryDonut() {
        const rows = this.categoryRows;
        const totalsByCategory = new Map();
        rows.forEach((r) => {
            const key = r.category || '—';
            totalsByCategory.set(key, (totalsByCategory.get(key) || 0) + this._num(r.tokens));
        });
        const slices = Array.from(totalsByCategory.entries())
            .map(([category, tokens]) => ({ category, tokens }))
            .sort((a, b) => b.tokens - a.tokens);

        const total = slices.reduce((sum, s) => sum + s.tokens, 0);
        const safeTotal = total > 0 ? total : 1;

        let offset = 0;
        const arcs = [];
        const legend = [];
        slices.forEach((s, i) => {
            const pct = (s.tokens / safeTotal) * 100;
            const color = SLICE_COLORS[i % SLICE_COLORS.length];
            const dash = (s.tokens / safeTotal) * DONUT_C;
            const gap = DONUT_C - dash;

            if (s.tokens > 0) {
                arcs.push({ key: `cat-arc-${i}`, color, dasharray: `${dash} ${gap}`, dashoffset: -offset, r: DONUT_R });
                offset += dash;
            }

            legend.push({
                key: `cat-leg-${i}`,
                feature: s.category,
                color,
                tokensLabel: this._formatInt(s.tokens),
                pctLabel: `${this._round(pct, 1)}%`,
                isZero: s.tokens === 0,
                style: `--slice-color:${color};`
            });
        });

        const top = slices.length ? slices[0].tokens : 0;
        const topPct = total > 0 ? this._round((top / total) * 100, 0) : 0;
        const ariaLabel = `${this.label.ByCategory}: ${slices.length} categories, largest share ${topPct}% of ${this._formatInt(total)} ${this.label.TokensUnit}.`;

        return {
            arcs,
            legend,
            hasArcs: arcs.length > 0,
            centerPct: `${topPct}%`,
            trackR: DONUT_R,
            viewBox: '0 0 160 160',
            ariaLabel
        };
    }

    /** Detail table rows: one per explicit action/prompt label, richest first. */
    get categoryDetailRows() {
        return this.categoryRows.map((r, i) => ({
            key: `cat-row-${i}`,
            category: r.category || '—',
            label: r.actionLabel || '—',
            nbLabel: this._formatInt(r.nbActions),
            tokensLabel: this._formatInt(r.tokens)
        }));
    }

    // ---------------------------------------------------------------------
    // Top users — horizontal bars
    // ---------------------------------------------------------------------

    get hasTopUsers() {
        return this.topUsers.length > 0;
    }

    get topUsers() {
        return (this.data && this.data.topUsers) || [];
    }

    get userBars() {
        const users = this.topUsers;
        const max = Math.max(1, ...users.map((u) => this._num(u.tokens)));
        return users.map((u, i) => {
            const value = this._num(u.tokens);
            // Floor the width so even a small value shows a readable bar; a lone
            // top user fills the track nicely.
            const pct = Math.max(6, this._round((value / max) * 100, 1));
            return {
                key: `bar-${i}`,
                userName: u.userName || '—',
                tokensLabel: this._formatInt(value),
                fcLabel: `${this._formatDecimal(u.estimatedFc, 2)} ${this.label.FcUnit}`,
                initials: this._initials(u.userName),
                rank: i + 1,
                barStyle: `width:${pct}%;`,
                color: SLICE_COLORS[i % SLICE_COLORS.length],
                avatarStyle: `--avatar-color:${SLICE_COLORS[i % SLICE_COLORS.length]};`
            };
        });
    }

    // ---------------------------------------------------------------------
    // Metered split
    // ---------------------------------------------------------------------

    get metered() {
        const m = (this.data && this.data.meteredSplit) || {};
        const billable = this._num(m.billableFc);
        const included = this._num(m.includedFc);
        const total = billable + included;
        const safeTotal = total > 0 ? total : 1;
        const billablePct = this._round((billable / safeTotal) * 100, 1);
        const includedPct = this._round((included / safeTotal) * 100, 1);
        return {
            billableLabel: this._formatDecimal(billable, 2),
            includedLabel: this._formatDecimal(included, 2),
            billablePct,
            includedPct,
            billableStyle: `width:${Math.max(billable > 0 ? 4 : 0, billablePct)}%;`,
            includedStyle: `width:${Math.max(included > 0 ? 4 : 0, includedPct)}%;`,
            billablePctLabel: `${billablePct}%`,
            includedPctLabel: `${includedPct}%`
        };
    }

    // ---------------------------------------------------------------------
    // Formatting helpers
    // ---------------------------------------------------------------------

    _num(v) {
        const n = Number(v);
        return Number.isFinite(n) ? n : 0;
    }

    _formatInt(v) {
        return new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(this._num(v));
    }

    _formatDecimal(v, digits) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: digits,
            maximumFractionDigits: digits
        }).format(this._num(v));
    }

    _round(v, digits) {
        const f = Math.pow(10, digits);
        return Math.round(this._num(v) * f) / f;
    }

    _shortDate(iso) {
        if (!iso) {
            return '';
        }
        // iso is yyyy-MM-dd; render as "Jun 26" without timezone drift.
        const parts = iso.split('-');
        if (parts.length < 3) {
            return iso;
        }
        const months = [
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec'
        ];
        const m = months[Number(parts[1]) - 1] || '';
        return `${m} ${Number(parts[2])}`;
    }

    _initials(name) {
        if (!name) {
            return '—';
        }
        const words = name.trim().split(/\s+/);
        const first = words[0] ? words[0][0] : '';
        const last = words.length > 1 ? words[words.length - 1][0] : '';
        return (first + last).toUpperCase();
    }
}
