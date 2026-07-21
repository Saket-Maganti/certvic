# Main Task Builder Guide

`main_task_builder` consumes licensed source rows and annotation masks and constructs removal,
insertion, and verified-attribute candidate families with source/mask/asset hashes, questions,
answer transitions, engine policy, strata, difficulty, reserve groups, rejected rows, shortages, and
balance. Complex removal/insertion routes to verified offline inpainting; failed automated semantic,
artifact, non-target, answerability, or license checks never enter human review.
