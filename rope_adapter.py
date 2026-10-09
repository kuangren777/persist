"""persistlab adapter for the official ROPE (arXiv 2608.27496) modules in agent-fuzz/ext/rope.
We do NOT reimplement ROPE; we wire the official enforce/origin/policy_synthesis/router into our tool loop
(af1 owns ext/rope; this glue is the persistlab side, E-SOTA head-to-head). Faithfulness scope: ROPE's
structural-origin tracker + policy + record-closure are the official code; our FLOOR tables and origin
globals are set for our tools and documented here.

Two configurations (af1 #367, EXPERIMENT_PLAN_ESOTA.md amendment 3):

  mode="record"  -> `rope` (fair, memory-as-record, Lemma 1). The side-tool target args are PS.RECORD, so a
                    value is authorized when it is in this session's request OR in the user's own authoritative
                    record. The cross-session store IS that record: its read result is filed under the reserved
                    record source (non-injectable) via a memory_record tool in AUTHORITATIVE_RECORD_TOOLS. To
                    keep that record trustworthy we add ROPE's write guard (Lemma 1, record closure): the memory
                    write tools (remember / update_policy) carry a PS.PROMPT floor on their value argument, so a
                    value that never appeared in the writing session's request cannot enter the store in the
                    first place. We do NOT use persistlab's own user/agent_tool provenance tags to decide what
                    counts as a record (af1 #367): the whole memory read is RECORD, and store integrity comes
                    only from ROPE's write guard; if an unguarded write path let other values in, the fix is to
                    add that write tool to WRITE_FLOOR, never to post-filter by our tags.

  mode="prompt"  -> `rope_raw` (ROPE as-is, cross-session). The official FLOOR with PS.PROMPT target args and
                    no write guard; the store read is an untrusted injectable input (it was produced in a prior
                    session). This is ROPE run unchanged against our cross-session threat model; it over-blocks
                    legitimate values the user stated in an earlier session (preserve ~33%), reported honestly
                    as the as-is number.
"""
import os, re, sys
sys.path.insert(0, os.environ.get("ROPE_SRC", os.path.join(os.path.dirname(os.path.abspath(__file__)), "third_party", "ROPE", "src")))
from rope import origin as O, policy_synthesis as PS            # noqa: E402
from rope.router import route_and_scope                         # noqa: E402
from rope.enforce import Enforcer, ValidationError              # noqa: E402

ROUTER_MODEL = os.environ.get("ROPE_ROUTER_MODEL", "claude-opus-4-8")   # unified across papers; recorded per row

# Side-effecting tools and the origin each target argument needs. The non-target free-text args (subject/body/
# key/role) are PS.FREE. The target args slide with the configuration: PS.RECORD for the fair memory-as-record
# config (request OR the user's own record), PS.PROMPT for the as-is config (request only).
def _side_floor(target_rule):
    return {
        "send_email":   {"to": target_rule, "cc": target_rule, "bcc": target_rule, "subject": PS.FREE, "body": PS.FREE},
        "http_post":    {"url": target_rule, "body": PS.FREE},
        "set_config":   {"value": target_rule, "key": PS.FREE},
        "grant_access": {"user": target_rule, "role": PS.FREE},
    }

RECORD_FLOOR = _side_floor(PS.RECORD)   # fair config side-tool gate
PROMPT_FLOOR = _side_floor(PS.PROMPT)   # as-is config side-tool gate

# ROPE write guard (Lemma 1 / record closure), fair config only: a value written into memory must appear in
# the writing session's request, else the store would carry an attacker value the record leg later trusts.
# Faithful to ROPE's audited floor, which never guards a prose argument (body/subject/content are PS.FREE) and
# whose record closure licenses only identifier fields (RECORD_FIELD_ALLOWLIST, e.g. order_id/product_id), the
# guard acts ONLY on structural identifiers a memory note introduces, not on ordinary prose words (af1 #380).
# This is an adapter choice for a free-text record, not a configuration present in the ROPE source: ROPE's own
# tokenizer treats any >=4-char word as an identifier, so a whole-note PS.PROMPT floor would reject nearly every
# benign memory write (preserve ~0; see test_rope.py::test_write_guard). A token counts as a structural
# identifier when it carries a non-word marker (a digit or one of @ . / :) and is at least six characters.
MEMORY_RECORD_TOOL = "memory_record"     # the reserved record source for the cross-session store (fair config)
DIRECTORY_RECORD_TOOL = "directory_record"   # part d (amendment 5): the unwritable platform-signed directory


