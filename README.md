# Shia Compass

**Take the Shia Compass Test: see where you align with traditional and contemporary scholars.**

A single-page web app built on the three spectrums Zoheir Esmail set out in his post of 14 October 2026 (after a framing by Shaykh Dr Vinay Khetia on the Shia Research Institute podcast):

1. **Modernist ↔ Traditionalist**: how far modern questions should reshape religious conclusions
2. **Minimalist ↔ Maximalist**: what an Imam is (Imamology)
3. **Rationalist ↔ Scripturalist**: whether reason or the transmitted texts come first

## What it does

- **Test**: 36 statements (12 per spectrum, some reverse-worded), answered on sliders from "Not at all" to "Completely"
- **Insights**: your position on each spectrum and what it means, the strongest case from the other side, reading and practices that tend to go with your position, related beliefs, and your closest scholars by match percentage
- **3D Compass**: a rotatable cube of 42 scholars from the 10th century to today, with your pin, filters by region (Iraq, Iran, Lebanon, Arabia & Gulf, Afghanistan, the West) and period, flat Front / Side / Top views, and clickable axis labels that explain the method behind each viewpoint
- **Glossary**: 44 Arabic terms, also available as tap-to-define pop-ups throughout

## Running it

It's one self-contained file. Open `index.html` in a browser, or serve the folder with any static host (for example GitHub Pages: Settings → Pages → deploy from the `main` branch).

## How user data is saved

**On the person's own device (always on).** Answers save to the browser's local storage as they're given, so the test resumes where it was left and the result is still there on return. A result code (`SC1-…`) carries the answers to another device, and on a hosted copy a `?r=` link opens a result directly. "Clear my data" deletes everything.

**Community results (optional, opt-in).** If you connect a Supabase database, the insights page offers an "Add my result" option behind a consent tick-box. People who agree add their 36 answers, three scores, result name, date and a random sharing ID, with no name, email or account. In return they see how they compare with everyone who has shared, and the community average appears on each spectrum. They can remove their result at any time. Totals stay hidden until at least 5 people have shared.

The public key can't read or change the table directly. The page can only call three database functions: add or update this browser's result, remove it, and fetch anonymous totals.

### Setting up community results

1. Create a free account at [supabase.com](https://supabase.com), then **New project**. Pick a region close to your users, such as London (`eu-west-2`).
2. In the project, open **SQL Editor → New query**, paste the whole of [`supabase/schema.sql`](supabase/schema.sql), and click **Run**.
3. Open **Project Settings → API Keys** and copy the **Project URL** and the **publishable key** (`sb_publishable_…`, or the legacy `anon` public key). Never use the secret or `service_role` key.
4. At the top of the script in `index.html`, fill in `COMMUNITY`: `url`, `key`, and the privacy-notice details `owner`, `contact` and `region`.
5. Deploy with GitHub Pages. The sharing section only appears on the hosted site, not inside a Claude artifact preview.

To see the data, use the Supabase **Table Editor** (table `results`) or the SQL Editor, for example `select archetype, count(*) from results group by 1 order by 2 desc;`.

**Your responsibilities as the data controller.** Answers about faith can reveal religious beliefs, which are special category data under UK GDPR, so the page relies on explicit consent. Before you switch sharing on:
- fill in a real name and contact address for the privacy notice
- keep the notice accurate if you change what's collected
- delete a person's row if they email their sharing ID
- delete all rows when the project closes

## Caveats

Scholar placements are approximate readings of each figure's best-known published positions and of the secondary literature. They are contestable and say nothing about piety or correctness. The test is a self-reflection tool, not a validated psychometric measure.
