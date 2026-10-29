-- Shia Compass: community results
-- Run this once in your Supabase project: Dashboard → SQL Editor → New query → paste → Run.
--
-- Design:
--   * One row per browser that chooses to share, keyed by a random token kept in that browser.
--   * The table is locked: the public (anon) key cannot read or write it directly.
--   * The page can only call three functions:
--       submit_result      add or update this browser's result (needs its token)
--       delete_result      remove this browser's result (needs its token)
--       community_summary  anonymous totals: count, averages, histograms (nothing per person)
--   * Summaries are withheld until at least 5 people have shared, so no one can be singled out.

create table if not exists public.results (
  id              bigint generated always as identity primary key,
  token           uuid        not null unique,
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  m               real        not null check (m between -1 and 1),   -- modernist (-1) .. traditionalist (+1)
  i               real        not null check (i between -1 and 1),   -- minimalist (-1) .. maximalist (+1)
  e               real        not null check (e between -1 and 1),   -- rationalist (-1) .. scripturalist (+1)
  archetype       text        not null check (char_length(archetype) between 1 and 60),
  answers         smallint[]  not null check (
                    array_ndims(answers) = 1 and cardinality(answers) = 36
                    and 0 <= all (answers) and 100 >= all (answers)),
  consent_version text        not null check (char_length(consent_version) between 1 and 20)
);

alter table public.results enable row level security;
-- No policies are created on purpose: with RLS on and no policies, the public key gets no rows.
revoke all on table public.results from anon, authenticated;

create or replace function public.submit_result(
  p_token uuid, p_m real, p_i real, p_e real,
  p_answers smallint[], p_archetype text, p_consent text
) returns void
language sql
security definer
set search_path = public
as $$
  insert into public.results (token, m, i, e, answers, archetype, consent_version)
  values (p_token, p_m, p_i, p_e, p_answers, p_archetype, p_consent)
  on conflict (token) do update
    set m = excluded.m, i = excluded.i, e = excluded.e,
        answers = excluded.answers, archetype = excluded.archetype,
        consent_version = excluded.consent_version, updated_at = now();
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
  total bigint;
  bins  constant int := 20;
begin
  select count(*) into total from public.results;
  if total < 5 then
    return json_build_object('n', total);
  end if;
  return json_build_object(
    'n', total,
    'avg', (select json_build_object(
              'm', round(avg(m)::numeric, 3),
              'i', round(avg(i)::numeric, 3),
              'e', round(avg(e)::numeric, 3)) from public.results),
    'hist', json_build_object(
      'm', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
             left join (select width_bucket(m, -1, 1.000001, bins) wb, count(*) c from public.results group by 1) x on x.wb = b),
      'i', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
             left join (select width_bucket(i, -1, 1.000001, bins) wb, count(*) c from public.results group by 1) x on x.wb = b),
      'e', (select json_agg(coalesce(c, 0) order by b) from generate_series(1, bins) b
             left join (select width_bucket(e, -1, 1.000001, bins) wb, count(*) c from public.results group by 1) x on x.wb = b)
    )
  );
end;
$$;

revoke all on function public.submit_result(uuid, real, real, real, smallint[], text, text) from public;
revoke all on function public.delete_result(uuid) from public;
revoke all on function public.community_summary() from public;
grant execute on function public.submit_result(uuid, real, real, real, smallint[], text, text) to anon, authenticated;
grant execute on function public.delete_result(uuid) to anon, authenticated;
grant execute on function public.community_summary() to anon, authenticated;

-- To read the data yourself, use the Table Editor or the SQL Editor (both run with full access), e.g.
--   select archetype, count(*) from public.results group by 1 order by 2 desc;
