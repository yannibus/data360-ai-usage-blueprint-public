/**
 * @description Server-side controller for the AI Usage Cockpit LWC (Tier 2 of the
 *              Data360 AI Usage Blueprint). Reads exclusively from the Data Cloud
 *              Calculated Insight DMO `AI_Usage_By_User__cio` via the native Apex
 *              Data Cloud query API (ConnectApi.CdpQuery.queryANSISQLV2) — no HTTP
 *              callout, no session id, no Named Credential are involved.
 *
 *              SECURITY NOTE: every SQL statement executed here is a static,
 *              server-side constant. No user input is ever concatenated into the
 *              SQL, so there is no SOQL/SQL-injection surface by construction.
 *
 *              CELL-TYPE NOTE: Data Cloud returns aggregate columns without their
 *              SQL alias, so all cells are read positionally from `row.rowData`.
 *              Cell value types are mixed (DECIMAL/BIGINT arrive as String, a zero
 *              DECIMAL arrives as the string "0E-18", DOUBLE/BOOLEAN arrive native),
 *              so every numeric/boolean cell is passed through a defensive coercion
 *              helper rather than being cast directly.
 *
 * @group Data360 AI Usage Blueprint
 */
public with sharing class AiUsageCockpitController {
    /** Queryable Calculated Insight DMO backing the whole cockpit. */
    private static final String CI_OBJECT = 'AI_Usage_By_User__cio';

    // ---------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------

    /**
     * @description Single entry point for the cockpit LWC. Runs the five aggregate
     *              queries against the Calculated Insight and returns one typed DTO
     *              the component can bind directly. Marked cacheable because the CI
     *              is read-only aggregated data, which lets the LWC use @wire and
     *              refreshApex for reactive refreshes.
     * @return CockpitData populated with KPIs, usage-over-time, feature split,
     *         top users and the metered/included split.
     * @throws AuraHandledException with a clean, user-facing message if the Data
     *         Cloud query layer fails, so the LWC can render a polished error state.
     */
    @AuraEnabled(cacheable=true)
    public static CockpitData getCockpitData() {
        try {
            CockpitData result = new CockpitData();
            result.kpis = loadKpis();
            result.usageOverTime = loadUsageOverTime();
            result.byFeature = loadByFeature();
            result.topUsers = loadTopUsers();
            result.meteredSplit = loadMeteredSplit();
            return result;
        } catch (Exception e) {
            throw new AuraHandledException('Unable to load AI usage data from Data Cloud: ' + e.getMessage());
        }
    }

    // ---------------------------------------------------------------------
    // Query methods (one per result set — kept separate because the shapes differ)
    // ---------------------------------------------------------------------

    /**
     * @description Headline KPIs in a single CI row: total tokens, total estimated
     *              Flex Credits, total interactions and the number of distinct
     *              features.
     */
    private static KpiSummary loadKpis() {
        String sql =
            'SELECT SUM(total_tokens__c), SUM(total_estimated_fc__c), ' +
            'SUM(nb_interactions__c), COUNT(DISTINCT feature_normalized__c) ' +
            'FROM ' +
            CI_OBJECT;

        KpiSummary kpis = new KpiSummary();
        // Default to zero so an empty Calculated Insight renders "0" everywhere
        // rather than blank/null cards in front of an audience.
        kpis.totalTokens = 0;
        kpis.totalEstimatedFc = 0;
        kpis.totalInteractions = 0;
        kpis.distinctFeatures = 0;
        List<ConnectApi.CdpQueryV2Row> rows = runQuery(sql);
        if (!rows.isEmpty()) {
            List<Object> cells = rows[0].rowData;
            kpis.totalTokens = toDecimal(cells[0]); // DECIMAL -> String
            kpis.totalEstimatedFc = toDecimal(cells[1]); // DOUBLE  -> native Double
            kpis.totalInteractions = toLong(cells[2]); // BIGINT  -> String
            kpis.distinctFeatures = toInteger(cells[3]); // COUNT DISTINCT -> Integer
        }
        return kpis;
    }

    /**
     * @description Total tokens per usage day, ascending — the time-series axis.
     *              `usage_day__c` is a timestamp string; only the leading date
     *              portion (yyyy-MM-dd) is kept for the axis label.
     */
    private static List<TimePoint> loadUsageOverTime() {
        String sql =
            'SELECT usage_day__c, SUM(total_tokens__c) ' +
            'FROM ' +
            CI_OBJECT +
            ' ' +
            'GROUP BY usage_day__c ORDER BY usage_day__c ASC';

        List<TimePoint> points = new List<TimePoint>();
        for (ConnectApi.CdpQueryV2Row row : runQuery(sql)) {
            List<Object> cells = row.rowData;
            TimePoint point = new TimePoint();
            String rawDay = toStr(cells[0]);
            point.day = rawDay == null ? null : rawDay.left(10);
            point.tokens = toDecimal(cells[1]);
            points.add(point);
        }
        return points;
    }

    /**
     * @description Total tokens per normalized feature, descending — the donut.
     *              Includes the "Untagged" bucket, whose zero total arrives as the
     *              string "0E-18" and is normalized to 0 by the coercion helper.
     */
    private static List<FeatureSlice> loadByFeature() {
        String sql =
            'SELECT feature_normalized__c, SUM(total_tokens__c) ' +
            'FROM ' +
            CI_OBJECT +
            ' ' +
            'GROUP BY feature_normalized__c ORDER BY 2 DESC';

        List<FeatureSlice> slices = new List<FeatureSlice>();
        for (ConnectApi.CdpQueryV2Row row : runQuery(sql)) {
            List<Object> cells = row.rowData;
            FeatureSlice slice = new FeatureSlice();
            slice.feature = toStr(cells[0]);
            slice.tokens = toDecimal(cells[1]);
            slices.add(slice);
        }
        return slices;
    }

    /**
     * @description Top 10 users by total tokens, with their estimated Flex Credits.
     */
    private static List<UserUsage> loadTopUsers() {
        String sql =
            'SELECT user_name__c, SUM(total_tokens__c), SUM(total_estimated_fc__c) ' +
            'FROM ' +
            CI_OBJECT +
            ' ' +
            'GROUP BY user_name__c ORDER BY 2 DESC LIMIT 10';

        List<UserUsage> users = new List<UserUsage>();
        for (ConnectApi.CdpQueryV2Row row : runQuery(sql)) {
            List<Object> cells = row.rowData;
            UserUsage user = new UserUsage();
            user.userName = toStr(cells[0]);
            user.tokens = toDecimal(cells[1]);
            user.estimatedFc = toDecimal(cells[2]);
            users.add(user);
        }
        return users;
    }

    /**
     * @description Estimated Flex Credits split by the `is_metered__c` boolean:
     *              metered = billable, non-metered = included. `is_metered__c`
     *              arrives as a native Boolean and the sum as a native Double.
     */
    private static MeteredSplit loadMeteredSplit() {
        String sql =
            'SELECT is_metered__c, SUM(total_estimated_fc__c) ' +
            'FROM ' +
            CI_OBJECT +
            ' ' +
            'GROUP BY is_metered__c';

        MeteredSplit split = new MeteredSplit();
        split.billableFc = 0;
        split.includedFc = 0;
        for (ConnectApi.CdpQueryV2Row row : runQuery(sql)) {
            List<Object> cells = row.rowData;
            Decimal amount = toDecimal(cells[1]);
            // Accumulate (+=) rather than assign: if Data Cloud ever returns more
            // than one row per metered flag (e.g. a NULL is_metered group), we sum
            // instead of letting the last row silently overwrite the bucket.
            if (toBool(cells[0])) {
                split.billableFc += amount;
            } else {
                split.includedFc += amount;
            }
        }
        return split;
    }

    // ---------------------------------------------------------------------
    // Data Cloud query execution
    // ---------------------------------------------------------------------

    /**
     * @description Executes one ANSI-SQL statement against Data Cloud and returns
     *              its rows. `sql` is always a static server-side constant built in
     *              this class — never user input — so there is no injection surface.
     * @param sql the static ANSI-SQL statement to run.
     * @return the list of result rows (never null; empty when there is no data).
     */
    private static List<ConnectApi.CdpQueryV2Row> runQuery(String sql) {
        ConnectApi.CdpQueryInput input = new ConnectApi.CdpQueryInput();
        input.sql = sql;
        ConnectApi.CdpQueryOutputV2 response = ConnectApi.CdpQuery.queryANSISQLV2(input);
        return response.data == null ? new List<ConnectApi.CdpQueryV2Row>() : response.data;
    }

    // ---------------------------------------------------------------------
    // Defensive cell coercion (Data Cloud returns mixed cell types)
    // ---------------------------------------------------------------------

    /**
     * @description Coerces any Data Cloud cell to a Decimal. Handles native numeric
     *              types and String-encoded decimals, including the scientific-
     *              notation zero "0E-18". Decimal.valueOf parses all observed forms.
     */
    private static Decimal toDecimal(Object o) {
        if (o == null) {
            return 0;
        }
        if (o instanceof Decimal) {
            return (Decimal) o;
        }
        if (o instanceof Double) {
            return Decimal.valueOf((Double) o);
        }
        if (o instanceof Integer) {
            return (Integer) o;
        }
        if (o instanceof Long) {
            return (Long) o;
        }
        if (o instanceof String) {
            String s = (String) o;
            return String.isBlank(s) ? 0 : Decimal.valueOf(s);
        }
        return 0;
    }

    /**
     * @description Coerces any Data Cloud cell to a Long (used for BIGINT/COUNT
     *              cells that arrive as long-fraction Strings such as "658.000...").
     */
    private static Long toLong(Object o) {
        return toDecimal(o).longValue();
    }

    /**
     * @description Coerces any Data Cloud cell to an Integer (used for
     *              COUNT(DISTINCT ...) which can arrive as a native Integer).
     */
    private static Integer toInteger(Object o) {
        return toDecimal(o).intValue();
    }

    /** @description Null-safe String coercion for VARCHAR / timestamp cells. */
    private static String toStr(Object o) {
        return o == null ? null : String.valueOf(o);
    }

    /**
     * @description Coerces any Data Cloud cell to a Boolean. BOOLEAN cells arrive
     *              native; anything else is parsed from its string form.
     */
    private static Boolean toBool(Object o) {
        if (o == null) {
            return false;
        }
        if (o instanceof Boolean) {
            return (Boolean) o;
        }
        return Boolean.valueOf(String.valueOf(o));
    }

    // ---------------------------------------------------------------------
    // Typed DTOs (public @AuraEnabled fields so the LWC can bind directly)
    // ---------------------------------------------------------------------

    /** @description Root payload returned to the cockpit LWC. */
    public class CockpitData {
        @AuraEnabled
        public KpiSummary kpis;
        @AuraEnabled
        public List<TimePoint> usageOverTime;
        @AuraEnabled
        public List<FeatureSlice> byFeature;
        @AuraEnabled
        public List<UserUsage> topUsers;
        @AuraEnabled
        public MeteredSplit meteredSplit;
    }

    /** @description The four headline KPI numbers. */
    public class KpiSummary {
        @AuraEnabled
        public Decimal totalTokens;
        @AuraEnabled
        public Decimal totalEstimatedFc;
        @AuraEnabled
        public Long totalInteractions;
        @AuraEnabled
        public Integer distinctFeatures;
    }

    /** @description One point on the usage-over-time axis. */
    public class TimePoint {
        @AuraEnabled
        public String day;
        @AuraEnabled
        public Decimal tokens;
    }

    /** @description One slice of the by-feature donut. */
    public class FeatureSlice {
        @AuraEnabled
        public String feature;
        @AuraEnabled
        public Decimal tokens;
    }

    /** @description One row of the top-users bar chart. */
    public class UserUsage {
        @AuraEnabled
        public String userName;
        @AuraEnabled
        public Decimal tokens;
        @AuraEnabled
        public Decimal estimatedFc;
    }

    /** @description Metered (billable) vs non-metered (included) Flex Credits. */
    public class MeteredSplit {
        @AuraEnabled
        public Decimal billableFc;
        @AuraEnabled
        public Decimal includedFc;
    }
}
