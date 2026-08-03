---
title: "Demographic Data Sources for Grounded Persona Generation"
status: "Research — verified 2026-08-03"
version: "1.0.0"
owner: "askthepeople-persistence-engineer"
last_reviewed: "2026-08-03"
---

# Demographic Data Sources for Grounded Persona Generation

## Purpose and scope

This document evaluates real population-data sources that could replace
LLM-invented demographic attributes (age, income, education, occupation,
location) in persona generation with values sampled from actual population
distributions.

This is a research and verification document. It contains no production code
and prescribes no implementation. It records what was tested live on
2026-08-03, what could only be read from documentation, and what the
licensing position is for a commercial product.

Every claim below is labelled:

- **VERIFIED** — a live request was issued and a real response received. The
  response snippet is pasted.
- **PARTIAL** — the endpoint responded, but the data path itself could not be
  exercised (for example, authentication blocked it). The exact observed
  status code is given.
- **UNVERIFIED** — taken from vendor documentation only, with no successful
  live confirmation.

Related reading: persona structure is discussed in
[persona-depth-analysis.md](./persona-depth-analysis.md); the persistence
layer is described in [data-model.md](../architecture/data-model.md).

## Headline findings

Four findings change the obvious plan and are stated up front.

1. **The Census data API now requires a key.** Keyless data queries do not
   return data and do not return an error code either — they answer HTTP 302
   redirecting to a "Missing Key" HTML page. Widely repeated guidance that
   500 queries per day are allowed without a key did not hold in testing, and
   the current Census terms of service contain no such numeric allowance.
2. **Census PUMS microdata is downloadable in bulk with no key at all,**
   from `www2.census.gov`, under a Creative Commons Zero public-domain
   dedication. This is a better fit than the keyed API for this use case.
3. **IPUMS is the wrong dependency for a commercial product,** not because of
   data quality (which is excellent) but because of redistribution terms.
   IPUMS USA requires permission to redistribute; IPUMS International
   prohibits commercial use outright. Census PUMS provides substantially the
   same US microdata with no such restriction.
