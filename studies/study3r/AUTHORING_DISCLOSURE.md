# Study 3R protocol-authoring disclosure

> **State:** `STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
>
> This state does not authorize freeze, task-bank realization or model
> execution. `formal_execution_authorized` remains `false`.

Machine-readable form: [`study3r_authoring_disclosure_v1.json`](study3r_authoring_disclosure_v1.json)

## 1. Starting and final state

| item | value |
| --- | --- |
| starting commit | `cd9c0af3118ca2f254bd0bbaa8eb2ee4dad6d1ed` |
| starting tree | `fc303a001bbfea60149e9f425f64230c022b6d91` |
| final commit | `a6ea96f80db38eddefcbbbc4e58c53f305e3c702` |
| final tree | `bc7fb7375d491c685c09d0e231110969a804f2bc` |
| merge commits | 0 |
| history rewrites | 0 |

## 2. Linear ancestry

| # | commit | tree | paths | subject |
| --- | --- | --- | --- | --- |
| 1 | `5a80c6730625` | `8cbc87ad8672` | 1 | Study 3R: publish the protocol-authoring authority alone |
| 2 | `c650e45c9a7a` | `27ad5141af3f` | 9 | Study 3R: seal the immutable revisions and the tokenizer-only acquisition |
| 3 | `8d59b06f675e` | `c2378787709a` | 20 | Study 3R: author the clean-room protocol candidate v1 |
| 4 | `a6ea96f80db3` | `bc7fb7375d49` | 10 | Study 3R: constrain every decision-bearing schema value |

The authority was published **alone** as the first commit after the starting state: 16972 byte(s), SHA-256 `bafd90a73261dc710b861a1f9bcf286804b3e902bc31b8342e39174b9bfe0200`, blob `6d5c2b2657185d3088e10f03fa7713881b2b9c57`.

## 3. Resolved immutable revisions

| role | repository | revision | tokenizer | vocab | context | `max_new_tokens` |
| --- | --- | --- | --- | --- | --- | --- |
| `RT` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B` | `ad9f0ae0864d7fbcd1cd905e3c6c5b069cc8b562` | `Qwen2Tokenizer` | 151643 | 131072 | 2 |
| `RP_B1` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B` | `916b56a44061fd5cd7d6a8fb632557ed4f724f60` | `Qwen2Tokenizer` | 151643 | 131072 | 2 |
| `RP_B2` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-14B` | `1df8507178afcc1bef68cd8c393f61a886323761` | `Qwen2Tokenizer` | 151643 | 131072 | 2 |
| `RP_B3` | `deepseek-ai/DeepSeek-R1-Distill-Qwen-32B` | `711ad2ea6aa40cfca18895e8aca02ab92df1a746` | `Qwen2Tokenizer` | 151643 | 131072 | 2 |

Allow-list: `config.json`, `generation_config.json`, `tokenizer_config.json`, `tokenizer.json`. `trust_remote_code = false`.

### Proof that no weight file was acquired

| check | value |
| --- | --- |
| `every_acquired_path_is_in_the_allow_list` | `True` |
| `no_acquired_path_has_a_weight_suffix` | `True` |
| `weight_bytes_acquired_total` | `0` |
| `weight_files_acquired_total` | `0` |
| `weight_paths_requested_total` | `0` |

### Tokenizer-only counters

| counter | value |
| --- | --- |
| `chat_template_renders` | 8 |
| `decode_calls` | 0 |
| `encode_calls` | 32 |
| `evidence_ledger_rows_written` | 0 |
| `execution_seeds_drawn` | 0 |
| `files_acquired` | 16 |
| `forward_passes` | 0 |
| `generations` | 0 |
| `gpu_or_cloud_jobs` | 0 |
| `interfaces_selected` | 0 |
| `logit_reads` | 0 |
| `model_constructions` | 0 |
| `network_file_downloads` | 16 |
| `network_metadata_requests` | 4 |
| `prefill_operations` | 0 |
| `remote_code_executions` | 0 |
| `scientific_items_realized` | 0 |
| `scoring_operations` | 0 |
| `tokenizer_constructions` | 4 |
| `weight_files_acquired` | 0 |

