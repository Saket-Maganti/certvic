# Cross-Model Comparison on Qwen-Failed Items

- Qwen failed items inspected: 12
- Only Qwen flips: 12
- Qwen plus exactly one other model flips: 0
- All three models flip: 0

Interpretation: the observed failed set is Qwen-specific on these 12 items under the available artifacts.

| Item | Target | Qwen | InternVL | LLaVA | Only Qwen |
| --- | --- | --- | --- | --- | --- |
| `sflip_table_ADE_train_00000377` | table | yes->no | yes->yes | yes->yes | True |
| `sflip_sofa_ADE_train_00000704` | sofa | yes->no | yes->yes | yes->yes | True |
| `sflip_sofa_ADE_train_00000719` | sofa | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00000194` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00000617` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00000436` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00000630` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00000268` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_chair_ADE_train_00001105` | chair | yes->no | yes->yes | yes->yes | True |
| `sflip_car_ADE_train_00002029` | car | yes->no | yes->yes | yes->yes | True |
| `sflip_car_ADE_train_00002034` | car | yes->no | yes->yes | yes->yes | True |
| `sflip_car_ADE_train_00003061` | car | yes->no | yes->yes | yes->yes | True |
