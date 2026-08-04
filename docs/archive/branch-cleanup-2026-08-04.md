# Remote branch cleanup — 2026-08-04

162 branches deleted from `origin`. Restore any one of them with:

```
git push origin <sha>:refs/heads/<branch-name>
```

Nothing unique was lost: every branch below either has zero commits that main
does not already have, or proposes one of two changes main already carries.

`report_evidence._section_query_seed` — main dedupes case-insensitively and
preserves order. The branches dedupe case-sensitively, or only after the
tokens are already truncated.

`simulation_runtime_contract.select_active_agent_ids` — main filters on
platform for every agent. The branches exempt boosted agents from the check.
That is a behaviour difference, not a fix; main's is the stricter contract and
is what `test_simulation_runtime_contract.py` asserts.

## Kept

`main`, the 12 `dependabot/*` branches (live dependency PRs, not duplicates),
and the six branches whose tests were salvaged into
`backend/tests/services/`:

- add-tests-report-agent-parse-9398923858815919300
- add-zep-tools-tests-11233596832177081533
- test-report-agent-plan-outline-5579421567871858887
- jules-testing-improvement-10403991681838583302
- jules-3201533664384281774-1d315cd8
- test-insight-forge-14873489418137811525

## Deleted

| SHA | Branch | Subject |
| --- | --- | --- |
| `3c932375b8a5f4b66a7c3d4cfd8b8671df42b162` | bolt-date-optimization-13810168647311473674 | Optimize date sorting in OpinionMap.vue |
| `e92e12563622ef51826a6fcd1854bad8ec96d24b` | bolt-date-optimization-3423529420899193573 | ⚡ Bolt: Replace Date object instantiation in sort callback with string comparison |
| `7cff72d96fc6bcfd7b6a9fef433c95ed739eda95` | bolt-fast-date-sort-15185072450749793624 | perf: optimize date sorting in OpinionMap by avoiding Date parsing |
| `26a55456bca811961754ee718df98749f69df98b` | bolt-history-vmemo-optimization-3777646487055317441 | ⚡ Bolt: Add v-memo to reduce v-for re-renders in HistoryDatabase |
| `9f38bc79aa5d488ac1bc83e23b41eb13eef4d38a` | bolt-opinion-map-date-sort-1338547440002293950 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `75fccb3b8a91245ed06ad20c6ad72b41a61ad685` | bolt-opinion-map-date-sort-14319733922301630153 | ⚡ Bolt: Optimize Date sorting in OpinionMap.vue by replacing Date instantiation with direct ISO 8601 string comparison |
| `d27c4df56e4db15dde4620d175b5711e2df5994e` | bolt-opinion-map-sort-16034112574653730879 | perf: optimize timestamp sorting in OpinionMap.vue to avoid Date GC overhead |
| `00e3f2d63a24ade3cb9478f4823374edaea0a912` | bolt-opinion-map-sort-gc-fix-6107294804269560724 | ⚡ Bolt: Optimize date sorting in OpinionMap to reduce GC overhead |
| `232be0c1128d094625946c5b4da713ebb04de715` | bolt-opinion-map-sort-optimization-8826807601426459075 | ⚡ Bolt: Optimize OpinionMap sorting by removing Date object instantiation |
| `034f99530bc5b76ea319387b52ab1f8c5c9d7c7b` | bolt-opinionmap-perf-11171660609371141382 | ⚡ Bolt: O(N) map pass & string comparison for OpinionMap |
| `f75229e47e6bb63d8d33bf7a6e3b880d9e7f06ca` | bolt-opinionmap-sort-opt-1625892411576059939 | ⚡ Bolt: Avoid Date instantiation in OpinionMap sorting |
| `9732e399565289f3bb539eae888823f260bcd8e0` | bolt-opinionmap-sort-opt-8180476194804343414 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue |
| `e364b24e9fcc099cc0fff8cc9287f99367fb1fc7` | bolt-optimization-iso-8601-3702263830657254982 | ⚡ Bolt: Direct ISO 8601 string comparison in OpinionMap sorting |
| `3f63815635f308cfecf99d2a7049cac1724443d1` | bolt-optimize-date-comparison-1157647950295159904 | ⚡ Bolt: Optimize date comparisons in OpinionMap |
| `b38812020234ae2bd104bb5e526d855f3f5f052c` | bolt-optimize-date-comparison-17690674098936243152 | ⚡ Bolt: optimize date comparison in OpinionMap |
| `abc2a3496c77b495b8793bf9cb1d3aa25c76eb7d` | bolt-optimize-date-comparison-2379912757878428052 | ⚡ Bolt: Optimize date comparison and mapping in OpinionMap |
| `6c870b349b58a0b796d98bc0f45efc51e097fcbf` | bolt-optimize-date-sort-8677771129478433684 | perf(frontend): optimize date comparison in OpinionMap sort |
| `3905fcbf5f4f4ae08c3d5d62c4a132768ccacec8` | bolt-optimize-date-sort-896519442342196759 | ⚡ Bolt: Optimize date comparison in OpinionMap sorting |
| `ac8b85e350581449a66fafaea482a3a56e5b10f1` | bolt-optimize-date-sorting-12328662499093811691 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue |
| `e4c6119b3e2b9d96f213dd1b48879e3f87918c31` | bolt-optimize-date-sorting-12863133172314933216 | perf: optimize Date sorting to reduce GC overhead in OpinionMap |
| `1e8ab2f4327149a5a244abe6328cbf314d768a6d` | bolt-optimize-date-sorting-14187349990030147358 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `88c82c74a7ca3f6f963100710c5c2a1702d8c68a` | bolt-optimize-date-sorting-1538508096510324976 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `0e73095c3cd1436a120be2156ff52f19e995743f` | bolt-optimize-date-sorting-18226247682380977702 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue |
| `11ede7d135600e5d289af188c469733acc21495c` | bolt-optimize-date-sorting-2390609388426572219 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `50f45f3c2754b0a0b11b8dbe4d4dc1d1c7112ea6` | bolt-optimize-date-sorting-2507778102358484454 | ⚡ Bolt: optimize date sorting in OpinionMap.vue by avoiding Date object instantiation |
| `f26f06d9db4389b8dd6fe80bdba13a1b2fd40497` | bolt-optimize-date-sorting-2955257181393957454 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `0855902397cfdf63e3347b006d9f8fc202d5cd02` | bolt-optimize-date-sorting-3797690945582593590 | ⚡ Bolt: Optimize date sorting in OpinionMap |
| `abd126c4ff01b78b17ac2db958150bc0cccc140b` | bolt-optimize-date-sorting-5782158160697251886 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue |
| `fefb1940cde9d6ad09386804ad3166c76ea57a5d` | bolt-optimize-date-sorting-5903399396885918049 | ⚡ Bolt: Optimize Date sorting in OpinionMap.vue |
| `9d16ff4c0f06d021a9f4b05740f77c90fbe71e53` | bolt-optimize-date-sorting-7257193292023278777 | ⚡ Bolt: Optimize Date instantiation in Vue sort callbacks |
| `93cdb65b234b851271544452aa807c0beecec15d` | bolt-optimize-history-vmemo-1069657564397186837 | perf(frontend): Add v-memo to HistoryDatabase simulation cards |
| `996dc9be278689b8a79ab1ef9abc31559156b036` | bolt-optimize-opinion-map-sort-5445992399918135647 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap.vue by replacing Date instantiation with string comparison |
| `55f2e74dc7f8972b8aebfbe66dbe7a4fca0c2d8d` | bolt-optimize-opinionmap-sort-10571355061469776134 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap.vue |
| `d6258fbf1ee2317403065b22c43053a5a18ef2d5` | bolt-optimize-opinionmap-sort-14118884104436941367 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap |
| `d743a4e91540a9f8e523581d1d3352d1e288f5da` | bolt-optimize-opinionmap-sort-17478685936385304538 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap |
| `729f1897b9c1d8334c364f61d8220ffc7658f4eb` | bolt-optimize-opinionmap-sort-5058465623195319268 | perf: optimize date sorting in OpinionMap.vue |
| `6313ada71655fa32d2a687a70329bc58d4b609ba` | bolt-optimize-timestamp-sort-13341164425128171797 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap.vue |
| `8fc4bde557642439ad26f6e59bf3377ab5a7ca4c` | bolt-optimize-timestamp-sort-16544159797034967896 | ⚡ Bolt: Optimize OpinionMap sort performance |
| `936f092a121eb6c021b054e0419e40262761160a` | bolt-optimize-timestamp-sort-5326428001131531288 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap.vue |
| `91f48801bba7f9e234a2d60bc2045f407b35bf2e` | bolt-optimize-zepp-api-cache-2252072826265846459 | perf(backend): cache get_all_nodes and get_all_edges in ZepToolsService |
| `978fcf427ad129d86646f67634a6e24f28bdba6a` | bolt-perf-history-db-vmemo-15098666615214053716 | ⚡ Bolt: Add v-memo optimization to HistoryDatabase list rendering |
| `624fc66739424e24212fdf9333af2b2a6be14d80` | bolt-perf-opinion-map-date-sort-15438854200573857113 | ⚡ Bolt: Optimize date sorting by avoiding object allocation |
| `3fcc14fc4736ec16e1e65f57ed6db98ccafbd7d3` | bolt-perf-opinion-map-on-15464789906098015880 | ⚡ Bolt: Optimize OpinionMap computed property to O(n) |
| `cf86f513962a894bbc60b5360a9693ce3cf905aa` | bolt-performance-cache-zeptools-7144305380555314637 | feat: add class-level cache for ZepToolsService get_all_nodes and get_all_edges |
| `4ffc882cbfd5851501d3ae550fa2a3cf6ed53dec` | bolt-performance-date-sort-6198523377952123245 | ⚡ Bolt: Refactor Date parsing in OpinionMap array sort to string comparison |
| `9fc0195c2b225513a07a33ad039870a2d9b3025c` | bolt-performance-opinionmap-sort-12661009703406524115 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue by using string comparison |
| `bc73d1579417331e36ed10291d68493f8ea0592f` | bolt-performance-opinionmap-sort-5044669269214693110 | ⚡ Bolt: Refactor latestOpinions to O(N) string comparison |
| `3ded9140e9f139db47c2e0ab80889b3a9c2a7686` | bolt-v-memo-optimization-6068997155202016713 | Add v-memo to simulation cards in HistoryDatabase.vue |
| `63e94c00f978b9244f5ae076bf5b7bf59fe327b6` | bolt-zep-tools-cache-15064789336900301204 | feat: optimize ZepToolsService with class-level caching |
| `db3b2ee817f75c1346cc4c0790b6870b0db6f3be` | bolt/opinion-map-date-sort-optimization-5260616403151168618 | perf(frontend): avoid Date parsing in OpinionMap sort callback |
| `a780713a70fd60fae35ac52093bdbd3ccdd0c914` | bolt/opinion-map-perf-7033263145556035996 | Optimize latestOpinions computed property in OpinionMap.vue |
| `c7a5c06fad2d9a6d94bd84ae1aefde41dcbf7313` | bolt/optimize-date-comparison-9105617591512419579 | ⚡ Bolt: Optimize date comparison in OpinionMap sorting |
| `b45811350c6071b0cdccf55397f5d2fe4c2d7f05` | bolt/optimize-date-comparison-9211937296433002630 | ⚡ Bolt: Optimize date comparison in OpinionMap |
| `00251faba4b249909360b6d050b623c1811acbd6` | bolt/optimize-date-instantiation-13325528138175129620 | perf(frontend): avoid Date instantiation in sort callbacks for performance |
| `b61af7013fc79928e7d905a6395f7c428a281e4d` | bolt/optimize-date-parsing-opinionmap-8271085895045759729 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap |
| `39eb645681254a1b93dde72cda4e1392b9fe563c` | bolt/optimize-date-sorting-17937386313594187350 | perf(frontend): optimize date sorting with string comparison |
| `dd79c4085ed71c2304a29de2e575d0c94e06aac8` | bolt/optimize-date-sorting-2806464064026053107 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue by removing Date instantiation |
| `73cb4a876a1f8a3e71a61b15e072270bade52dd3` | bolt/optimize-date-sorting-9315636679438239097 | ⚡ Bolt: Optimize date sorting in OpinionMap.vue |
| `2486486f92abd3aa556754fa66dfc75e58f27440` | bolt/optimize-v-memo-11710129858273452538 | ⚡ Bolt: Optimize HistoryDatabase.vue list rendering with v-memo |
| `ea4e639c2ebef3c9cda14767956ef05e2ff26435` | bolt/optimize-vmemo-history-1923008918448840173 | ⚡ Bolt: Use v-memo in HistoryDatabase for performance |
| `ffe7bfb82b2ab7f2cd3b2927ea07184b9e1d77d4` | bolt/v-memo-history-database-3071623628142683598 | perf: use v-memo in HistoryDatabase.vue to prevent unnecessary re-renders |
| `1deb7e68087bc8cf940addfc8f2eb0077b9b9e44` | bolt/v-memo-optimization-16361454731468713206 | ⚡ Bolt: Optimize simulation cards rendering in HistoryDatabase |
| `77fd51897c478d85cb465c51b63c6dafee39e9e0` | bugfix/simulation-runtime-evidence-generation-28433091921348944 | fix: resolve failing backend tests in evidence generation and agent selection |
| `10f86d7c2524fb5b48bf50b6c403a6a215b2fa06` | daily-apex-fixes-9962452443348319918 | Fix evidence deduplication order and active agent platform filtering |
| `9d5bb3d5f5540724120114fdadbf31a1415ca0cb` | daily-upgrade-backend-logic-fix-17866935179245820094 | fix: Resolve backend test failures in runtime contract and report evidence |
| `bb04da57ef3be7c5d2e7c83296c30f84cc415bb7` | daily-upgrade-runtime-fixes-10221957101766666512 | Fix backend simulation runtime bugs and test failures |
| `e749deff7a70c691cde4baa4de832724196545d0` | daily-upgrade-simulation-contract-15387849603629486802 | fix: strictly enforce platform matching for active agent selection |
| `6791f023c3a98e1873e5ff97e5e1925a113ab26f` | docs/production-authority | docs(authority): comprehensive sweep - release notes, archive state, validator docstring |
| `f2a2bd3cce83e1717e479cf531404675453ad2a3` | feat-implement-env-setup-step-14658486295295997220 | feat: implement environment setup step and router navigation in Process.vue |
| `8c817120f85adff0666fd4aea9e3dc5420336c38` | feat/projects-history | style(HistoryDatabase): update modal layout and enhance user guidance |
| `1dff14e5102cae7b5cc1eedfab582fa9b655cc1b` | fix-agent-platform-compatibility-10921469818654321098 | fix: enforce platform compatibility and correct boosted agent probability in simulation runtime |
| `6d315b83715516f2559d75507ede4c1e33e31516` | fix-agent-platform-selection-17598757432039158932 | fix(backend): Fix agent platform selection and evidence deduplication bugs |
| `5909edc5ed691de051b07b63900547d9e2056aa2` | fix-agent-selection-platform-14441494529113041278 | fix: respect platform preference in agent selection |
| `3c200c8e7c6e4dde0c786b31190de5e087efa307` | fix-agent-selection-platform-strictness-9970694322589989706 | fix(backend): strictly enforce platform matches and correctly bypass checks for boosted agents in simulation runtime |
| `98a7c865255ac1a5d4426d80e59349610ebf8b9e` | fix-backend-logic-bugs-2395129271305744881 | Fix agent filtering logic and deduplicate token seeds |
| `2d6fab1059eef065e0d2bd2c2c2b8b2e072221cc` | fix-backend-simulation-bugs-15808068369004400939 | fix: correct agent selection logic and seed deduplication in report generation |
| `d3cbbdf0b4546c0b3369ba50a0ffd6aed32b096c` | fix-backend-simulation-logic-10574291556543029309 | fix: resolve test failures in backend simulation logic |
| `6237a54b31eaf0873a0b846e9dcb4019cb48943d` | fix-backend-test-failures-11865005559333880872 | fix: resolve backend test failures in runtime contract and report evidence |
| `ba08cb5110482292d9bae57441c92a090cf55eea` | fix-backend-tests-logic-8926024821550982331 | Fix backend logic causing test failures in evidence builder and runtime simulator. |
| `9264e451c6b1964a93fa7ab3ac1490c5daed8ef7` | fix-platform-compatibility-agent-selection-7197755093320313933 | Fix platform compatibility logic in agent selection |
| `2b20afd86fa17d4eddf10c24c88113f90f99cdbb` | fix-platform-preference-enforcement-16028644017336534625 | fix: strictly enforce platform preference in agent selection |
| `d6a55d43f27f7846766121e24a74c19689cc5869` | fix-platform-preference-filtering-11211296381206558197 | fix: ensure select_active_agent_ids strictly respects platform compatibility |
| `f4a802cea2c5798f779256f97589df30706f2cae` | fix-report-evidence-dedup-16565524078442737223 | fix: deduplicate seeds in report evidence generation |
| `1790017346201a6c5374aee4368888265c95288e` | fix-report-evidence-dedup-5369419708398135300 | fix(backend): preserve seed order during token deduplication in evidence querying |
| `cb3dd451e1d7bb8bad2fb4788c2ab23760d7a8b0` | fix-simulation-and-evidence-bugs-755622245343283725 | fix: Resolve bugs in evidence query token generation and agent platform filtering |
| `503b595971ce59bbe125ab03f28bd8b8098d94cb` | fix-simulation-logic-13190693787019628843 | fix: backend agent selection and report evidence generation |
| `4af95e236bacad926222647d5adcb1691912fc2f` | fix-simulation-logic-bugs-329701064340905665 | Fix simulation logic and evidence parsing bugs |
| `b32b5af91765d4c70bd98fd821cc0becf5a848e4` | fix-simulation-platform-compatibility-15532535145257122432 | fix(backend): strictly enforce platform compatibility for agents |
| `fda7aca217bb5d2c7ad8851eb117cb3d9772350b` | fix-simulation-runtime-agent-selection-6940985622901845119 | 🧹 [code health] Enforce strict platform matching for agent selection |
| `2993750d3bbb76cec4525856ee5eedf3b1b57d18` | fix-simulation-runtime-and-evidence-9225732593176989507 | 🧹 [Fix core simulation tests and bugs] |
| `f7560cf748b7e2262fbdf6da2e32410f11571b42` | fix-unused-import-interviewresult-5923122871291515849 | 🧹 [code health] Remove unused import InterviewResult from report_agent.py |
| `ea267e806d4712c65d297f2da40565f305614355` | fix-unused-imports-1876986191960001500 | 🧹 [Code Health] Remove unused imports from zep_graph_memory_updater.py |
| `d4a7dfa0c9f2295922e33e2fc91a7afd501d3e53` | fix/active-agents-platform-preference-896402299715993028 | fix(simulation): enforce platform matching for active agent selection |
| `52d4f0c6da7156d6e2a33926adc3b50182934244` | fix/agent-selection-platform-compatibility-1425791132906820054 | fix(simulation): enforce strict platform compatibility in agent selection\n\nThe method `select_active_agent_ids` in `ba |
| `d3f94913bfa4d2c088d7a3e0ed813b6d5260250c` | fix/backend-simulation-test-reliability-10360455415337886684 | fix: Resolve flaky unit tests and robust evidence query matching |
| `777c0bf8ab84c61aac0b3a053ace932d2800add3` | fix/backend-tests-order-and-platform-preference-7571745241916609687 | fix: resolve backend test failures in evidence deduplication and agent platform selection |
| `19e5d7284f4c64cbc3a5da5712401ce384cba03a` | fix/n1-query-follow-5125059472237542553 | ⚡ Fix N+1 query issue in _enrich_action_context for FOLLOW actions |
| `e7bcb105dece829cdc8e2b35cf4c847e467fdcce` | fix/platform-match-logic-8204682399400193984 | fix: strictly enforce platform compatibility and fix boosted logic scaling |
| `b490005ac5c0934bc0040f946c9b3e8180f30492` | fix/remove-ontology-generator-import-7253786861362928872 | 🧹 Remove unused OntologyGenerator import from services/__init__.py |
| `1b5d88a669f156d1266e13e5544407b16177a9e2` | fix/remove-unused-import-insightforgeresult-12162644069653274088 | refactor: remove unused InsightForgeResult import to improve code health |
| `444729afdf0c6f40b0a03c318f1bc4846934383f` | fix/remove-unused-time-import-3558072976962277189 | 🧹 Remove unused `import time` from report_agent.py |
| `e077429bb763821f13189455dc4b1a31d869e2f2` | fix/report-evidence-deduplication-11147394950361364329 | fix: Deduplicate tokens and seeds in report evidence query to fix SQLite limits and `test_observation_and_evidence.py` f |
| `61ee41e7ab4ece21b89c7f95ad999f4a84b9b5ef` | fix/simulation-agent-platform-selection-17007573480830290024 | fix: strict platform matching for active agent selection |
| `73bb7cf394244d082e62d989e47e0807799276dd` | fix/simulation-runtime-agent-boost-534045003193839008 | fix(simulation): allow event-boosted agents to bypass platform preference checks |
| `07957124df7f4b074a3cfd5d00e77791f19cafb2` | fix/simulation-runtime-agent-boost-logic-4959714137830174963 | fix(simulation): enforce platform preference while preserving agent boosts |
| `ee515ef2f97ff5b3d466874c4d3ec68e01c9a401` | fix/simulation-runtime-agent-platform-enforcement-15318788286874303971 | Fix platform preference filtering in select_active_agent_ids |
| `87c8ca1bb913bb1acd43c516ced8040666990115` | fix/simulation-runtime-bugs-17222648459242752576 | fix: fix evidence builder seeds and agent platform preference selection\n\n* Deduplicated seeds in `report_evidence.py`  |
| `422ef0da85854032d05f6a39b06a18534b9cbb49` | fix/simulation-tests-18311628965109868288 | fix: fix simulation logic and tests |
| `7794b54ff96c0002986eba99011f7be3de246535` | jules-10271537204046322583-71d9af85 | fix: enforce strict platform preference in agent selection and deduplicate seed tokens in report generation |
| `9fe5db26a123cc3f5cef5f0dd216872a906f2457` | jules-10987865866148784173-2c0c675f | Fix active agent platform selection and query seed duplication |
| `3969a8ebe2ac613389ccad8f32c693136ba0ade1` | jules-1142262645525539155-4aaee161 | 🧹 [logic fix] fix agent selection platform filtering and seed token deduplication |
| `cd3848f38e52c46f4585d4fd4185d8ee6225c0ea` | jules-13747335394195073683-39f7bc79 | fix(backend): deduplicate search tokens while preserving order in report_evidence |
| `17e322082f1e363a7e4f65c8ab062d77cb321797` | jules-14250898176251584573-d5fdd016 | 🧹 Code Health: Remove unused import os |
| `43f21c6a29eb87c6b195952e3b03d0acb7ff3748` | jules-14613109971439491570-c824d0fd | 🧹 Improve code health in Process.vue by implementing env setup creation |
| `b94833a8906945ec772127f3ba9cf7561687062f` | jules-14725963147262080823-1fee248a | Optimize N+1 query in fetch_new_actions_from_db |
| `ecceca8f6cf551b8fdd4b3712bd9b29c43b75ce0` | jules-14931419438775933364-79049618 | 🧹 Remove unused `shutil` import in simulation_manager.py |
| `afb7ae1c772b6b093513d26f24f12843614afe30` | jules-15033550607390993507-c73af1be | ⚡ Bolt: Add thread-safe caching to ZepToolsService for graph queries |
| `f54fb845e10754cfa318dada302ac4dd3b01fcac` | jules-15246150041928963180-e6ad4f72 | fix(simulation): ensure active agents respect platform preference when boosted |
| `de240a8533271a8728becfc4fac44fa7fc900411` | jules-15384756959869366069-15c30efe | 🧹 Remove unused Config import in simulation_manager.py |
| `c77d27f37d869d2cc9fc31a446b809f40a91a4e4` | jules-15509312998480527259-7f4411f4 | fix(backend): resolve broken tests in simulation runtime and report evidence |
| `e59f222b152ebefb65c7c92e980f946a60d8cd5c` | jules-15824550828700112299-3335c484 | fix(simulation): Enforce strict platform matching in agent selection |
| `6990f1637b9842f072c757b1c0c5072324266b45` | jules-16976193912937202649-94e64e1d | 🧹 Remove unused 'os' import in zep_graph_memory_updater.py |
| `d4cc1e63e10871441e41b3442092de8dfae7557d` | jules-18052263501324210720-397add65 | 🔒 Security fix: Restrict CORS origins |
| `a76c6d4abf4a4b10bfcfb520a56a7e56c07bd270` | jules-18347766741864830508-182fbfd2 | 🧹 [code health] remove unused import OasisAgentProfile |
| `3b58b20d16a707d63f81907a1b00cc5d0d283de5` | jules-3468873738170029850-db1c32eb | fix(simulation): enforce platform compatibility for agents and deduplicate seeds |
| `ef7a7d34371321542d506ffc7557ee0082ecca3f` | jules-4235752464619263540-342dfa96 | 🧹 Remove unused GraphBuilderService import in services module |
| `c562d1f6551b62a8ad46d83701473351f412e9f2` | jules-4353212735481578082-baf62d28 | 🧹 Remove unused import FilteredEntities from simulation_manager.py |
| `78419320e1d97efd80e9c6d1d5ad05f246cb4de5` | jules-4369425287078433532-836df61f | 🧹 [Code Health] Remove unused ZepEntityReader import and format simulation_config_generator |
| `6d2804404c046b4b5524f2bebba1148fb363a037` | jules-4694269374642057597-018dd241 | fix: deduplicate seeds in report evidence builder to prevent limiting SQLite queries prematurely |
| `09f4f5dce1dc79002f912db5023bbb14a9e7e58e` | jules-7009280652093390520-8b95bd88 | 🧹 [code health] remove unused json import from zep_graph_memory_updater.py |
| `3bae91ab4924815c0411e782e27b9e400fb4cff3` | jules-7960179773978765939-f912dceb | fix(backend): deduplicate generated evidence report seeds |
| `40417e39549c817a564d70de72a5de43df98eac9` | jules-8577312225111153814-47021726 | 🧹 [Code Health] Remove unused imports and fix linting issues in report_agent.py |
| `742f68951a71a521c41a855bfc64ce63a0e309c9` | jules-8781701989699296105-bae95753 | ⚡ Bolt: Optimize timestamp sorting in OpinionMap.vue computed property |
| `34b3e4a56c3bae5cad0d7986983a630330800268` | jules-959520126889258080-7a1d4362 | Fix frontend build warning and backend test failures |
| `83001dfb85ed89e4acb8bfc34c1326b3131f770b` | jules-bolt-perf-12158533929262627951 | ⚡ Bolt: Avoid Date() object allocation in timestamp sorting loops |
| `6c8386c24aa2e8d10f19768b57a017eaf6f7f50f` | jules-bolt-perf-v-memo-history-2371006672129866022 | ⚡ Bolt: Optimize simulation list rendering in HistoryDatabase.vue with v-memo |
| `cf0f6361bb7383249c51c80342e00f45698197ea` | jules-bolt-vmemo-optimization-8220712435819597742 | ⚡ Bolt: Add v-memo to reduce re-renders in HistoryDatabase |
| `611e99f358d7fd66c1cabcdd745ccaedf9dd3940` | jules-bolt-vue-date-sorting-3157638407406179292 | ⚡ Bolt: Optimize date string sorting in OpinionMap.vue |
| `f6275c33ebae6fe46d16109f18a89fb4d70a5e12` | jules-code-health-simulation-manager-2546986653085267199 | 🧹 [code health improvement] Remove unused import SimulationParameters |
| `90fa4ffd3bb69e4048806fde58f50ebddddd2626` | jules-daily-upgrade-improvements-2603910961027686190 | fix: apply strict platform filtering and performance optimizations |
| `07cdecd5134e4b73aa223c3e6a987a5de565b88c` | jules-daily-upgrade-platform-validation-14750438152542471421 | feat: Add strict whitelist validation to platform parameters in simulation API endpoints to prevent path traversal vulne |
| `f440405aa1caf6b91260de66926686391ffb7409` | jules-daily-upgrade-report-evidence-4622254555204340738 | fix(backend): deduplicate seed tokens in report evidence generation |
| `cff78fa946428a4fb219a12a9a2c88fc5f49352f` | jules-daily-upgrade-simulation-boost-17823613667276790686 | fix(simulation): preserve boost agent priority regardless of platform constraints |
| `dbc81573c4e9868296d30bb165fc98616d67d5c5` | jules-fix-agent-platform-selection-5687496569875280908 | Fix agent platform preference enforcement in simulation runtime |
| `3b0e60162aecb0ddc4242ab1f40911a20c7364e4` | jules-fix-platform-compatibility-5274853446901233860 | fix(backend): enforce strict platform compatibility check for agents |
| `e51311cd41c5eb9780a8b93def2ea33bd24df93a` | jules-fix-platform-match-for-active-agents-7378008889007129923 | fix(simulation): enforce strict platform compatibility for active agents |
| `f42238734ac67e31bb372acfe24b38b909207758` | jules-fix-seed-platform-agent-10405720469756411825 | fix(simulation): Deduplicate query seeds and strictly enforce platform preference for agents |
| `0f2f2beba3cc809f46b2629af486891b88d757e9` | jules-fix-unused-import-report-agent-2744936107181816143 | 🧹 Remove unused SearchResult import from report_agent.py |
| `545acbb282115a0015c0416a13dfb55b82cd580c` | jules-frontend-optimizations-9662240265738657628 | ⚡ Refactor frontend imports and optimize OpinionMap dates |
| `b5ccd27eb8ae98977557580e767db6206f350334` | jules-perf-opinionmap-6481909051987972010 | ⚡ Bolt: Optimize OpinionMap latestOpinions to O(N) map update |
| `fbdf80c4b424339e1f583d9d18aeffae37b7b55b` | jules-performance-bolt-timestamp-sort-9702731418870635757 | ⚡ Bolt: Refactor timestamp sorting to use fast string comparison |
| `c1bca0223b53472b172674ce4cab03580f1a46be` | jules-remove-unused-import-2148033483543651247 | 🧹 [code health] Remove unused TextProcessor import |
| `239e1ae38f01199cf0ba73c9c31985f6430e615a` | jules-security-fix-secret-key-9398923858815919114 | 🔒 fix: use secure fallback for SECRET_KEY |
| `21560f4c0324fca8de970b0f882310d1ea22449b` | jules/fix-agent-selection-18188471699668572015 | fix: ensure boosted agents bypass platform preference properly |
| `07139c05142a0c8169dcec87e22c91cbf192d7ec` | master | feat: Add WebSocket support for simulation and report updates |
| `8a33fe287fe46604b6ad0c6e5852d309906d4bc3` | optimize-get-user-name-n1-query-14003140127742446182 | ⚡ Optimize _get_user_name N+1 issue with user_name_cache |
| `19275f2b03a3fc8c54b681f413d7c8e18588a0ff` | optimize-opinion-map-date-sort-16477568003478771012 | feat(frontend): optimize date sorting in OpinionMap.vue |
| `bfce134c227c5d7693706e0650167cabdaf8b0a8` | perf-zep-tools-cache-2640060994509208477 | perf: add class-level caching for ZepToolsService node and edge retrieval |
| `536f4d83b6689c888f8f70a1b75d29e0f48e81ae` | performance/zep-tools-caching-2012228052872865957 | perf: add thread-safe cross-request caching to ZepToolsService |
| `df638c3cbe410ab6dcc12c5a0e4bcc228ae2d775` | test-simulation-manager-error-handling-1821987149357393771 | Add error handling tests for prepare_simulation in SimulationManager |
| `5226bb55c626fbcaaf252f1fa6364531f5438229` | test-zep-tools-fallback-17476684726937230036 | 🧪 Add edge case testing for _generate_sub_queries fallback |
| `3053412e09e2f543f2f9ccf0d8a3a5032729d3ce` | tests-prepare-simulation-208751634195744843 | 🧹 [testing improvement] Add unit tests for prepare_simulation in SimulationManager |

## Pushed during the cleanup

The bot integrations are still running: these two were created while the
deletion was in progress and are obsolete in the same two ways.

| SHA | Branch | Subject |
| --- | --- | --- |
| `684a8dcee91949c5e751181dc025d9926819933d` | bolt-fix-date-sort-gc-overhead-360377683865982205 | ⚡ Bolt: Optimize date sorting to prevent GC overhead in OpinionMap |
| `86fdd601662bbaa21f327268f70129c83378f4b0` | fix-simulation-runtime-agent-selection-7801603094212047095 | fix: correct platform matching logic for boosted agents |

`OpinionMap.vue` already sorts with `localeCompare` over the raw timestamp
strings and instantiates no `Date`, so the first proposes work that is done.
The second is the boost-bypass behaviour change described above.

Deleting these does not stop more from arriving; that needs the Bolt and Jules
integrations turned off at the repository level.