## 4. Estimands

* primary: `E0_zero_generated_reasoning_token_expressed_competence`
* diagnostic: `D0_single_forward_decodability` — D0_single_forward_decodability proves only conditional discriminant decodability at a frozen position under a frozen counterfactual surface. It never demonstrates natural expression, never demonstrates complete-answer competence, is never an RP-B gate and never qualifies a candidate.
* ceiling: `COT_generated_reasoning_ceiling`, `k = 1` — A generated-CoT ceiling pass proves only that the checkpoint has generated-CoT headroom on the registered ceiling bank. Neither a pass nor a failure selects an interface, selects a wrapper arm, or demonstrates no-CoT capability.

## 5. Census and statistics

`m_max = 58` gate-bearing atomic cells over 9 gates; 8108 scheduled item evaluations.

| gate | cells | direction | floor/margin | alternative | alpha/cell | power | n | boundary | exact size | exact power |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `G01_COT_CEILING` | 4 | greater_than_floor | `3/4` | `9/10` | `1/1160` | `9/10` | 128 | k >= 111 | 0.000856460763 | 0.912498598878 |
| `G02_CONTROL_RECOVERY` | 8 | greater_than_floor | `9/10` | `99/100` | `1/1160` | `9/10` | 110 | k >= 108 | 0.000807913105 | 0.901331394239 |
| `G03_CONTROL_BINDING` | 8 | greater_than_floor | `9/10` | `99/100` | `1/1160` | `9/10` | 110 | k >= 108 | 0.000807913105 | 0.901331394239 |
| `G04_CONTROL_PRIMITIVE` | 8 | greater_than_floor | `9/10` | `99/100` | `1/1160` | `9/10` | 110 | k >= 108 | 0.000807913105 | 0.901331394239 |
| `G05_NEGATIVE_CONTROL` | 8 | less_than_upper_margin | `35/100` | `1/4` | `1/1160` | `9/10` | 416 | k <= 115 | 0.000827387853 | 0.902527305436 |
| `G06_WRAPPER_JOINT_ADEQUACY` | 8 | greater_than_floor | `1/2` | `3/4` | `1/1160` | `9/10` | 74 | k >= 51 | 0.000758111832 | 0.907835037241 |
| `G07_RPB_DEVELOPMENT` | 6 | greater_than_floor | `1/2` | `3/4` | `1/1160` | `9/10` | 74 | k >= 51 | 0.000758111832 | 0.907835037241 |
| `G08_RPB_CONFIRMATION` | 6 | greater_than_floor | `1/2` | `3/4` | `1/1160` | `9/10` | 74 | k >= 51 | 0.000758111832 | 0.907835037241 |
| `G09_RT_E0_QUALIFICATION` | 2 | greater_than_floor | `1/2` | `3/4` | `1/1160` | `9/10` | 74 | k >= 51 | 0.000758111832 | 0.907835037241 |

Independent recalculation: 9/9 gates in exact agreement; `imports_production_calculators = false`; recomputed `m_max = 58`, recomputed `alpha_per_cell = 1/1160`.

## 6. Tokenizer equivalence and strata

Verified tuple: `bytes`, `token_ids`, `common_prefix`, `discriminant_position`, `answer_surface_token_ids`.

| role | stratum |
| --- | --- |
| `RP_B1` | `STRATUM_01` |
| `RP_B2` | `STRATUM_01` |
| `RP_B3` | `STRATUM_01` |
| `RT` | `STRATUM_01` |

All four registered revisions produce identical bytes, token IDs, common prefixes and discriminant positions on both wrapper arms, so exactly 1 stratum is registered. A checkpoint whose tuple differed in any element would be an isomorphic re-instantiation stratum and would never be pooled as the same frozen byte/token interface.

