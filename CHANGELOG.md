# CHANGELOG

<!-- version list -->

## v2.4.8 (2026-05-02)

### Update

- Update dependency cryptography to v47 ([#93](https://github.com/bartekmp/MediCony/pull/93),
  [`d88e499`](https://github.com/bartekmp/MediCony/commit/d88e4997d5d658c42f7fc5f4c2a8f8cc6c343601))


## v2.4.7 (2026-05-02)

### Bug Fixes

- **deps**: Update dependency psycopg2-binary to v2.9.12
  ([#94](https://github.com/bartekmp/MediCony/pull/94),
  [`f40d609`](https://github.com/bartekmp/MediCony/commit/f40d609838e5cc3cc790ec6610720d3bd73a67a6))


## v2.4.6 (2026-04-25)

### Bug Fixes

- Replace naive flag polling 300 times per minute with a single wake event
  ([#91](https://github.com/bartekmp/MediCony/pull/91),
  [`91c77c3`](https://github.com/bartekmp/MediCony/commit/91c77c3c4bede97a1889e1228bb0cf1e75fa92a4))

### Improvement

- Format sources ([#91](https://github.com/bartekmp/MediCony/pull/91),
  [`91c77c3`](https://github.com/bartekmp/MediCony/commit/91c77c3c4bede97a1889e1228bb0cf1e75fa92a4))

- Merge MedicoverDbLogic+Client into single class, eliminate tuple pipeline
  ([#91](https://github.com/bartekmp/MediCony/pull/91),
  [`91c77c3`](https://github.com/bartekmp/MediCony/commit/91c77c3c4bede97a1889e1228bb0cf1e75fa92a4))


## v2.4.5 (2026-04-18)

### Bug Fixes

- **deps**: Update python dependencies ([#90](https://github.com/bartekmp/MediCony/pull/90),
  [`161c1ee`](https://github.com/bartekmp/MediCony/commit/161c1ee834bf5ee70408082517d1debbb305c8f2))


## v2.4.4 (2026-04-11)

### Bug Fixes

- **deps**: Update python dependencies ([#88](https://github.com/bartekmp/MediCony/pull/88),
  [`b3ae031`](https://github.com/bartekmp/MediCony/commit/b3ae031f5f556c6d426decc8c2b79871dbd101d1))


## v2.4.3 (2026-04-07)

### Improvement

- Replace N+1 appointment existence checks with a single bulk SELECT
  ([#86](https://github.com/bartekmp/MediCony/pull/86),
  [`af214a5`](https://github.com/bartekmp/MediCony/commit/af214a5370d4232ca943d241259878c82aaafecc))


## v2.4.2 (2026-04-05)

### Bug Fixes

- **deps**: Update dependency numpy to v2.4.4 ([#84](https://github.com/bartekmp/MediCony/pull/84),
  [`3158e1f`](https://github.com/bartekmp/MediCony/commit/3158e1f6b207f0e3709dba2d7a17bd9ea28d9675))


## v2.4.1 (2026-04-04)

### Bug Fixes

- **deps**: Update dependency pytest-env to v1.6.0
  ([#82](https://github.com/bartekmp/MediCony/pull/82),
  [`3b661cf`](https://github.com/bartekmp/MediCony/commit/3b661cf4be0982fef61fd74251d1c106fc2773cc))


## v2.4.0 (2026-04-04)

### Features

- **mfa**: Handle Medicover verification code limit and active cooldowns
  ([#83](https://github.com/bartekmp/MediCony/pull/83),
  [`a848888`](https://github.com/bartekmp/MediCony/commit/a848888e80411397cf0a5b758e7e45acefeba9d6))


## v2.3.1 (2026-04-04)

### Improvement

- Disable stdin MFA provider in non-interactive environments
  ([#81](https://github.com/bartekmp/MediCony/pull/81),
  [`4c90a04`](https://github.com/bartekmp/MediCony/commit/4c90a04910fde5849ce437af70fc70f6110a2ba4))


## v2.3.0 (2026-04-04)

### Feature

- Enhance MFA transparency, telemetry, and startup logging
  ([#80](https://github.com/bartekmp/MediCony/pull/80),
  [`51430bf`](https://github.com/bartekmp/MediCony/commit/51430bfa153d86349815f2e2563f56ca72237ca7))


## v2.2.3 (2026-04-04)

### Update

- Update dependency setuptools-scm to v10 ([#78](https://github.com/bartekmp/MediCony/pull/78),
  [`8f8f38d`](https://github.com/bartekmp/MediCony/commit/8f8f38dfd45461a82545fe85a7f7ccf0890c9f2e))


## v2.2.2 (2026-04-04)

### Bug Fixes

- **deps**: Update python dependencies ([#79](https://github.com/bartekmp/MediCony/pull/79),
  [`a618b7b`](https://github.com/bartekmp/MediCony/commit/a618b7b60102c8e32ed6b033f1e8f50d0f6706a4))


## v2.2.1 (2026-04-02)

### Improvement

- Remove MFA gate skip page support ([#77](https://github.com/bartekmp/MediCony/pull/77),
  [`758e1be`](https://github.com/bartekmp/MediCony/commit/758e1be97d318667f49cffd43cc76439cf35239d))


## v2.2.0 (2026-04-02)

### Features

- **auth**: Session persistence ([#76](https://github.com/bartekmp/MediCony/pull/76),
  [`b0e13a1`](https://github.com/bartekmp/MediCony/commit/b0e13a1037936dea6d52bd9ea54f58ba7e4bdba7))


## v2.1.1 (2026-03-31)

### Bug Fixes

- Race condition on mfa code accepting ([#75](https://github.com/bartekmp/MediCony/pull/75),
  [`3b97f60`](https://github.com/bartekmp/MediCony/commit/3b97f60df8a24f25040de83d25db8fcdb140e77b))


## v2.1.0 (2026-03-29)

### Features

- **auth**: Implement interactive MFA (2FA) verification flow
  ([#74](https://github.com/bartekmp/MediCony/pull/74),
  [`e6a7d3d`](https://github.com/bartekmp/MediCony/commit/e6a7d3d36fbd9e0fd0666206cc78f18d5c1f4093))


## v2.0.1 (2026-03-23)

### Bug Fixes

- Save appointment history entries in a single batch
  ([#72](https://github.com/bartekmp/MediCony/pull/72),
  [`0c7a47b`](https://github.com/bartekmp/MediCony/commit/0c7a47bdc529544a70072b6cd7f0065e96742488))


## v2.0.0 (2026-03-23)

### Features

- Update docker/metadata-action action to v6 ([#71](https://github.com/bartekmp/MediCony/pull/71),
  [`2d0dd2f`](https://github.com/bartekmp/MediCony/commit/2d0dd2f3dcb97fc00fc3d2d3c47889a11093e7c6))


## v1.5.8 (2026-03-21)

### Bug Fixes

- **deps**: Update python dependencies ([#70](https://github.com/bartekmp/MediCony/pull/70),
  [`eb509e8`](https://github.com/bartekmp/MediCony/commit/eb509e81865522d1a1260674661cbca5f15e2d6e))


## v1.5.7 (2026-03-18)

### Enhancement

- Reorganize code, update feature test ([#69](https://github.com/bartekmp/MediCony/pull/69),
  [`52ac833`](https://github.com/bartekmp/MediCony/commit/52ac833efdcfc6c519da03dd2652a68e20424243))


## v1.5.6 (2026-03-17)

### Enhancement

- Renovate config ([#68](https://github.com/bartekmp/MediCony/pull/68),
  [`c6644dd`](https://github.com/bartekmp/MediCony/commit/c6644dd262583571ad1f5ec2e490df9be66de40d))


## v1.5.5 (2026-03-17)

### Bug Fixes

- The condition of medicine finding feature test
  ([#67](https://github.com/bartekmp/MediCony/pull/67),
  [`3203f62`](https://github.com/bartekmp/MediCony/commit/3203f62604664cd2a1995d9258e5cf4730a952a9))


## v1.5.4 (2026-03-14)

### Bug Fixes

- **deps**: Update dependency black to v26.3.0 ([#64](https://github.com/bartekmp/MediCony/pull/64),
  [`feceefd`](https://github.com/bartekmp/MediCony/commit/feceefd36686ef21c8ac7622cf2166cc08de42cb))


## v1.5.3 (2026-03-10)

### Bug Fixes

- **deps**: Update python dependencies ([#60](https://github.com/bartekmp/MediCony/pull/60),
  [`7f1e3f7`](https://github.com/bartekmp/MediCony/commit/7f1e3f73a5a36467c33320c75a48a409c16a603e))


## v1.5.2 (2026-03-10)

### Bug Fixes

- Remove explicit click dependency
  ([`ab61a1e`](https://github.com/bartekmp/MediCony/commit/ab61a1ec5c989f8fc1801073e6005e0e21265a19))


## v1.5.1 (2026-03-06)

### Improvement

- Move container image building and publishing to GHA
  ([#59](https://github.com/bartekmp/MediCony/pull/59),
  [`be2a36a`](https://github.com/bartekmp/MediCony/commit/be2a36a51021fc3cb86b36e08ef729bd257a4843))


## v1.5.0 (2026-03-05)

### Feature

- Update to new login flow and handle Medicover MFA gate
  ([#58](https://github.com/bartekmp/MediCony/pull/58),
  [`53028ca`](https://github.com/bartekmp/MediCony/commit/53028ca45c3f4227e53d724bd99e191476a6b462))


## v1.4.1 (2026-02-28)

### Bug Fixes

- **deps**: Update python dependencies ([#54](https://github.com/bartekmp/MediCony/pull/54),
  [`23de525`](https://github.com/bartekmp/MediCony/commit/23de5251e30b547ee3a66d0c38c014ce0d038d57))


## v1.4.0 (2026-01-02)

### Feature

- Update deployment example
  ([`7624531`](https://github.com/bartekmp/MediCony/commit/76245319431a8c0dcbf444c2a13e472058e69cbc))


## v1.3.1 (2026-01-02)

### Bug Fixes

- Update python package dependencies ([#42](https://github.com/bartekmp/MediCony/pull/42),
  [`f8e872b`](https://github.com/bartekmp/MediCony/commit/f8e872b1dc7cc9a12eecdc68d9715e791f176949))


## v1.2.8 (2025-12-22)

### Bug Fixes

- Downgrade click dependency ([#40](https://github.com/bartekmp/MediCony/pull/40),
  [`d721312`](https://github.com/bartekmp/MediCony/commit/d7213127823d08bdc77f0b1f35cca9c25eda1db3))


## v1.2.7 (2025-12-19)

### Bug Fixes

- Formatting in renovate.json
  ([`2267fbb`](https://github.com/bartekmp/MediCony/commit/2267fbba3f55c3e28bd7c40c6df6e54bf804dd5f))


## v1.2.6 (2025-12-19)

### Enhancement

- Update renovate.json configuration settings
  ([`480533f`](https://github.com/bartekmp/MediCony/commit/480533f89b2fe40d786ef5ef8902245c038ef18d))


## v1.2.5 (2025-11-25)

### Bugfix

- Python package dependencies ([#35](https://github.com/bartekmp/MediCony/pull/35),
  [`aae7ccc`](https://github.com/bartekmp/MediCony/commit/aae7ccc04b6dc18d74837964c4fb98644e4bcc22))


## v1.2.4 (2025-10-18)

### Bug Fixes

- Move wake event past the log message ([#31](https://github.com/bartekmp/MediCony/pull/31),
  [`1530239`](https://github.com/bartekmp/MediCony/commit/1530239fce2a64a1e4bd6d14ef2d74df19689ab8))


## v1.2.3 (2025-10-13)

### Bug Fixes

- Wrong loop evaluation
  ([`7533c79`](https://github.com/bartekmp/MediCony/commit/7533c791f8beb2ae081f2a0d4b9496461bae54f5))


## v1.1.8 (2025-08-29)

### Bug Fixes

- Reformat code
  ([`20fd59d`](https://github.com/bartekmp/MediCony/commit/20fd59d826e79a7fbbcbb1945743caa8b71dc25e))


## v1.1.7 (2025-08-29)

### Bug Fixes

- Remove debug docker push properties
  ([`323a5a4`](https://github.com/bartekmp/MediCony/commit/323a5a427a30f1a6f65a9907b27a175202deb29a))


## v1.0.0 (2025-08-28)

- Initial Release

## v1.3.0 (2025-08-26)

### Bug Fixes

- Do not allow alias duplicates ([#39](https://github.com/bartekmp/MediCony/pull/39),
  [`d86338f`](https://github.com/bartekmp/MediCony/commit/d86338ff2e330915aafae5e279a62597d524b88c))

- Failing auth feature tests ([#39](https://github.com/bartekmp/MediCony/pull/39),
  [`d86338f`](https://github.com/bartekmp/MediCony/commit/d86338ff2e330915aafae5e279a62597d524b88c))

### Enhancement

- Default account printing in watch add bot command
  ([#39](https://github.com/bartekmp/MediCony/pull/39),
  [`d86338f`](https://github.com/bartekmp/MediCony/commit/d86338ff2e330915aafae5e279a62597d524b88c))

### Feature

- Add multiple user accounts support for medicover component
  ([#39](https://github.com/bartekmp/MediCony/pull/39),
  [`d86338f`](https://github.com/bartekmp/MediCony/commit/d86338ff2e330915aafae5e279a62597d524b88c))

- Multi user support ([#39](https://github.com/bartekmp/MediCony/pull/39),
  [`d86338f`](https://github.com/bartekmp/MediCony/commit/d86338ff2e330915aafae5e279a62597d524b88c))


## v1.2.2 (2025-08-23)

### Bug Fixes

- Wrong gitops folder path
  ([`0887694`](https://github.com/bartekmp/MediCony/commit/0887694636ca4dff25c4a7dc233c3e24d4ffe9fb))


## v1.2.1 (2025-08-23)

### Bug Fixes

- Docker image tagging order
  ([`0209f61`](https://github.com/bartekmp/MediCony/commit/0209f61f4a24652903c246475ed5fe159591eaa0))


## v1.2.0 (2025-08-23)

### Bug Fixes

- Medicine search timeouts ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Remove unused database file ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Use right pharmaradar link ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Wrong checks for adding medicines ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

### Enhancement

- Extract pharma db client class ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Remove db file config option, adapt bot commands, improve message formats
  ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Split medicine and medicover database interfaces
  ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

### Feature

- Migrate to pharmaradar and postgresql ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Migrate to postgresql, fix pharmaradar inconsistencies
  ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))

- Remove medicine classes, use pharmaradar package instead
  ([#38](https://github.com/bartekmp/MediCony/pull/38),
  [`9a7435b`](https://github.com/bartekmp/MediCony/commit/9a7435b9a72b6e7217e2373c5a85072b9d5ba85b))


## v1.1.6 (2025-07-22)

### Bug Fixes

- Use proper python binary
  ([`7fcc299`](https://github.com/bartekmp/MediCony/commit/7fcc299ce26823617bf0c7827cdfd7d7cfdd9980))


## v1.1.5 (2025-07-17)

### Bug Fixes

- Add_watch name mismatch
  ([`0dcc01a`](https://github.com/bartekmp/MediCony/commit/0dcc01ac85fbd1dc81c7e10ca80b2140d544b6df))


## v1.1.4 (2025-07-17)

### Bug Fixes

- Use proper param-env order in jenkinsfile
  ([`4864898`](https://github.com/bartekmp/MediCony/commit/48648989514cb51d8541e69d9b07f3e9a35ca275))


## v1.1.3 (2025-07-17)

### Bug Fixes

- Default argocd deployment variable assignment
  ([`5378879`](https://github.com/bartekmp/MediCony/commit/5378879a2e5dde54ef9fc9f7f19d73245d96d6f9))


## v1.1.2 (2025-07-17)

### Bug Fixes

- Argocd deployment variable in jenkinsfile
  ([`9f2aab1`](https://github.com/bartekmp/MediCony/commit/9f2aab18da14196fad8026057c36236b170efec2))


## v1.1.1 (2025-07-17)

### Bug Fixes

- Gitops repo URL from global variable
  ([`2a455a0`](https://github.com/bartekmp/MediCony/commit/2a455a0401ef429e987ff0444cce02e14f8b0858))


## v1.1.0 (2025-07-16)

### Feature

- Add argocd pushing, remove dead code, refactor db code
  ([#37](https://github.com/bartekmp/MediCony/pull/37),
  [`f9dd14a`](https://github.com/bartekmp/MediCony/commit/f9dd14ad2bd148722aa54d7208fd01edbb003c30))


## v1.0.0 (2025-07-16)

- Initial Release
