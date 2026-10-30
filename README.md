# Shia Compass

**Take the Shia Compass Test: see where you align with traditional and contemporary scholars.**

A single-page web app built on the three spectrums Zoheir Esmail set out in his post of 14 October 2026 (after a framing by Shaykh Dr Vinay Khetia on the Shia Research Institute podcast):

1. **Modernist ↔ Traditionalist**: how far modern questions should reshape religious conclusions
2. **Minimalist ↔ Maximalist**: what an Imam is (Imamology)
3. **Rationalist ↔ Scripturalist**: whether reason or the transmitted texts come first

A second, optional part adds 18 more axes. Nine are inspired by the [12Axes](https://12axes.github.io/) political test (social life, religion and politics, other religions, Sunni–Shia relations, ritual, religion and state, wider society, philosophy and mysticism, religious authority). Nine cover faith and practice (faith and doubt, what Karbala means, waiting for the Mahdi, inner and outer religion, approach to rulings, majority opinion, money and riba, community identity, science and scripture).

## What it does

- **About you**: six optional, unscored questions (gender, age band, family roots, country, marja', attendance), asked once before whichever part is taken first
- **Part 1 · Worldview and Methodology**: 49 statements on Zoheir Esmail's three spectrums. Some ask about each spectrum directly; others ask indirectly, about habits and tastes that tend to go with it (two use a "Not at all" to "Always" scale). New questions are always added after the existing ones, and retired ones keep their stored slot, so earlier answers and result codes still work.
- **Part 2 · Society, politics and practice**: 63 questions. 38 statements on the first nine axes (4 each, half reverse-worded, plus two on ritual: matam and bid'ah), 19 on the faith-and-practice axes (1 to 3 each; "You question the existence of God" uses a "Not at all" to "Always" scale), and 6 unscored habit questions (what you play in the car, which class you'd join, mut'ah, and so on) that are there to find patterns. Newer questions are always added after the existing ones, so earlier answers and result codes still work
- **Insights**: for part 1, your position on each spectrum and what it means, the strongest case from the other side, reading and practices that tend to go with your position, related beliefs, and your closest scholars. For part 2, a result name (such as "The Quiet Guardian" or "The Civil Pluralist", from social life, politics and other religions), the four main leanings (politics, social life, other religions, philosophy) as two-pole percentage bars (12Axes style), a "Detailed profile" that opens all 18 axes, and the scholars closest to you on those questions
- **Two 3D compasses**: part 1's cube of 43 scholars (Modernist ↔ Traditionalist × Minimalist ↔ Maximalist × Rationalist ↔ Scripturalist), and part 2's cube of the 19 scholars with documented positions (Liberal ↔ Conservative × Quietist ↔ Activist × Philosophical ↔ Anti-philosophical). Both have your pin, filters by region and period, flat Front / Side / Top views, and clickable axis labels
- **Share card**: a downloadable image, with the person's name at the top if they add one (kept only in their browser), of part 1's three spectrums, part 2's four main leanings and your closest scholars, ready to post. Scholar portraits come from `img/scholars/<id>.jpg` if you add them (see `img/scholars/README.md`); otherwise each scholar gets an initials tile
- **Glossary**: 59 Arabic terms, also available as tap-to-define pop-ups throughout

## Running it

It's one self-contained file. Open `index.html` in a browser, or serve the folder with any static host (for example GitHub Pages: Settings → Pages → deploy from the `main` branch).

## How user data is saved

**On the person's own device (always on).** Answers save to the browser's local storage as they're given, so the test resumes where it was left and the result is still there on return. A result code carries the answers to another device (`SC1-…` for part 1, `SC2-…` for part 2 plus the About-you answers), and on a hosted copy a `?r=…&r2=…` link opens results directly. "Clear my data" deletes everything.

**Community results (optional, opt-in).** If you connect a Supabase database, the insights page offers an "Add my result" option behind a consent tick-box. People who agree add their answers to whichever parts they've finished (including the optional About-you answers), their scores, result name, date and a random sharing ID, with no name, email or account. Anyone who says they're under 18 isn't offered sharing. In return they see how they compare with everyone who has shared, and the community average appears on each spectrum. They can remove their result at any time. Totals stay hidden until at least 5 people have shared.

The public key can't read or change the table directly. The page can only call three database functions: add or update this browser's result, remove it, and fetch anonymous totals.

### Setting up community results

1. Create a free account at [supabase.com](https://supabase.com), then **New project**. Pick a region close to your users, such as London (`eu-west-2`).
2. In the project, open **SQL Editor → New query**, paste the whole of [`supabase/schema.sql`](supabase/schema.sql), and click **Run**.
3. Open **Project Settings → API Keys** and copy the **Project URL** and the **publishable key** (`sb_publishable_…`, or the legacy `anon` public key). Never use the secret or `service_role` key.
4. At the top of the script in `index.html`, fill in `COMMUNITY`: `url`, `key`, and the privacy-notice details `owner`, `contact` and `region`.
5. Deploy with GitHub Pages. The sharing section only appears on the hosted site, not inside a Claude artifact preview.

To see the data, use the Supabase **Table Editor** (table `results`) or the SQL Editor, for example `select archetype, count(*) from results group by 1 order by 2 desc;`. If you ran an older `schema.sql`, just run the new one: it upgrades the table in place.

### Finding patterns

`analysis/patterns.py` looks for links in the shared results, including ones the axis labels don't predict:

1. In Supabase, open **Table Editor → results → Export → Export table as CSV**.
2. Run `pip install numpy pandas`, then `python3 analysis/patterns.py results.csv`.
3. Open `analysis/report.html`.

The report shows, for each multiple-choice answer (for example "a latmiyya in the car" or "family roots in Iraq"), how that group differs from everyone else on every axis; the strongest correlations between statements written for different axes; and a factor analysis of which statements move together. Groups under 30 people are never shown. Run `python3 analysis/patterns.py --demo` to see an example report on made-up data. `analysis/questions.json` maps each position in the stored answer arrays to its question; regenerate it if the questions change.

**Your responsibilities as the data controller.** Answers about faith can reveal religious beliefs, which are special category data under UK GDPR, so the page relies on explicit consent. Before you switch sharing on:
- fill in a real name and contact address for the privacy notice
- keep the notice accurate if you change what's collected
- delete a person's row if they email their sharing ID
- delete all rows when the project closes

## Caveats

Scholar placements are approximate readings of each figure's best-known published positions and of the secondary literature. They are contestable and say nothing about piety or correctness. The test is a self-reflection tool, not a validated psychometric measure.