## 7. Coordinated mutations

24 registered, 24 killed, **0 survivors**, all killed by semantic validation.

* `target_checkpoint_identity`
* `rp_b_membership_and_order`
* `rp_b_ladder_length_l`
* `immutable_revision`
* `e0_legal_answer_surface`
* `e0_max_new_tokens`
* `d0_discriminant_position`
* `wrapper_role`
* `wrapper_bytes`
* `gate_alpha`
* `gate_sample_size`
* `gate_floor`
* `gate_pass_count`
* `multiplicity_family`
* `negative_control_margin`
* `negative_control_chance_level`
* `cot_k`
* `cot_parser`
* `cot_resource_bound`
* `state_transition`
* `census_wrapper_factor`
* `current_authoritative_path`
* `execution_authorization`
* `manifest_inclusion_rule`

## 8. Manifest

27 entries, aggregate `c3983f570281c1ab0a987d97d7861943dc8e11681e3d5bb2938f5a6276db8fe0`. The sealing design is acyclic: the manifest makes no self-hash claim, excludes only itself with a stated reason, and defers to the Git commit and tree for the outer recursive identity.

| path | bytes | sha256 | git blob |
| --- | --- | --- | --- |
| `studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.json` | 11748 | `9553310bfe14d01969321de8c51d651d580eae6f146388c566b74a0ddf04665c` | `e340b52574c7e15d6b9383e5f0e82c81e2ad5991` |
| `studies/study3r/acquisition/study3r_checkpoint_acquisition_v1.schema.json` | 7877 | `9a47a016e0a225759fc6bff224d69339afc67565dbebe3fd3b9440492915b930` | `4c00cf14b772c5bbb85674bd7b4ca1a2de73ab83` |
| `studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.json` | 3250 | `2501a8e2e91b5b7cf519ce4debb8579b6139960345b32f9cd4bba9f5bda675b3` | `f2c6c2150c6450ba31d35765b335bc261a456703` |
| `studies/study3r/acquisition/study3r_tokenizer_equivalence_v1.schema.json` | 3697 | `5b2a64ddd71cbd4512dd1b8ded2ff422ed7a6cd832230afd57e50e1bcbf1cb6d` | `eb68b3f98b3788a7d7582cf4f752b30951eee63f` |
| `studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.json` | 80771 | `28e09d944703be720a3533465f0511d69235229333700398d4cd45a6d29a611b` | `3dc986103f30209251b301ff3c67b230d632d788` |
| `studies/study3r/acquisition/study3r_tokenizer_surfaces_v1.schema.json` | 27355 | `6aaa5f069f9762ee3a90b5c7395451580135ed695cc49f803bee940d63609acb` | `00d5b95ddfd2dd647a92c756688181f8933fd70a` |
| `studies/study3r/analysis/study3r_atomic_cell_census_v1.json` | 15789 | `76df49bb8d88d1c215a1b0531249244c1978f4dd79e3a7d88b69d515ee951bdc` | `d4cfb405f21b0784898e1677ace4a170dc8c2ce7` |
| `studies/study3r/analysis/study3r_design_statistics.py` | 22060 | `a6c9cf7bc14b5fc58eeb6611d09118248da8c4abad1c9f31749fa82692c82969` | `e73460e37e098b43f1105d4f16bb3536bd87c6f0` |
| `studies/study3r/analysis/study3r_design_statistics_tables.json` | 52941 | `c00494c2213ce849fdaae583a99c2e84edfe54045761d4fd2ed54787c39bf478` | `9c73994302f6edb7287c5a982add21e107af31a7` |
| `studies/study3r/analysis/study3r_independent_recalculation.py` | 12027 | `6e9b43670684063abf156f5153e9128f9652b8355ad2986833e944063cb14532` | `7e51832b6f4f8c8ca5d761804077c54793cf504d` |
| `studies/study3r/analysis/study3r_independent_recalculation_tables.json` | 28587 | `4bd019631027c9232b08cb7b65428524347c06b8c6c8ab860b332e5a1a1ef02c` | `b584cf47d580b10e111747121d7cfd13292ba48a` |
| `studies/study3r/analysis/study3r_manifest.py` | 16322 | `f0f8aac7e70a83da45505b2f03259bbf26b40876610ae0acba2bad52d7e9a467` | `5c11f6af021d84e34e6aa099de61837324f7d075` |
| `studies/study3r/analysis/study3r_protocol_build.py` | 92080 | `d2fc5eb0b76680a60ac9f80ac4d4823cd37137438ec864da8cad3e7b0bcb586e` | `a09734766c18a74c54ef7ede4c96ae0a65798605` |
| `studies/study3r/analysis/study3r_tokenizer_probe.py` | 52666 | `b7a35426bbcd39d3f921d668f43c4dfa6027292b1dc4a0af6837f915aa9cb16f` | `77bdcd95508a5f6ded4f485229198437b1e1a98f` |
| `studies/study3r/prompts/study3r_protocol_v1_authoring_authority.md` | 16972 | `bafd90a73261dc710b861a1f9bcf286804b3e902bc31b8342e39174b9bfe0200` | `6d5c2b2657185d3088e10f03fa7713881b2b9c57` |
| `studies/study3r/protocol/study3r_protocol_current.json` | 814 | `37c18746ae6f580a0dc7ee23b4df3145ff2d111d75d0787f5f43e4b4da1cc401` | `2b3c467fe121d0419901f8ff1eb89fab2bb02521` |
| `studies/study3r/protocol/study3r_protocol_current.schema.json` | 1831 | `29dee1d6dd085a9802e529ab47cbd304659ca6522e45eac56777644e9afc9183` | `4828c3904e0e16f5e531ea331d0878b15a153aef` |
| `studies/study3r/protocol/study3r_protocol_v1.json` | 66444 | `3a9b68f68560594886251b36d0d46f8c1d0262103c87ce322732fd33da018c61` | `f749760e30a3de7f300db067d0e8a4ba4bd4093b` |
| `studies/study3r/protocol/study3r_protocol_v1.md` | 12584 | `eaccf354902ddc5cd64dc024b8c704404e0089981663e9cc3f7949fe58905a8f` | `cd0270ead07b268188b17848784a85de50cf1667` |
| `studies/study3r/protocol/study3r_protocol_v1.schema.json` | 60580 | `98f6fa884c3cae9f138aa9863bcfd3fe1aa086733dc4bc6e9048dfb5ef5e4f93` | `6594832f4351a2012db17be7957dfac395554403` |
| `studies/study3r/protocol/study3r_rendering_registry_v1.json` | 16057 | `830898eca5b385b3e4c35f613d8feea020dfaaa338c9813a117f287f1e74633f` | `4e1a92bffd4e1d593a355465a621177c7c9ae2e9` |
| `studies/study3r/protocol/study3r_rendering_registry_v1.schema.json` | 6224 | `0ebb1a701b31871213da00be7ef406324cb36a437be21609a4087023b2418abc` | `b72594ce77d2b18d5a28dd7eed8eca09a62aec88` |
| `studies/study3r/protocol/study3r_state_machine_v1.json` | 8677 | `450fc3c33d87cd8b608426d817f9b0a0e10d409e7337bef288ef6f0ddd687755` | `d5e6e44d018a7ed98d2ff0b19fc2f26bfdc7411a` |
| `studies/study3r/protocol/study3r_state_machine_v1.schema.json` | 6428 | `e5c86ab6509d4d15427bfaed41ead4bea396934e3e0dadf651a3aaa41c663b52` | `dfdcc042a3cf9c9e63896419ec67102e5925fe87` |
| `studies/study3r/study3r_candidate_manifest_v1.schema.json` | 4444 | `f416d8dc2bee1e45fc53943ded6febf86cad1dbba8734a7c80bec93856bb289d` | `8f4ae08873c09a3340038b1d1394cb0a88ae3c2f` |
| `studies/study3r/tasks/study3r_task_generators_v1.py` | 16233 | `47383a8f1c95f9efa868964097be5b2f9dfcce06d527678b1593685cdf52f97e` | `88951091f1efe412458b87acc322813071b3abc2` |
| `tests/test_study3r_protocol_v1.py` | 70206 | `7d625c270df85ee0c82871c6e170de400a79b5ff2a4e10dffcc52c32a2b9c626` | `ef50699bb58c7704f66dd1ce91d167d74e976e3f` |