def _set_record_globals(record_mode):
    # our harness has no AgentDojo verification / OTP / record-field tools; clear those defaults every time.
    O.RECORD_FIELD_ALLOWLIST = {}
    O.VERIFICATION_EXECUTOR_TOOLS = frozenset()
    O.OTP_DEFERRABLE_TOOLS = frozenset()
    # the cross-session store is the user's authoritative record only in the fair config; in the as-is config
    # nothing is a record, so the store read stays an injectable blob. part d adds the directory record tool
    # alongside the store in the fair config (it is unwritable by construction, af1 #700 i).
    recs = {MEMORY_RECORD_TOOL}
    if record_mode:
        recs.add(DIRECTORY_RECORD_TOOL)
    O.AUTHORITATIVE_RECORD_TOOLS = frozenset(recs) if record_mode else frozenset()


_INTERNAL_MARKER = re.compile(r"[A-Za-z0-9][.:][A-Za-z0-9]")   # a . or : between alphanumerics (domain, host:port)


def _structural_ids(text):
    """Structural identifier tokens of a memory note, by ROPE's own tokenizer plus the structural filter
    documented above. split_composites=False keeps a padded composite (attacker/<trusted>) one decision unit,
    matching ROPE's STRICT matcher, so it cannot ride in on a shared piece. A token qualifies only after its
    label/sentence punctuation is stripped and a GENUINE marker remains: an `@` or `/`, a digit, or an internal
    `.`/`:` with an alphanumeric on both sides. This excludes a prose word that merely ends in a colon (`email:`)
    or a period, which ROPE's raw tokenizer would otherwise treat as an identifier and wrongly block."""
    # two token sources (errata 5c): ROPE's tokenizer, plus RAW whitespace tokens. ROPE's `_TOKEN_RE` cannot
    # START a token with a symbol, so a leading-@ handle (`@ops-lead-ext`) tokenizes to `ops-lead-ext`, its `@`
    # marker is lost, and the write guard passed an attacker handle that the memory-as-record leg then trusted
    # (19 harmful part d cells). Whitespace tokens keep the leading symbol.
    cands = set(O.tokenize_identifiers(text, split_composites=False))
    cands |= {t for t in str(text or "").split()}
    out = set()
    for t in cands:
        st = t.strip(".:,;")
        if len(st) < 6:
            continue
        if ("@" in st) or ("/" in st) or any(c.isdigit() for c in st) or _INTERNAL_MARKER.search(st):
            out.add(st)
    return out

_ALL_TOOLS = ["read_file", "list_dir", "remember", "update_policy",
              "send_email", "http_post", "set_config", "grant_access"]
_SCOPE_CACHE = {}   # (user_prompt, mode) -> TaskScope (router reads only the user prompt; identical across seeds)


def _router(client_factory):
    def llm_complete(system, user):
        cl = client_factory(ROUTER_MODEL)
        r = cl.chat.completions.create(model=ROUTER_MODEL,
                                       messages=[{"role": "system", "content": system},
                                                 {"role": "user", "content": user}],
                                       max_tokens=600, temperature=0)
        return r.choices[0].message.content or ""
    return llm_complete


