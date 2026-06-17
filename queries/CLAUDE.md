# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

A TypeScript + SQLite e-commerce query project used to practice the Claude Agent SDK
(`@anthropic-ai/claude-agent-sdk`) and Claude Code hooks. `src/main.ts` opens a local
`ecommerce.db` (via the `sqlite` wrapper over `sqlite3`) and creates the schema; the
query modules expose typed read functions over that schema.

## Database schema

`src/schema.ts` creates the full e-commerce schema: customers, addresses, categories,
products, inventory, warehouses, orders, order_items, reviews, promotions, and related
tables. It is the source of truth for table and column names — read it before writing a
query.

## Project structure

- `src/main.ts` — entry point: opens `ecommerce.db` and runs `createSchema`.
- `src/schema.ts` — schema creation (`createSchema(db)`).
- `src/queries/` — all query modules, one per domain: `customer_queries.ts`,
  `product_queries.ts`, `order_queries.ts`, `analytics_queries.ts`,
  `inventory_queries.ts`, `promotion_queries.ts`, `review_queries.ts`,
  `shipping_queries.ts`.
- `sdk.ts` — Agent SDK playground (`npm run sdk`).
- `hooks/` — Claude Code hooks (see below).
- `scripts/init-claude.js` — renders `.claude/settings.example.json` into
  `.claude/settings.local.json`, substituting `$PWD`.
- `.env.example` — placeholder env template; copy to `.env` for any real secrets
  (`.env` is gitignored).

## Commands

```bash
npm run setup   # install deps + generate .claude/settings.local.json from the template
npm run sdk     # run sdk.ts with tsx
```

## Working with queries

Query functions are `async` and use the `sqlite` wrapper's promise API directly — there
is no manual `new Promise`/callback wrapping. Match the existing style:

- Single record: `await db.get(query, params)`.
- Multiple records: `await db.all(query, params)`.
- Always use parameterized queries (`?` placeholders) — never string-interpolate input.
- Type the `db` parameter as `Database` from `sqlite`.

Example (matches the real code):

```typescript
import { Database } from "sqlite";

export async function getCustomerByEmail(db: Database, email: string): Promise<any> {
  const query = `SELECT * FROM customers WHERE email = ?`;
  return await db.get(query, [email]);
}
```

## Claude Code hooks

Running `npm run setup` activates the hooks defined in `.claude/settings.example.json`:

- **PreToolUse** (`hooks/query_hook.js`) — on Write/Edit, uses the Agent SDK to check
  whether a new query duplicates an existing one and blocks (exit 2) with feedback if so.
  Note: the body currently early-returns `process.exit(0)`, so it is effectively a no-op
  until that guard is removed.
- **PostToolUse** (`hooks/tsc.js`) — type-checks edited `.ts`/`.tsx` files and blocks
  (exit 2) on errors. Also runs Prettier on the edited file.
- `hooks/read_hook.js` — stub intended to block reads of `.env`; the check is a TODO.

## Critical guidance

- All database queries must live in `src/queries/`.
