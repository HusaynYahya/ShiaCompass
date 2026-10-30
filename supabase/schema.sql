-- Shia Compass: community results
-- Run this once in your Supabase project: Dashboard → SQL Editor → New query → paste → Run.
-- (Safe to re-run: it creates the table if missing and adds any newer columns.)
--
-- Design:
--   * One row per browser that chooses to share, keyed by a random token kept in that browser.
--   * Part 1 (51 stored slots, 49 asked) and part 2 (70 questions) are both optional; a row holds whichever were finished.
--   * The table is locked: the public (anon) key cannot read or write it directly.
--   * The page can only call three functions:
--       submit_result      add or update this browser's result (needs its token)
--       delete_result      remove this browser's result (needs its token)
--       community_summary  anonymous totals: counts, averages, histograms (nothing per person)
--   * Summaries are withheld until at least 5 people have shared, so no one can be singled out.

create table if not exists public.results (
  id              bigint generated always as identity primary key,
  token           uuid        not null unique,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  consent_version text        not null check (char_length(consent_version) between 1 and 20)
);
-- Part 1: Esmail's three spectrums
alter table public.results add column if not exists m         real     check (m between -1 and 1);  -- modernist (-1) .. traditionalist (+1)
alter table public.results add column if not exists i         real     check (i between -1 and 1);  -- minimalist (-1) .. maximalist (+1)
alter table public.results add column if not exists e         real     check (e between -1 and 1);  -- rationalist (-1) .. scripturalist (+1)
alter table public.results add column if not exists archetype text     check (char_length(archetype) between 1 and 60);
alter table public.results add column if not exists answers   smallint[] check (
  answers is null or (array_ndims(answers) = 1 and cardinality(answers) = 36 and 0 <= all (answers) and 100 >= all (answers)));
-- About you (optional, each item may be null) and part 2
-- Part 1 length check: questions are only ever appended (36 → 50 → 51 so far), so allow room to grow without re-running this.
alter table public.results drop constraint if exists results_answers_check;
alter table public.results add constraint results_answers_check check (
  answers is null or (array_ndims(answers) = 1 and cardinality(answers) between 36 and 80 and 0 <= all (answers) and 100 >= all (answers))) not valid;
alter table public.results add column if not exists about     smallint[] check (
  about is null or (array_ndims(about) = 1 and cardinality(about) = 6 and 0 <= all (about) and 10 >= all (about)));
alter table public.results add column if not exists answers2  smallint[] check (
  answers2 is null or (array_ndims(answers2) = 1 and cardinality(answers2) between 42 and 150 and 0 <= all (answers2) and 100 >= all (answers2)));
alter table public.results add column if not exists scores2   jsonb    check (scores2 is null or jsonb_typeof(scores2) = 'object');
-- Keep the part 2 length check current if an older version of this script created it with a different length.
alter table public.results drop constraint if exists results_answers2_check;
alter table public.results add constraint results_answers2_check check (
  answers2 is null or (array_ndims(answers2) = 1 and cardinality(answers2) between 42 and 150 and 0 <= all (answers2) and 100 >= all (answers2))) not valid;  -- not valid: rows saved under an earlier version (42 or 61 answers) are kept as they are
-- Older installs made these NOT NULL; part 1 is now optional.
alter table public.results alter column m drop not null, alter column i drop not null, alter column e drop not null,
  alter column archetype drop not null, alter column answers drop not null;

alter table public.results enable row level security;
-- No policies are created on purpose: with RLS on and no policies, the public key gets no rows.
revoke all on table public.results from anon, authenticated;

drop function if exists public.submit_result(uuid, real, real, real, smallint[], text, text);
create or replace function public.submit_result(
  p_token uuid, p_m real, p_i real, p_e real, p_answers smallint[], p_archetype text, p_consent text,
  p_about smallint[] default null, p_answers2 smallint[] default null, p_scores2 jsonb default null
) returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  if p_answers is null and p_answers2 is null then
    raise exception 'nothing to submit';
  end if;
  if p_scores2 is not null and (
       (select count(*) from jsonb_object_keys(p_scores2)) > 20
    or exists (select 1 from jsonb_each(p_scores2) x
               where jsonb_typeof(x.value) <> 'number' or (x.value)::text::real not between -1 and 1)) then
    raise exception 'invalid scores2';
  end if;
  insert into public.results (token, m, i, e, answers, archetype, consent_version, about, answers2, scores2)
  values (p_token, p_m, p_i, p_e, p_answers, p_archetype, p_consent, p_about, p_answers2, p_scores2)
  on conflict (token) do update
    set m = excluded.m, i = excluded.i, e = excluded.e,
        answers = excluded.answers, archetype = excluded.archetype,
        consent_version = excluded.consent_version, about = excluded.about,
        answers2 = excluded.answers2, scores2 = excluded.scores2, updated_at = now();
end;
$$;

create or replace function public.delete_result(p_token uuid)
returns boolean
language sql
security definer
set search_path = public
as $$
  with gone as (delete from public.results where token = p_token returning 1)
  select exists (select 1 from gone);
$$;

create or replace function public.community_summary()
returns json
language plpgsql
stable
security definer
set search_path = public
as $$
declare
  total bigint; n1 bigint; n2 bigint;
  bins  constant int := 20;
  keys2 constant text[] := array['p','a','pl','u','c','r','w','s','g','f','kb','mh','io','rl','mj','rb','id','sc'];
  part1 json := null; part2 json := null;
begin
  select count(*), count(m), count(scores2) into total, n1, n2 from public.results;
  if n1 >= 5 then
    part1 := json_build_object(
      'avg', (select json_build_object('m', round(avg(m)::numeric, 3), 'i', round(avg(i)::numeric, 3), 'e', round(avg(e)::numeric, 3))
              from public.results where m is not null),
      'hist', json_build_object(
        'm', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
               left join (select width_bucket(m, -1, 1.000001, bins) wb, count(*) c from public.results where m is not null group by 1) x on x.wb = b),
        'i', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
               left join (select width_bucket(i, -1, 1.000001, bins) wb, count(*) c from public.results where i is not null group by 1) x on x.wb = b),
        'e', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
               left join (select width_bucket(e, -1, 1.000001, bins) wb, count(*) c from public.results where e is not null group by 1) x on x.wb = b)));
  end if;
  if n2 >= 5 then
    part2 := (select json_object_agg(k, (select round(avg((scores2 ->> k)::numeric), 3) from public.results where scores2 ? k))
              from unnest(keys2) k);
  end if;
  return json_build_object('n', total, 'n1', n1, 'n2', n2,
    'avg', part1 -> 'avg', 'hist', part1 -> 'hist', 'avg2', part2);
end;
$$;

revoke all on function public.submit_result(uuid, real, real, real, smallint[], text, text, smallint[], smallint[], jsonb) from public;
revoke all on function public.delete_result(uuid) from public;
revoke all on function public.community_summary() from public;
grant execute on function public.submit_result(uuid, real, real, real, smallint[], text, text, smallint[], smallint[], jsonb) to anon, authenticated;
grant execute on function public.delete_result(uuid) to anon, authenticated;
-- Totals are private for now: only the project owner (dashboard / SQL Editor) can see any results.
-- To publish anonymous totals on the site later, grant this back to anon, authenticated.
revoke execute on function public.community_summary() from anon, authenticated;

-- To read the data yourself, use the Table Editor or the SQL Editor (both run with full access), e.g.
--   select archetype, count(*) from public.results group by 1 order by 2 desc;
-- For the pattern analysis, export the table as CSV (Table Editor → Export) and run analysis/patterns.py.