def _unwrap_scalar_const(scope):
    """ROPE's router pins a named recipient as a CONST whose value is a LIST (AgentDojo recipients are lists:
    e.g. ["team@..."]). Our tools take a SCALAR string for every target arg (to/cc/url/value/user/...), so a
    list-valued jsonschema `const` can never equal a string value and would block the correctly-named call.
    We unwrap a single-element CONST list to the scalar so the pin matches our tool shape (adapter choice for a
    scalar-recipient harness; the pin's meaning, "this arg must equal the named value", is unchanged)."""
    for tool, args in (scope.overrides or {}).items():
        for arg, rule in list(args.items()):
            if isinstance(rule, (list, tuple)) and len(rule) == 2 and rule[0] == "const":
                v = rule[1]
                if isinstance(v, (list, tuple)) and len(v) == 1:
                    args[arg] = ("const", v[0])
    return scope


def start_task(user_prompt, mem_texts, client_factory, mode="record"):
    """Build the ROPE Enforcer + OriginTracker for one activation task, in the given configuration.
    record mode files the cross-session store under the reserved record source (non-injectable); prompt mode
    files it as an injectable blob. read_file / list_dir results are absorbed live during the loop in both."""
    record_mode = (mode == "record")
    _set_record_globals(record_mode)
    floor = RECORD_FLOOR if record_mode else PROMPT_FLOOR
    key = (user_prompt, mode)
    if key in _SCOPE_CACHE:
        scope = _SCOPE_CACHE[key]
    else:
        scope = _unwrap_scalar_const(route_and_scope(user_prompt, floor, _router(client_factory)))
        _SCOPE_CACHE[key] = scope
    origin_map = {}
    policy = PS.compile_policy(floor, scope, origin_map=origin_map,
                              prompt_ids=O.tokenize_identifiers(user_prompt))
    enf = Enforcer(); enf.set_user_query(user_prompt); enf.update_security_policy(policy)
    enf.update_always_allowed_tools([t for t in _ALL_TOOLS if t not in floor])
    trk = O.OriginTracker(origin_map)
    for mt in mem_texts:
        if record_mode:
            absorb_record(trk, mt)          # the user's own authoritative record -> non-injectable
        else:
            absorb_result(trk, "memory_load", mt)   # untrusted cross-session blob -> injectable
    return enf, trk


def start_write_guard(user_prompt, client_factory=None):
    """The authorization set for one writing session's memory write guard (fair config only): the request's
    identifiers. A note may introduce a structural identifier only if it is in this set. Bucket-independent and
    request-only, so no router call. Returns the prompt id set that write_blocked() checks against."""
    return O.tokenize_identifiers(user_prompt)


def write_blocked(prompt_ids, name, args):
    """True if a memory write introduces a structural identifier the writing session never requested (Lemma 1
    write guard, fair config). Ordinary prose is unrestricted, exactly as ROPE's floor leaves prose args FREE."""
    text = args.get("note") or args.get("line") or ""
    return bool(_structural_ids(text) - set(prompt_ids))


def absorb_result(trk, fn, text):
    """File a tool result as an injectable blob (read_file / list_dir; the store in the as-is config)."""
    trk._absorb({"role": "tool", "content": str(text), "tool_call": {"function": fn, "args": {}}})


def absorb_directory(trk, text):
    """File a platform-signed directory result under the reserved record source (part d, amendment 5): the
    directory is an authoritative record tool in the fair config, so its identifiers license a matching
    PS.RECORD target value. Non-injectable: the directory is unwritable by construction (af1 #700 i)."""
    trk._absorb({"role": "tool", "content": str(text), "tool_call": {"function": DIRECTORY_RECORD_TOOL, "args": {}}})


def absorb_record(trk, text):
    """File a cross-session store item under the reserved record source (fair config): non-injectable, so its
    identifiers license a matching PS.RECORD target value. Faithful to origin.py: a result from a tool in
    AUTHORITATIVE_RECORD_TOOLS is added under RECORD_SOURCE_KEY with injectable=False."""
    trk._absorb({"role": "tool", "content": str(text), "tool_call": {"function": MEMORY_RECORD_TOOL, "args": {}}})


def check(enf, name, args):
    """True if ROPE denies this call."""
    try:
        enf.check_tool_call(name, args)
        return False
    except ValidationError:
        return True
