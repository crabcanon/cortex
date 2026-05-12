# Cortex Docs

This is the Cortex documentation site, built with Next.js and Fumadocs.

Run development server:

```bash
bun run dev
```

Open http://localhost:3000 with your browser to see the result. The root page
redirects to the Chinese docs at `/zh/docs/cortex`; English content remains
available without a locale prefix, for example `/docs/cortex`.

`bun run dev` uses Next.js with Webpack for local stability on Windows. Next.js
16 uses Turbopack by default, and Turbopack can spawn many Rust worker threads
while compiling large MDX sites. If the machine has enough memory and page file
capacity, you can run the Turbopack dev server explicitly:

```bash
bun run dev:turbo
```

Production builds use the same stable Webpack path:

```bash
bun run build
```

The Next.js config also limits static-generation workers for Windows machines
with constrained page file capacity. This makes builds slower, but avoids
worker crashes while generating the full MDX route set.

To test the Turbopack build path explicitly:

```bash
bun run build:turbo
```

## Explore

In the project, you can see:

- `lib/source.ts`: Code for content source adapter, [`loader()`](https://fumadocs.dev/docs/headless/source-api) provides the interface to access your content.
- `lib/layout.shared.tsx`: Shared options for layouts, optional but preferred to keep.

| Route                     | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `app/(home)`              | The route group for your landing page and other pages. |
| `app/docs`                | The documentation layout and pages.                    |
| `app/api/search/route.ts` | The Route Handler for search.                          |

### Fumadocs MDX

A `source.config.ts` config file has been included, you can customise different options like frontmatter schema.

Read the [Introduction](https://fumadocs.dev/docs/mdx) for further details.

## Learn More

To learn more about Next.js and Fumadocs, take a look at the following
resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js
  features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.
- [Fumadocs](https://fumadocs.dev) - learn about Fumadocs
