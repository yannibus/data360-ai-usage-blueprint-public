# Prerequisite — Activate the "User" data stream (one time)

> **Do this once per org, before Options 1 and 2.**
> Duration: ~5 minutes + the time for a first refresh.

## Why this step

Salesforce's AI usage telemetry only records the user's **technical identifier** (a code like
`005…`), not their name. For your queries and reports to show **readable names**, Data Cloud needs
the data from the **User** object. That is what the User data stream provides.

**Without this step:** everything still works, but each row shows a `005…` code instead of a name —
so it is unreadable for per-user steering.

## Steps

1. Go to **Setup** → search for **"Data Cloud"** → open **Data Cloud Setup**.
2. Open **Data Streams**.
3. Locate the **Salesforce CRM connector** stream (the one linking your org to Data Cloud).
   - If it already exists: click it to edit.
   - If it doesn't exist yet: create it via **New** → **Salesforce CRM** connector.
4. In the list of objects to include, **check the `User` object**.
5. **Save** and let the stream **run once** (a few minutes depending on volume).

## Verify it worked

1. Open the **Data Cloud** app → **Query Editor**.
2. Paste and run:

   ```sql
   SELECT COUNT(*) FROM ssot__User__dlm;
   ```

3. The result must be **greater than 0**. If so, names will resolve in every query and report.

> If the result is 0 or the table is not found: the stream hasn't run yet, or the `User` object isn't
> checked. Redo step 4 and re-run the stream.

---

**Next step:** choose your option in the [Guide](00-Guide.md) —
[Option 1](02-Option-1-On-Demand-Queries.md) or [Option 2](03-Option-2-Report-and-Dashboard.md).