4. **Independent sampling from marginal distributions is measurably broken.**
   Using real Wyoming microdata, it produced 2.72% logically impossible
   age/education pairs and destroyed the education/income correlation
   (0.210 collapsed to 0.008). Numbers and method are in
   [Marginal versus joint distributions](#marginal-versus-joint-distributions).

## Source verification table

| Source | Status | Key required | Free | Format | Commercial use |
|---|---|---|---|---|---|
| Census data API (ACS 1-yr / 5-yr) | VERIFIED that a key is now required | Yes | Yes | JSON arrays | Yes, public domain |
| Census API metadata endpoints | VERIFIED | No | Yes | JSON | Yes, CC0 |
| Census PUMS bulk microdata | VERIFIED | No | Yes | CSV in ZIP | Yes, CC0 |
| World Bank Indicators API | VERIFIED | No | Yes | JSON / XML | Yes, CC BY 4.0 |
| Eurostat dissemination API | VERIFIED | No | Yes | JSON-stat 2.0 | Yes, with carve-outs |
| UN World Population Prospects bulk CSV | VERIFIED | No | Yes | Gzipped CSV | Licence not confirmed |
| UN Data Portal API (`/data/`) | PARTIAL — HTTP 401 | Yes | Unclear | JSON | Licence not confirmed |
| IPUMS USA / International API | PARTIAL — HTTP 401 | Yes | Yes to register | JSON / fixed-width | Restricted, see below |
| Pew Research Center datasets | UNVERIFIED for download | Account likely | Yes | SPSS / CSV | Conditional, see below |

## United States Census Bureau

### Data API key requirement

**VERIFIED.** A standard ACS 1-year query without a key does not return data:

```text
$ curl -sS -o /dev/null -w "code=%{http_code} redirect=%{redirect_url}\n" \
  "https://api.census.gov/data/2023/acs/acs1?get=NAME,B01001_001E&for=state:06"
code=302 redirect=https://api.census.gov/data/missing_key.html
```

Following the redirect yields an HTML page titled `Missing Key`. The same
302-to-`missing_key.html` behaviour was reproduced on `acs/acs1` and
`acs/acs5` and for both state and national geographies. Supplying a
deliberately invalid key returns an HTML page titled `Invalid Key`, which
confirms the parameter is genuinely being authenticated rather than ignored.

Two consequences matter for planning. First, any ingestion that uses the
data API needs a key provisioned as configuration, and keys are free from
`https://api.census.gov/data/key_signup.html` (**VERIFIED**, HTTP 200).
Second, because failure arrives as an HTTP 302 to an HTML page rather than a
4xx JSON error, a naive client that only checks for non-2xx status will parse
HTML as data. Any client must treat a redirect to `missing_key.html` as a
hard failure.

### Rate limits

**UNVERIFIED, and the commonly cited figure appears to be folklore.** The
current terms of service page contains no numeric quota. It has only a
"Right to Limit" clause stating that use "may be subject to certain
limitations on access, calls, or use" and that access may be blocked if
limits are exceeded. No 500-per-day threshold appears anywhere in that
document. Treat the true limit as unpublished, and design ingestion to be a
small number of bulk calls rather than per-persona live calls.

### Metadata endpoints work without a key

**VERIFIED.** The catalogue and variable dictionaries are open:

```text
$ curl -sS "https://api.census.gov/data.json" | ...
total datasets: 1791
{ "title": "Jan 1990 Current Population Survey: Basic Monthly",
  "accessLevel": "public",
  "license": "https://creativecommons.org/publicdomain/zero/1.0/" }
```

The catalogue advertises 1,791 datasets, each carrying an explicit CC0
public-domain licence. The variable dictionary for the 2023 ACS 5-year
detail tables returned 28,299 variables, and these specific identifiers were
confirmed to exist with these exact labels:

| Variable | Label | Concept |
|---|---|---|
| `B01001_001E` | Estimate!!Total: | Sex by Age |
| `B19013_001E` | Median household income in the past 12 months | Median Household Income |
| `B15003_022E` | Estimate!!Total:!!Bachelor's degree | Educational Attainment |
| `B01002_001E` | Estimate!!Median age --!!Total: | Median Age by Sex |
| `C24010_001E` | Estimate!!Total: | Sex by Occupation |

Note that `https://api.census.gov/data/2023/acs/acs5/variables/B19013_001.json`
returned HTTP 404; the working form is the whole-dictionary
`.../acs5/variables.json`.

### Aggregate tables versus microdata

ACS detail tables are **aggregates**. `B19013_001E` is a single median income
number for a geography. `B01001` is a count of people per age-and-sex cell.
These are marginal or lightly cross-tabulated summaries. They can tell you
what fraction of a county holds a bachelor's degree and what the county's
median income is, but they cannot tell you the income distribution *of the
degree holders* beyond whatever specific cross-tabulations the Bureau chose
to publish. That limitation is the entire reason microdata matters, developed
below.

### PUMS microdata over the API and in bulk

**VERIFIED.** PUMS is exposed both as API datasets and as bulk files. The
catalogue lists eight PUMS datasets for vintages 2022 and 2023
(`acs/acs1/pums`, `acs/acs5/pums`, plus Puerto Rico variants), each labelled
CC0. The PUMS variable dictionary for 2023 5-year returned 521 variables,
and the person-level attributes needed for persona grounding all exist:

| Variable | Meaning |
|---|---|
| `AGEP` | Age |
| `SEX` | Sex |
| `SCHL` | Educational attainment |
| `OCCP` | Occupation recode, 2018 OCC codes |
| `PINCP` | Total person's income |
| `WAGP` | Wages or salary income, past 12 months |
| `ESR` | Employment status recode |
| `COW` | Class of worker |
| `WKHP` | Usual hours worked per week |
| `MAR` | Marital status |
| `RAC1P` | Recoded detailed race code |
| `HISP` | Recoded detailed Hispanic origin |
| `STATE` | State code |
| `PUMA` | Public use microdata area code, 2020 definition |
| `PWGTP` | Person weight |
| `ADJINC` | Income adjustment factor, six implied decimals |

A naming trap worth recording: the geography variable is `STATE`, not `ST`.
A query for `ST` returns nothing. `REGION` and `DIVISION` also exist.

Bulk download needs no key. **VERIFIED** by actually retrieving and parsing
a state file:

```text
$ curl -sS -L -o wy.zip \
  "https://www2.census.gov/programs-surveys/acs/data/pums/2023/1-Year/csv_pwy.zip"
$ unzip -q wy.zip && ls -l
  264187 ACS2023_PUMS_README.pdf
 4231555 psam_p56.csv
```

Parsing that file gave 6,024 person records across 287 columns. Summing
`PWGTP` produced a weighted population estimate of **584,057**, which is
consistent with Wyoming's actual resident population. This is a useful
end-to-end sanity check: it confirms the weights are correct and that
weighted sampling reproduces real population totals.

Measured file sizes, from HTTP `Content-Length` headers:

| File | Size |
|---|---|
| `2023/1-Year/csv_pwy.zip` (Wyoming persons) | 1.29 MB |
| `2023/1-Year/csv_pvt.zip` (Vermont persons) | 1.42 MB |
| `2023/1-Year/csv_pny.zip` (New York persons) | 36.6 MB |
| `2023/1-Year/csv_ptx.zip` (Texas persons) | 53.4 MB |
| `2023/1-Year/csv_pca.zip` (California persons) | 69.8 MB |
| `2023/1-Year/csv_pus.zip` (national persons) | 597 MB |
| `2023/1-Year/csv_hus.zip` (national households) | 250 MB |
| `2023/5-Year/csv_pus.zip` (national persons) | 2.25 GB |

### Coverage, cadence and terms

Geographic coverage runs from nation down to block group for aggregate
tables. PUMS geography is coarser by design: state and PUMA only, where a
PUMA holds roughly 100,000 people. PUMS deliberately cannot resolve to a
city or ZIP code, which is a disclosure-avoidance feature.

Temporal coverage in the catalogue reaches back to 1990 for CPS and covers
ACS from 2005 onward. Cadence is annual: 1-year estimates release in
September for the prior year, 5-year estimates in December. The 5-year files
carry a `Last-Modified` of 2024-09-10 for the 2023 vintage.

Licensing is the strongest of any source reviewed. Census output is US
federal government work, and the API catalogue explicitly tags datasets
CC0 public domain. Commercial use is permitted. The terms of service impose
three obligations that are directly relevant:

- Display the notice: "This product uses the Census Bureau Data API but is
  not endorsed or certified by the Census Bureau." This applies to API use.
- Do not imply Census endorsement of the product.
- Under 13 U.S.C. sections 8 and 9, do not use the data, alone or combined
  with other data, to identify any individual person or household.

That third clause interacts directly with persona generation and is treated
in [Privacy and ethics boundary](#privacy-and-ethics-boundary).

## IPUMS

**PARTIAL.** The API is reachable and rejects unauthenticated calls cleanly:

```text
$ curl -sS -L "https://api.ipums.org/metadata/usa/sample?collection=usa&version=2"
{
    "error": "Authorization field missing"
}
```

Both `/metadata/` and `/extracts/` returned HTTP 401. This confirms the
service is live and that an API key issued from a registered account is
required. No data was retrieved, so all statements about IPUMS content
below are UNVERIFIED.

IPUMS harmonises variables across time and across countries, which is real
engineering value: raw Census occupation and education codes change between
vintages, and IPUMS supplies consistent recodes. For a project that only
needs recent single-vintage US data, that value is modest.

The licensing position is the decisive factor, and it differs sharply by
collection:

| Aspect | IPUMS USA | IPUMS International |
|---|---|---|
| Commercial use | Not prohibited in the published terms | "Commercial use is strictly prohibited" |
| Redistribution | "You will not redistribute the data without permission" | "You will not redistribute the data", no permission route offered |
| Licensing model | Per-user agreement, renewed annually | Each team member must license individually |
| Extra limits | Full Count adds "These data will not be republished" and bars genealogical use | Re-identification barred; extracts must be secured or destroyed |

Two practical conclusions. First, IPUMS International is unusable for this
product; the commercial prohibition is explicit. Second, IPUMS USA is
usable only for internal analysis unless written redistribution permission
is obtained, because shipping a database built from IPUMS extracts inside a
commercial product is redistribution. IPUMS states it will "consider
requests for free and commercial redistribution", so the route exists, but
it is a negotiation with an unknown outcome and an annual renewal attached.

Because Census PUMS supplies the same underlying US microdata under CC0
with no redistribution restriction, taking on IPUMS terms to obtain US data
is an avoidable risk. Recommendation: **do not depend on IPUMS.** Revisit
only if cross-national harmonised microdata becomes a requirement, and then
only for IPUMS International with commercial licensing resolved first, which
its published terms suggest is not available.

## World Bank Open Data

**VERIFIED** with a real response:

```text
$ curl -sS -L "https://api.worldbank.org/v2/country/USA/indicator/SP.POP.TOTL?format=json&date=2022:2023"
[{"page":1,"pages":1,"per_page":50,"total":2,"sourceid":"2","lastupdated":"2026-07-13"},
 [{"indicator":{"id":"SP.POP.TOTL","value":"Population, total"},
   "country":{"id":"US","value":"United States"},"countryiso3code":"USA",
   "date":"2023","value":336755052,"unit":"","obs_status":"","decimal":0},
  {"indicator":{"id":"SP.POP.TOTL","value":"Population, total"},
   "country":{"id":"US","value":"United States"},"countryiso3code":"USA",
   "date":"2022","value":333996304,"unit":"","obs_status":"","decimal":0}]]
```

No key, no registration, HTTP 200. The envelope carries
`"lastupdated":"2026-07-13"`, so the mirror is current. A query for all
countries at `per_page=20000` returned `total: 265` in a single page,
confirming generous pagination and that the whole country list fits in one
request.

Dimensions are the limiting factor. This is a **country-year indicator
service**, not a demographic cross-tabulation service. It gives national
aggregates such as total population, age-band shares, and income
classifications. It has no joint distribution of age against income against
education, and no sub-national geography beyond aggregates. It is suitable
for country-level context and for sanity-checking national totals. It is
not suitable for generating individual persona attributes.

Licence is CC BY 4.0 by default, which permits commercial use with
attribution and an indication of any changes made. Caveat recorded from the
licence page: many datasets in the wider catalogue carry other licences
including ODbL and a Microdata Research Licence, so the specific dataset
label governs rather than the site default. No rate limits are documented
on the licence page; none were encountered.

## Eurostat

**VERIFIED** with a real response. Population of Germany aged exactly 25,
on 1 January 2023:

```text
$ curl -sS -L "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_pjan?format=JSON&geo=DE&sex=T&age=Y25&time=2023"
{"version":"2.0","class":"dataset",
 "label":"Population on 1 January by age and sex","source":"ESTAT",
 "updated":"2026-07-09T11:00:00+0200",
 "value":{"0":974583},"status":{"0":"b"},
 "id":["freq","unit","age","sex","geo","time"],"size":[1,1,1,1,1,1],
 "dimension":{...,"age":{"label":"Age class","category":{"index":{"Y25":0},
  "label":{"Y25":"25 years"}}},...}}
```

No key, HTTP 200, and a real figure of 974,583. Format is JSON-stat 2.0,
which is a sparse structure: `value` is an index-keyed map and the
`dimension` block plus `size` array define how to decode indices into
coordinates. A client must implement that decoding; it is not a flat row
format.

Coverage is EU member states plus EFTA and candidate countries, with NUTS
regional breakdowns for many datasets, and annual cadence. Dimensions
available across the catalogue include age, sex, education attainment,
income deciles and occupation, though generally as separate aggregate
datasets rather than as one joint microdata table.

Licensing permits commercial reuse: statistical data reuse "for commercial
or non-commercial purposes is authorised provided the source is
acknowledged", under Commission Decision 2011/833/EU, with no written
licence required. Three carve-outs must be respected before commercial
reuse, and each requires filtering rows out rather than a blanket
compliance step:

- Data attributed to non-Eurostat sources.
- Data for countries outside the EU, EFTA and official candidate countries.
  Rows for the United States, Japan and China are explicitly named as
  non-commercial-only.
- Certain trade data declared by Switzerland, Liechtenstein and Austria.

Logos and trademarks are excluded from the general permission, and modified
data must be flagged as modified with a Eurostat non-responsibility
disclaimer.

## United Nations World Population Prospects

The API and the bulk files behave differently, and this distinction is the
main finding here.

**PARTIAL for the Data Portal API.** Metadata is open but data is not. The
indicator list returned HTTP 200 with 86 indicators, including exactly what
would be wanted:

```text
$ curl -sS -L "https://population.un.org/dataportalapi/api/v1/indicators"
{"pageNumber":1,"pageSize":100,"pages":1,"total":86,"data":[...]}
  46 | Population by 5-year age groups and sex | dimAge=True dimSex=True
  47 | Population by 1-year age groups and sex | dimAge=True dimSex=True
  49 | Total population by sex               | dimAge=False dimSex=True
```

The `/locations` endpoint likewise returned 300 locations with ISO codes.
But the actual data path returned HTTP 401 with an empty body:

```text
$ curl -sS -L -w "[code=%{http_code} size=%{size_download}]" \
  ".../api/v1/data/indicators/49/locations/840/start/2024/end/2024"
[code=401 size=0]
```

So the Data Portal API now requires a token for data retrieval. Any
documentation describing it as fully open is out of date.

**VERIFIED for bulk CSV.** The bulk file downloads without authentication
and contains real data:

```text
$ curl -sS -L -o wpp.csv.gz ".../WPP2024_Population1JanuaryBySingleAgeSex_Medium_1950-2023.csv.gz"
$ ls -l wpp.csv.gz
62107912 wpp.csv.gz
HEADER: SortOrder,LocID,Notes,ISO3_code,ISO2_code,SDMX_code,LocTypeID,
        LocTypeName,ParentID,Location,VarID,Variant,Time,MidPeriod,
        AgeGrp,AgeGrpStart,AgeGrpSpan,PopMale,PopFemale,PopTotal
ROW: ,5507,,,,,,,,ADB region: Central and West Asia,2,Medium,1950,1950,0,0,1,1222.011,1190.3,2412.311
```

That is 59 MB gzipped, single year of age, by sex, by location, 1950 to
2023, from the 2024 revision. Population figures are in thousands.

Dimensions are age, sex, location and year only. There is no income, no
education, no occupation. WPP is a demographic structure source, not a
socio-economic one. Its correct role is providing age and sex distributions
for countries where no microdata is available.

Cadence is roughly biennial by revision; the current files are WPP2024.

**Licence: UNVERIFIED, and this is an open item.** Several candidate pages
returned errors rather than terms: `population.un.org/wpp/citations`,
`/citation`, `/terms-of-use` and `/publications` all returned HTTP 404, and
`un.org/en/about-us/terms-of-use` and `/copyright` returned HTTP 403. A
scan of the WPP landing page HTML found no Creative Commons or IGO licence
string, and the page body is JavaScript-rendered so a plain fetch returns
only the title. UN data is commonly published under CC BY 3.0 IGO, but that
was **not confirmed** here and must not be recorded as verified. Resolve
the licence in writing before any commercial dependency on WPP.

## Pew Research Center

**UNVERIFIED for data access.** The dataset landing page returned HTTP 200,
but no dataset was downloaded and no download path was exercised, so
nothing about file formats or contents is confirmed here.

The terms position is nonetheless clear enough to act on, and it is
restrictive in ways that matter:

- The general terms explicitly exclude the American Trends Panel, which is
  "governed by their own terms and conditions" that are not published on
  that page. The ATP is the flagship dataset, so its actual terms remain
  unknown.
- For other datasets, reproduction and distribution are "limited to excerpts
  and may not be reproduced, displayed, distributed, broadcast, transmitted,
  or published in full." A product that ships a full Pew dataset would
  breach this.
- The licence granted for Data is "nonexclusive, non-sublicensable,
  non-transferable, revocable" and, unlike the Content licence, omits
  sell, license and transfer from the enumerated rights.
- Prohibited conduct includes "unauthorized spidering, 'scraping,' or
  harvesting", so automated ingestion is not permitted.
- Users must not "attempt to ascertain the identity of or derive information
  about individual survey respondents", nor link records to other datasets
  to identify people.
- Use must not attribute a policy or lobbying objective to Pew, or imply
  Pew endorsement of any product.

Pew's value is attitudinal rather than demographic: it measures opinion,
which is precisely what this product's personas are meant to explore. That
makes it attractive as a **validation benchmark** and hazardous as a
generation input. Recommendation: do not ingest Pew microdata into the
product. Use published Pew reports as an external reference for comparing
simulated opinion distributions against real ones, cited per Pew's format,
with the required non-responsibility disclaimer. Resolve ATP terms directly
with Pew before anything more than that.

## Marginal versus joint distributions

### The failure mode

A marginal distribution describes one variable in isolation: the age
distribution of a population, or its income distribution. A joint
distribution describes variables together: the probability of being 22 *and*
earning 180,000 *and* holding a doctorate.

Sampling each attribute independently from its own marginal reproduces every
individual histogram correctly while destroying every relationship between
them. The population looks right in aggregate and every individual in it is
potentially absurd: a 22-year-old with a thirty-year career, a doctorate
holder earning a paper-route income, a retiree with a toddler's education
code. Personas are consumed one at a time by users, so per-individual
incoherence is exactly the visible failure, and aggregate correctness does
not compensate for it.

### Measured, not asserted

This was quantified against the real Wyoming 2023 PUMS file already
downloaded, weighting by `PWGTP` so both methods target the same true
population. The impossibility test uses `AGEP` under 21 combined with `SCHL`
of 21 or higher; `SCHL` 21 is confirmed from the official dictionary to mean
"Bachelor's degree", so those pairs imply a bachelor's degree before age 21.

```text
INDEPENDENT marginals: impossible age/education combos: 544/20000 = 2.72%
JOINT record sampling:  impossible age/education combos:   2/20000 = 0.01%
```

Correlation damage, same data, 20,000 draws:

```text
TRUE (joint) corr(education, income) = 0.210
TRUE (joint) corr(age, income)       = 0.124
MARGINAL     corr(education, income) = 0.008
MARGINAL     corr(age, income)       = 0.007
```

Independent marginal sampling erased the education/income relationship
almost entirely, reducing a correlation of 0.210 to 0.008. Two details are
worth stating precisely. The 2.72% figure counts only one narrow class of
impossibility; the true rate of *implausible* combinations across age,
education, occupation and income jointly is considerably higher, because
this test ignores occupation and income entirely. And the residual 0.01%
under joint sampling is not an artifact — those are real respondents,
genuine people who completed a bachelor's degree at 20. Preserving rare but
real combinations while excluding impossible ones is exactly the desired
behaviour, and it is a property no marginal method has.

### Options evaluated

**Microdata record sampling.** Draw a whole real PUMS person record with
probability proportional to `PWGTP`, then read attributes off that one
record. Every correlation, including ones nobody thought to model, is
preserved because the combination actually occurred in a surveyed human.
Cost is storage and the coarse geography ceiling of state or PUMA. It cannot
invent combinations absent from the sample, which is a limitation for very
small subgroups and a safety feature everywhere else.

**Iterative proportional fitting, also called raking.** Start from a seed
joint table and scale it iteratively until margins match known targets. This
is the standard tool for small-area estimation and is the right answer when
you must match published local margins that microdata cannot resolve, such
as attributes at census-tract level. It needs a seed joint distribution to
begin with, so it does not remove the need for microdata; it redistributes
it. It also suffers zero-cell propagation: combinations absent from the seed
stay absent regardless of margins.

**Copulas.** Model marginals separately and impose a dependence structure
between them. Well suited to continuous, roughly monotone relationships.
Poorly suited here: occupation is a categorical variable with several
hundred unordered levels, education is ordinal with structural age
constraints, and the real dependence includes hard logical impossibilities
rather than smooth correlation. Fitting a copula over `OCCP` is not
meaningful, and a Gaussian copula would happily generate the 22-year-old
professor because it encodes correlation, not constraint.

**Conditional-distribution chaining.** Sample age, then education given age,
then occupation given age and education, then income given all three. This
is principled and gives fine control, and it is how you would proceed if
only aggregate cross-tabulations were available. The cost is that each
conditional must be estimated and stored, the number of conditioning cells
grows multiplicatively, sparse cells need smoothing decisions, and every
modelling choice is a place to introduce bias. It is a substantial amount of
statistical machinery to approximate something the microdata already
contains exactly.

### Recommendation

**Use microdata record sampling from Census PUMS, weighted by `PWGTP`, as
the primary mechanism.** Reasons, in order of weight:

1. It is correct by construction. Coherence is inherited from real
   respondents rather than modelled, so it holds across all attributes
   simultaneously, including interactions never explicitly considered.
2. It was measured working here: weighted sampling reproduced Wyoming's
   population total at 584,057, and preserved a 0.210 education/income
   correlation that marginal sampling reduced to 0.008.
3. It is the simplest option to implement and to audit. A sampled persona
   can carry the identifier of its source record, making every generated
   demographic profile traceable to a real survey row — which fits this
   project's existing provenance posture.
4. It is free of licensing risk under CC0, unlike the IPUMS route to the
   same data.

Add IPF only if and when sub-PUMA geographic precision becomes a genuine
product requirement, using PUMS records as the seed and ACS tract-level
tables as the margins. Do not use copulas here. Keep conditional chaining
in reserve for countries where microdata is unavailable and only aggregate
tables exist; for those, expect materially lower persona coherence and say
so rather than hiding it.

One consequence to design for: attributes not present in PUMS, such as
personality or attitudes, must be generated conditional on the sampled
demographic record rather than independently, or the same incoherence
reappears one layer up.

## Storage approach

The repository already standardises on SQLAlchemy 2 with `psycopg` version 3
for PostgreSQL in production and SQLite locally, per `backend/pyproject.toml`
(`sqlalchemy>=2.0.0`, `alembic>=1.13.0`, `psycopg[binary]>=3.2.0`). Reference
demographic data should live in that same database rather than in a separate
store or in flat files read at request time. It is small, read-only,
relational, and needs to be queryable by geography.

### Measured volume

Sizing is derived from real measurement, not estimated from assumptions.
Reducing the 287-column Wyoming person file to the 16 columns identified
earlier, then loading it into SQLite with an index on `(STATE, PUMA, AGEP)`:

```text
WY records=6024  full 287-col CSV=4.23MB  trimmed 16-col CSV=0.323MB
SQLite (indexed): 6024 rows = 0.328 MB -> 54.4 bytes/row
```

54.4 bytes per row is **MEASURED**. Row counts for the national files are
**ESTIMATED** from the published sampling rates, since downloading the
597 MB national archive was out of scope:

| Subset | Approximate rows | Projected size |
|---|---|---|
| Single small state, 1-year | 6,024 (measured) | 0.33 MB |
| National 1-year, roughly a 1% sample | about 3.4 million | about 185 MB |
| National 5-year, roughly a 5% sample | about 15.7 million | about 854 MB |

### Recommendation

Load the **national 1-year PUMS person file, trimmed to the 16 needed
columns**, as the default US subset. At roughly 185 MB it is unremarkable
for PostgreSQL, and it remains workable in SQLite for local development.
The 5-year file triples the sample for rare subgroups at roughly 854 MB and
should be treated as an opt-in extension rather than the default.

Four design points follow from the measurements:

- **Do not commit the data to git.** Even the trimmed national extract is far
  too large, and it is reproducible from a stable public URL. Fetch and load
  it with a checked-in ingestion script under Alembic-managed schema, and
  record the source URL, vintage and retrieval date.
- **Keep a small state subset as the test fixture.** Wyoming at 0.33 MB is
  a realistic, fully self-consistent fixture that is committable and makes
  local tests and CI fast without mocking.
- **Store native integer codes, not decoded labels.** `SCHL`, `OCCP` and
  `RAC1P` are compact integers; hold the code-to-label dictionaries in small
  companion lookup tables fetched from the PUMS variables endpoint. This is
  where the measured 54.4 bytes per row comes from, and decoding to strings
  at load time would inflate it substantially.
- **Index for the sampling access pattern.** Weighted sampling within a
  geography needs `(STATE, PUMA)` at minimum. Storing a running cumulative
  weight per geography turns weighted selection into an indexed range lookup
  rather than a full scan, which matters at 3.4 million rows.

Record `ADJINC` alongside income and apply it when comparing across
vintages; income fields are nominal to their survey year, and the factor
carries six implied decimal places.

## Privacy and ethics boundary

Every source recommended here is either an aggregate statistic or already
anonymised public-use microdata. PUMS records are released by the Census
Bureau only after disclosure-avoidance treatment, which is why geography
stops at PUMA rather than address, and why extreme values are top-coded.
Ingesting them does not bring personal data into the system, so this work
does not create a new category of personal-data processing.

That boundary is real but narrow, and three obligations sit on top of it.

**Re-identification is prohibited, explicitly and in multiple places.**
Census terms invoke 13 U.S.C. sections 8 and 9: the data must not be used,
"alone or in combination with any other Census or non-Census data, to
identify any individual person" or household, and inadvertent discovery of
an identity must be reported. Pew and IPUMS International carry equivalent
clauses. Practically, this forbids joining PUMS records against any other
dataset in an attempt to narrow a record toward a real person, and it means
a sampled record must never be enriched with external data keyed on its
attribute combination.

**A record is a statistical unit, not a person, and must not be dressed as
one.** The most likely ethical failure here is not a data breach but a
presentation error: sampling a real PUMS row, attaching a generated name,
photograph, biography and quotation, and displaying the result in a way
that implies a specific real individual holds that opinion. The underlying
row describes a real respondent's demographics; the opinions layered on top
are model output and belong to nobody. Generated personas must be presented
as synthetic constructs throughout, never as identifiable individuals, and
never as human respondents. This aligns with the existing product
requirement to disclose zero human respondents and to mark machine origin.

**Grounding improves realism, not validity.** Sampling real demographics
makes personas demographically representative. It does not make their
opinions evidence about real opinions, and it must not be described as doing
so. If anything, better-grounded demographics increase the risk of
over-trust, because output that looks statistically respectable invites
being read as survey data. Any surfacing of this feature should strengthen
rather than soften the existing boundary that output is not a forecast and
not a survey of people.

Finally, attribution obligations are compliance work, not optional polish:
the Census non-endorsement notice for API use, CC BY attribution and
change-indication for World Bank, and source acknowledgement plus
modification flagging for Eurostat.

## Open items

These remain unresolved and are stated as open rather than assumed:

- UN WPP licence terms could not be retrieved; all candidate pages returned
  404 or 403. Confirm in writing before commercial dependency.
- Pew American Trends Panel terms are not published on the general terms
  page and must be obtained from Pew directly.
- Census API rate limits are not documented numerically. The absence of a
  published quota is not evidence of a generous one.
- Whether IPUMS would grant commercial redistribution permission for IPUMS
  USA is unknown, and is only worth asking if harmonised cross-vintage
  variables become a requirement.
- National PUMS row counts are extrapolated from sampling rates, not counted.
  Verify by loading the national file before finalising capacity plans.