## 9. Test results

| run | commit | failed | passed | skipped | errors |
| --- | --- | --- | --- | --- | --- |
| registered baseline | `cd9c0af3118c` | 8 | 5025 | 16 | 0 |
| final authoring head | `a6ea96f80db3` | 8 | 5120 | 16 | 0 |

Focused Study 3R modules: 163 passed, 0 failed.

New failure node IDs: **0**. Collection errors: **0**. The 8 standing failures are unchanged:

* `tests/test_parser_v3_seal_job.py::test_seal_writes_twelve_objects_with_the_set_manifest_last`
* `tests/test_parser_v3_seal_job.py::test_seal_refuses_a_non_empty_parent_prefix`
* `tests/test_phase1_0d_build_provenance.py::test_the_bundle_digest_ignores_the_checkout_line_endings`
* `tests/test_phase1_0d_generation_launcher_rp_compat.py::test_shim_has_valid_bash_syntax_and_frozen_launcher_remains_in_baseline`
* `tests/test_phase1_0d_protected_bytes.py::test_line_endings_do_not_change_the_rollup`
* `tests/test_phase1_0d_review_image.py::test_v2_refuses_a_rehashed_record_with_moved_metadata`
* `tests/test_study3_p0_feasibility_pilot.py::test_every_committed_p0_source_file_is_lf_only`
* `tests/test_study3_v0_7_focused_review.py::test_the_review_changed_no_reviewed_or_historical_path`

