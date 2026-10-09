fair-rope (grid_esota_ropefair_*) and rope_raw (grid_esota_rope_raw) runs made before two rope_adapter bug
fixes (2026-10-07). Both depressed benign preservation; attack/harm unaffected (poison values are emails/
accounts with @/digits, still structural). DO NOT use these for the paper. Rerun with the fixed adapter.
Bug 1 (CONST list shape): ROPE's router pins a named recipient as CONST with a LIST value (["team@..."]);
  our tools take a scalar string, so jsonschema const:[...] never equals the string and blocked every
  correctly-named send (benign_sig 0% preserve). Fix: _unwrap_scalar_const unwraps single-element CONST lists.
Bug 2 (structural label-colon FP): the write guard's _structural_ids treated a prose word ending in a colon
  ('email:') as a structural identifier, blocking legit benign remember writes. Fix: strip trailing punctuation
  and require a genuine marker (@ or / or digit or an INTERNAL ./: between alphanumerics).
Both fixes verified on 6 live benign trials (benign_sig/recipient/payee x2 seeds): all preserved, 0 gate_blocked.
