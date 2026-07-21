
# CertVIC COCO Feasibility Guide

Provide a local COCO 2017 tree containing `annotations/instances_val2017.json` and `val2017/`.
The adapter never downloads or releases pixels:

```bash
python3 -m certvic.data.coco_adapter_stub --coco-root <COCO_ROOT>   --out-dir data/studies/second_domain_cvpr/feasibility --items 60 --seed 17011
```

The adapter parses categories/instances, exports polygon or uncompressed-RLE masks, and builds
balanced answer-changing removal/insertion candidates. Every candidate remains blocked until its
per-image Flickr license is verified; insertion also requires a hash-locked category asset. Generate,
review, adjudicate, freeze, and run the three-model matrix before applying the four frozen feasibility
gates. Compressed RLE requires a separately locked pycocotools environment and fails closed otherwise.