## 10. Protected bytes

30 reviewed, rejected-candidate, independent-review, protected historical and charter paths compared against `a08ec1462f02`: all identical.

`tests/test_study3r_operator_governance.py` had its two scope assertions extended; 0 protected-blob assertion was changed and the rejected review artifact was not edited.

## 11. Boundary

| counter | value |
| --- | --- |
| `decode_calls` | 0 |
| `evidence_ledger_rows_written` | 0 |
| `execution_seeds_drawn` | 0 |
| `forward_passes` | 0 |
| `generations` | 0 |
| `gpu_or_cloud_jobs` | 0 |
| `interfaces_selected` | 0 |
| `logit_reads` | 0 |
| `model_constructions` | 0 |
| `prefill_operations` | 0 |
| `remote_code_executions` | 0 |
| `scientific_items_realized` | 0 |
| `scoring_operations` | 0 |
| `weight_files_acquired` | 0 |

`formal_execution_authorized = false`, `execution_authorized = false`, `frozen = false`. `paper/evidence_ledger.csv` still ends at `EV-0016` and no evidence-ledger row was written. No RP-B candidate was selected, no bank was realized, no seed was drawn, no scientific claim was made and no Study 3M artifact exists.

## 12. Publication

`origin/main` immediately before this disclosure commit: `a6ea96f80db38eddefcbbbc4e58c53f305e3c702`. The final origin/main is the commit that publishes this disclosure, so its identity cannot be embedded in the disclosure itself without a hash fixed point. It is the head of the linear ancestry recorded above plus exactly one further commit carrying this disclosure and the Study 3R routing update, and it is verifiable directly from the published branch.

`STUDY3R_PROTOCOL_V1_AUTHORED_AWAITING_SINGLE_INDEPENDENT_FOCUSED_REVIEW`
