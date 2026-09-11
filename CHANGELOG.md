# Changelog

## [0.4.0](https://github.com/homestead-affairs/homestead-law/compare/v0.3.0...v0.4.0) (2026-09-11)


### Added

* a Chapter 13 pack that drafts nothing, with the plan-period flag ([98c2dd5](https://github.com/homestead-affairs/homestead-law/commit/98c2dd5243f2a533233062913baf44391114ea76))
* a workers' compensation pack that keeps dates and references, never the medicine ([81a6a17](https://github.com/homestead-affairs/homestead-law/commit/81a6a17306fad8b85c82b0461065614b76861083))
* add the workers' comp pack (wave 3, decision 7) ([fcff5f4](https://github.com/homestead-affairs/homestead-law/commit/fcff5f438b5de175b5ff9ec603d3eb277a60a09b))
* compute a deadline from a pack template through the gate, and accept it by token ([d13dbad](https://github.com/homestead-affairs/homestead-law/commit/d13dbad9673d8c6fa740e19b91592a0b75f42b67))
* custody relocation fields, repeatable children, and deadline templates ([3c3320b](https://github.com/homestead-affairs/homestead-law/commit/3c3320b9e36351429bd42ea5227150ce04e6f4a8))
* deadline templates — compute and accept, never guess (L3-deadline-templates) ([03d66be](https://github.com/homestead-affairs/homestead-law/commit/03d66bec2e9bc6850680fa29560df0649085d230))
* the bankruptcy pack, a plan-period interaction flag, and I-44's AST guard ([4d11cfd](https://github.com/homestead-affairs/homestead-law/commit/4d11cfdf15c0acdd0d2b077297817bfc56f09f3f))
* the custody pack carries the relocation, registration, and children a move needs ([bf2fa21](https://github.com/homestead-affairs/homestead-law/commit/bf2fa21253a8594050e8a3ac2e8902f4343481cc))


### Fixed

* an L1 district_state on the bankruptcy pack, so a forward count reads the district's calendar ([82c40b8](https://github.com/homestead-affairs/homestead-law/commit/82c40b833002cf6cc1109abcd1e66556fd5ce1bc))
* describe the banned phrases instead of quoting them in the README ([2ede392](https://github.com/homestead-affairs/homestead-law/commit/2ede39260df3f868db25dd3254e62e5911c58c43))
* one template contract with no exception, and a repeatable field that needs its sub ([5995973](https://github.com/homestead-affairs/homestead-law/commit/59959734902f732d3615184c5cbe59d7ac8fb4ba))
* only say "district holidays not applied" where one could have been ([b5c2299](https://github.com/homestead-affairs/homestead-law/commit/b5c2299b455ccfae55d37062a5d213f058d5524b))
* pick a template by the instance's forum, and name the calendars a count used ([115f692](https://github.com/homestead-affairs/homestead-law/commit/115f6922b0d41387b59ed49b39dd8b6de3d96c65))
* refuse a broken template at the door instead of raising through it ([938faf9](https://github.com/homestead-affairs/homestead-law/commit/938faf99b3c2d9a2d12e6574962bf9e1db066c1e))
* rung the harm, not the template, and split ime the way custody splits child ([139df17](https://github.com/homestead-affairs/homestead-law/commit/139df175a0ec02969cb229f5e92a3e5195bad91c))
* the templates the sibling bite can read, and a flag that fails closed ([1d29902](https://github.com/homestead-affairs/homestead-law/commit/1d299028925724cb6be4276fb48569492eb6bae5))

## [0.3.0](https://github.com/homestead-affairs/homestead-law/compare/v0.2.0...v0.3.0) (2026-09-11)


### Added

* matter instances and per-instance jurisdiction (L2b-instances) ([f81da7b](https://github.com/homestead-affairs/homestead-law/commit/f81da7b3aaf592ca7b733c882d827e8f022da4b0))


### Fixed

* refuse an option `deadline` does not take instead of storing it ([231bfb7](https://github.com/homestead-affairs/homestead-law/commit/231bfb73c70f7a19e5d9a7f1b74f6f927ab3f6e6))
* address every deadline to an instance, and re-check a jurisdiction on read ([ff2df4e](https://github.com/homestead-affairs/homestead-law/commit/ff2df4ebd94901a9e45a33a3ddcb0ec7f870004d))

## [0.2.0](https://github.com/homestead-affairs/homestead-law/compare/v0.1.1...v0.2.0) (2026-09-11)


### Added

* jurisdiction and derived forms on the custody pack (decisions 1, 3) ([945a44a](https://github.com/homestead-affairs/homestead-law/commit/945a44a0c1aeb4702e46bd66b26cc8c230f88913))
* let a household enter and read its own records without the entity extra ([86817fa](https://github.com/homestead-affairs/homestead-law/commit/86817fa5026ce16621cbcb51df68e60a01c3701d))


### Fixed

* rest the cover on the matters a household has, not the packs it ships ([4741d7e](https://github.com/homestead-affairs/homestead-law/commit/4741d7e0452b712bdcf74e185023d001a0694dd7))
* require a derived form at import and scan the registry for tables too ([72cbb56](https://github.com/homestead-affairs/homestead-law/commit/72cbb56a9c4f9774b2c4787aa7df1bb13694c72d))
* drain a refused request body before the socket closes ([add4f68](https://github.com/homestead-affairs/homestead-law/commit/add4f6856696b358fd0a642657cd1c41871afbc1))
* draw one cover button and one queue pane per registered matter ([ed8df14](https://github.com/homestead-affairs/homestead-law/commit/ed8df143887db63c188777a956b03a62badd11cc))
* refuse a missing matter, parse the CLI's dates, and smoke every module ([ec23c0b](https://github.com/homestead-affairs/homestead-law/commit/ec23c0b64d69819d26c6e1f785fba9b151b70a1c))

## [0.1.1](https://github.com/homestead-affairs/homestead-law/compare/v0.1.0...v0.1.1) (2026-08-24)


### Build

* **deps:** bump actions/setup-python from 5 to 7 ([2d7bb9d](https://github.com/homestead-affairs/homestead-law/commit/2d7bb9d9550e9955ab4edcd658f7265b8da9dde0))
* **deps:** bump actions/checkout from 4 to 7 ([e92aa17](https://github.com/homestead-affairs/homestead-law/commit/e92aa17c8694e2ad22b28d496a302eea3829f55b))
* **deps:** bump actions/upload-artifact from 4 to 7 ([0404a71](https://github.com/homestead-affairs/homestead-law/commit/0404a717fd70e4d5e811b3a5c073b2e684b219ff))
* **deps:** bump actions/download-artifact from 4 to 8 ([e878668](https://github.com/homestead-affairs/homestead-law/commit/e878668f617d41652eda39c7bd825b3c16770f1b))

## [0.1.0](https://github.com/rudi193-cmd/homestead-law/compare/v0.0.1...v0.1.0) (2026-08-11)


### Added

* draw from the engine's shared theme; pin homestead-affairs&gt;=0.1.0,&lt;1.0 ([cc3892d](https://github.com/rudi193-cmd/homestead-law/commit/cc3892d678d92b63389955d22926af1d583c36f1))


### Fixed

* handle --help and headless failure in the entry point ([99cce45](https://github.com/rudi193-cmd/homestead-law/commit/99cce4569786968d59461eb5f4911d53d073c420))
* handle --help and headless failure in the entry point ([6bbcfd6](https://github.com/rudi193-cmd/homestead-law/commit/6bbcfd66e66010203ee705ab6fe297579807ba1e))


### Build

* add homestead-law's PyPI release chain (release-please + Trusted Publishing) ([f865328](https://github.com/rudi193-cmd/homestead-law/commit/f865328f2ba8374f8d37a2f2de6540aca428ccfb))
* consume the engine from PyPI (homestead-affairs) ([9b213fc](https://github.com/rudi193-cmd/homestead-law/commit/9b213fcbc194b603a46c644c33bd05dd8faef197))
* consume the engine from PyPI (homestead-affairs) ([35d269a](https://github.com/rudi193-cmd/homestead-law/commit/35d269aa28f993d8e5f314e5adbe2775307ee2cd))
* relicense to Apache-2.0 ([2c76792](https://github.com/rudi193-cmd/homestead-law/commit/2c76792271b214f10fd5362f6f35a29dcfdc2093))
* relicense to Apache-2.0 ([9e05384](https://github.com/rudi193-cmd/homestead-law/commit/9e05384eb41b7ffcde409385e69003e1c20d81ce))

## Changelog

All notable changes to `homestead-law` are documented here. The format is
based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is maintained by
[release-please](https://github.com/googleapis/release-please), which builds each
entry from the [Conventional Commits](https://www.conventionalcommits.org/)
prefixes on `main` — see `release-please-config.json` for which types cut a
release. The version is derived from the git tag (pyproject `dynamic =
["version"]` + hatch-vcs); there is no version literal in the source to drift.

**Generated entries are sometimes corrected by hand, and this is why.** This repo
merges with merge commits rather than squashing, and GitHub writes the PR title
into the merge commit body — which release-please parses *alongside* the commit
it merges, so one change can produce two identical entries.
`tools/changelog_dedup.py` rebuilds the newest section from the non-merge
commits so the duplicate never ships; see the engine's (`homestead-affairs`)
0.0.2 entry for the failure this closes.
