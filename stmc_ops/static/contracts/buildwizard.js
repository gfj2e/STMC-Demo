/* STMC BuildWizard runtime data (from Django endpoint/context, not embedded HTML JSON) */
var __WIZ = window.STMC_WIZARD_DATA || {};
var __WIZ_MISSING_KEYS = [];

function __wizRequired(key){
  var value = __WIZ[key];
  if(value === undefined || value === null) __WIZ_MISSING_KEYS.push(key);
  return value;
}

function renderWizardConfigError(){
  if(!__WIZ_MISSING_KEYS.length) return;
  var missing = __WIZ_MISSING_KEYS.join(", ");
  console.error("[STMC] Missing required seed keys:", missing);
  var step = document.getElementById("stepContainer");
  if(step){
    step.innerHTML = ''
      + '<div class="card">'
      +   '<div class="section-hdr"><span>Wizard Configuration Error</span></div>'
      +   '<div class="card-pad">Missing required seed data from backend: <strong>' + esc(missing) + '</strong><br>'
      +   'Run seed commands and refresh this page.</div>'
      + '</div>';
  }
  var navPrev = document.getElementById("navPrev");
  var navNext = document.getElementById("navNext");
  var navStatus = document.getElementById("navStatus");
  if(navPrev) navPrev.disabled = true;
  if(navNext) navNext.disabled = true;
  if(navStatus) navStatus.textContent = "Configuration error";
}

var P = __wizRequired("P");
var SA = __wizRequired("SA");
var RD = __wizRequired("RD");
var MD = __wizRequired("MD");
var PM = __wizRequired("PM");
var P10 = __wizRequired("P10");
var BRANCHES = __wizRequired("BRANCHES");
var PLAN_METRICS = __wizRequired("PLAN_METRICS");
var INT_CONTRACT = __wizRequired("INT_CONTRACT");
var BASE_COSTS = __wizRequired("BASE_COSTS");
var INT_RC = __wizRequired("INT_RC");
var MODELS = __wizRequired("MODELS");
var PDF_FILES = __wizRequired("PDF_FILES");
var CRAFTSMAN = __wizRequired("CRAFTSMAN");
var APPLIANCE_LABELS = __wizRequired("APPLIANCE_LABELS");
var APPLIANCE_COSTS = __wizRequired("APPLIANCE_COSTS");
var ISLAND_ADDON_LABELS = __wizRequired("ISLAND_ADDON_LABELS");
var __WIZ_DEFAULT_MODE = window.STMC_WIZARD_DEFAULT_MODE || "";
var __WIZ_LOCK_MODE = window.STMC_WIZARD_LOCK_MODE || "";
var MODEL_ALIASES = __wizRequired("MODEL_ALIASES");

function canonicalModel(m){ return (m && MODEL_ALIASES[m]) ? MODEL_ALIASES[m] : m; }

function normalizeObjectKeys(obj){
  // For each alias key in obj, move its value to the canonical key, unless the canonical
  // key already has data (in which case we keep existing and delete the alias duplicate).
  Object.keys(MODEL_ALIASES).forEach(function(alias){
    if(Object.prototype.hasOwnProperty.call(obj, alias)){
      var canon = MODEL_ALIASES[alias];
      if(!Object.prototype.hasOwnProperty.call(obj, canon)){
        obj[canon] = obj[alias];
      }
      delete obj[alias];
    }
  });
}

function applyModelAliases(){
  // All model-keyed data objects get normalized to the canonical spelling.
  [PLAN_METRICS, INT_CONTRACT, BASE_COSTS, MODELS, CRAFTSMAN, PDF_FILES].forEach(normalizeObjectKeys);
  // LIBERTY GROVE exists only in INT_CONTRACTS_APP data — no exterior data — drop it.
  // (User directive: canonical list is 40 names = 39 preset from PM + CUSTOM FLOOR PLAN)
  ["LIBERTY GROVE"].forEach(function(m){
    if(MODELS[m]) delete MODELS[m];
    if(PDF_FILES[m]) delete PDF_FILES[m];
    if(CRAFTSMAN[m]) delete CRAFTSMAN[m];
  });
}

if(__WIZ_MISSING_KEYS.length === 0){
  applyModelAliases();
}

/* CANONICAL_MODELS — the alphabetized list shown in the model dropdown.
   39 preset models from PM + CUSTOM FLOOR PLAN pinned at end. */
var CANONICAL_MODELS = __WIZ_MISSING_KEYS.length === 0 ? Object.keys(PM).sort() : [];
// Ensure CUSTOM FLOOR PLAN exists in MODELS (it was in INT App MODELS).
// It's NOT in PM since PM is exterior-only presets. We keep it as a special entry.

function isTurnkeyEligible(model){
  var c = canonicalModel(model);
  if(c === "CUSTOM FLOOR PLAN") return true; // custom uses reverse-margin formula
  return !!(INT_CONTRACT[c] && typeof INT_CONTRACT[c].t === "number");
}

function isCustomFloorPlan(){
  if(STATE.model === "CUSTOM FLOOR PLAN") return true;
  var m = MODELS[STATE.model];
  if(m && m.isCustom) return true;
  var c = canonicalModel(STATE.model);
  if(INT_CONTRACT[c] === undefined && STATE.model) {
    // Turnkey-ineligible preset — caller should gate mode switch, not this helper.
    // Return false here; isCustomFloorPlan is specifically about derived-pricing behavior.
    return false;
  }
  return false;
}

/* ═══════════════════════════════════════════════════════════════
   STATE — single source of truth (§13f schema).
   NEVER scrape DOM; always read from STATE.
   ═══════════════════════════════════════════════════════════════ */
var STATE = defaultState();
function defaultState(){
  return {
    // Step 1
    customer:{name:"",addr:"",order:"",rep:"",p10:0},
    model:"", jobMode:"shell", branch:"summertown", miles:0,
    _stepIdx: 0,   // current visible-step index (0-based into the active step list)

    // Steps 2–3 (Exterior)
    ext:{
      slab:[],
      roof:[],
      foundType:"concrete", bsmtFrame:0, crawlSF:0,
      stories:1,
      wallTuff:0, wallType:"Metal",
      wainscotUpg:0, wallRock:0, wallStone:0,
      stoneUpg:0,
      sglW:0, dblW:0, win12:0, s2s:0, s2d:0,
      sglD:0, dblD:0,
      sheath:0, g26:0,
      awnQty:0, cupQty:0, chimQty:0,
      punchAmt:2500,
      customCharges:[],
      detShop:0, deckShown:0,
      ctrOverrides:{}
    },

    // Step 4 (Concrete)
    conc:{sqft:0, type:"", zone:1, lp:false, bp:false, wire:false, rebar:false, foam:0, customCharges:[]},

    // Step 5 (Interior Selections)
    int:null,   // populated on model load (or manually on Custom Floor Plan)

    // Step 6 Sub-Tab A (Cabinets) — lazy-initialized by initCabUpgradesState()
    cadCharges:[],
    cabUpgrades:null,

    // Step 6 Sub-Tab B (Countertops)
    ct:{areas:[], notes:""},

    // Step 6 sub-tab pill: "cabinets" or "countertops"
    cabSubTab:"cabinets",

    // Step 7 (Selections) — 5 pills
    sel:{
      docusign:{toggles:{}, qtys:{}, lfs:{}, gasType:"", customLines:[]},
      electrical:{toggles:{}, qtys:{}, customLines:[]},
      plumbing:{toggles:{}, qtys:{}, sfs:{}, customLines:[]},
      trim:{sfs:{}, qtys:{}, toggles:{}, concreteFinishLines:[], customLines:[]},
      custom:{upgrades:[], credits:[]}
    },

    // Backend-only (computed, never rendered)
    budget:{backend:{}}
  };
}

/* ═══════════════════════════════════════════════════════════════
   FORMATTING HELPERS
   ═══════════════════════════════════════════════════════════════ */
function $(n){return Math.round(n||0).toLocaleString("en-US")}
function fmt(n){return "$"+$(n)}
function fmtC(n){return "$"+(n||0).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g,",")}
function pn(v){var x=parseFloat(v);return isNaN(x)?0:x}
function pi(v){var x=parseInt(v,10);return isNaN(x)?0:x}
function esc(s){return (s==null?"":String(s)).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]})}
function showToast(msg){var t=document.getElementById("toast");t.textContent=msg;t.classList.add("show");clearTimeout(showToast._id);showToast._id=setTimeout(function(){t.classList.remove("show")},2200)}

/* ═══════════════════════════════════════════════════════════════
   PURE COMPUTED HELPERS — all take STATE.ext (or STATE) as input.
   No global-var reads. Preserves V8's battle-tested logic.
   ═══════════════════════════════════════════════════════════════ */
function livSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.n==="1st Floor Living Area"||s.n==="2nd Floor Area"||s.n==="Bonus Room")t+=pn(s.sf)});return t}
function garSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.n==="Garage Area")t+=pn(s.sf)});return t}
function porSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.n==="Front Porch Area"||s.n==="Back Porch Area")t+=pn(s.sf)});return t}
function carSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.n==="Carport Area")t+=pn(s.sf)});return t}
function bonSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.n==="Bonus Room"||s.n==="2nd Floor Area")t+=pn(s.sf)});return t}
function tgSF(E){var t=0;(E||STATE.ext).slab.forEach(function(s){if(s.tg)t+=pn(s.sf)});return t}
function totSlab(E){var t=0;(E||STATE.ext).slab.forEach(function(s){t+=pn(s.sf)});return t}
function totRoof(E){var t=0;(E||STATE.ext).roof.forEach(function(r){t+=pn(r.sf)});return t}
function rfMetalStd(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.type==="metal"&&!r.steep)t+=pn(r.sf)});return t}
function rfMetalSteep(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.type==="metal"&&r.steep)t+=pn(r.sf)});return t}
function rfSsStd(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.type==="ss"&&!r.steep)t+=pn(r.sf)});return t}
function rfSsSteep(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.type==="ss"&&r.steep)t+=pn(r.sf)});return t}
function rfSsSF(E){return rfSsStd(E)+rfSsSteep(E)}
function rfSteep(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.steep)t+=pn(r.sf)});return t}
function rfShAll(E){var t=0;(E||STATE.ext).roof.forEach(function(r){if(r.type==="shingles")t+=pn(r.sf)});return t}
function sofLF(E){return Math.round((livSF(E)+garSF(E))*0.11)}
function baseSF(E){return livSF(E)+garSF(E)+porSF(E)}
function totEW(E){E=E||STATE.ext;return pn(E.wallTuff)+pn(E.wallRock)+pn(E.wallStone)}
function cSF(E){E=E||STATE.ext;return pn(E.crawlSF)||livSF(E)}
function grossWallSF(E){E=E||STATE.ext;return pn(E.wallTuff)+(pn(E.dblD)*45)+(pn(E.sglD)*22)+(pn(E.dblW)*33)+(pn(E.sglW)*17)+(pn(E.s2s)*17)+(pn(E.s2d)*33)}

/* ═══════════════════════════════════════════════════════════════
   LINE-ITEM ENGINE — pure STATE readers, refactored from V8.
   buildSalesItems = customer-facing line items (drives Contract Part A)
   buildCtrItems   = contractor labor line items (drives Step 9 Budget Part A)
   buildConcItems  = concrete line items (feeds into both)
   ═══════════════════════════════════════════════════════════════ */
function buildConcItems(S){
  S = S || STATE;
  var c = S.conc, db = P.conc, items = [];
  function add(l,q,r,u,sec){ if(q<=0||r<=0) return; items.push({label:l,qty:q,rate:r,cost:q*r,unit:u,section:sec||"Concrete"}); }
  if(pn(c.sqft)>0 && c.type && db.types[c.type]){
    var r = db.types[c.type][c.zone];
    var sub = pn(c.sqft) * r;
    var mono = (c.type === "4mono" || c.type === "6mono");
    var mn = mono ? db.minM : db.minF;
    var fin = Math.max(sub, mn);
    add("Concrete ("+c.type+", Zone "+c.zone+")", pn(c.sqft), r, "SF");
    if(fin > sub) add("Minimum adjustment", 1, fin-sub, "ea");
  }
  if(c.lp) add("Line pump", 1, db.lp, "ea");
  if(c.bp) add("Boom pump", 1, db.bp, "ea");
  if(pn(c.sqft)>0 && c.wire)  add("Wire",  pn(c.sqft), db.wire,  "SF");
  if(pn(c.sqft)>0 && c.rebar) add("Rebar", pn(c.sqft), db.rebar, "SF");
  if(pn(c.foam)>0) add("2\" foam perimeter", pn(c.foam), db.foam, "LF");
  (c.customCharges || []).forEach(function(cc){
    if(pn(cc.qty)>0 && pn(cc.rate)>0) add(cc.desc || "Concrete custom", pn(cc.qty), pn(cc.rate), cc.unit || "SF");
  });
  return items;
}

/* Preset customer labor base by model. Exterior upgrades still add on top. */
var PRESET_LABOR = {
  "ARROWHEAD LODGE": 63500,
  "THE BERKLEY": 49500,
  "BLUEWATER": 19600,
  "BROOKSIDE": 20528,
  "BUFFALO RUN": 32000,
  "CAJUN": 43315,
  "CEDAR RIDGE": 87000,
  "COTTONWOOD BEND": 44500,
  "CREEKSIDE SPECIAL": 41380,
  "DAUGHERTY": 83500,
  "EAST FORK DELUXE": 33200,
  "FOX RUN BARNDOMINIUM": 83000,
  "FRANKS BARNDOMINIUM": 77500,
  "THE HADLEY": 61500,
  "HUNTLEY": 27000,
  "HUNTLEY 2.0": 30724,
  "JOHNSON": 44500,
  "MAPLE GROVE": 69500,
  "MARTIN LODGE": 49500,
  "MEADOWS END": 46120,
  "MINI PETTUS": 48700,
  "NORTHVIEW LODGE": 37500,
  "PETTUS": 59847,
  "THE PETTUS": 59847,
  "PINEY CREEK": 33260,
  "RIDGECREST": 69200,
  "RIVERVIEW COTTAGE": 31500,
  "ROBERTSON": 46300,
  "ROBERTSON DELUXE": 49500,
  "ROCKY TOP": 55060,
  "SHADY MEADOWS": 26980,
  "SOUTHERN MONITOR": 38800,
  "THE SOUTHERN MONITOR": 38800,
  "SUMMER BREEZE": 78500,
  "THOMPSON": 50800,
  "TIMBER CREST": 28700,
  "WESTVIEW MANOR": 82000,
  "WHISPERING PINES": 44800,
  "WILLOW CREEK": 25200,
  "WOODSIDE SPECIAL": 44000,
  "WOODSIDE SPECIAL DELUXE": 44000
};

/* Remote branch interior contract overrides + material freight/transit markup. */
var INT_CONTRACT_REMOTE = {
  "ARROWHEAD LODGE": {t: 221067},
  "THE BERKLEY": {t: 163020},
  "BLUEWATER": {t: 118580},
  "BROOKSIDE": {t: 115500},
  "BUFFALO RUN": {t: 161040},
  "CAJUN": {t: 178200},
  "CEDAR RIDGE": {t: 358710},
  "COTTONWOOD BEND": {t: 205029},
  "CREEKSIDE SPECIAL": {t: 190080},
  "DAUGHERTY": {t: 302267},
  "EAST FORK DELUXE": {t: 150150},
  "FOX RUN BARNDOMINIUM": {t: 303600},
  "FRANKS BARNDOMINIUM": {t: 331760},
  "THE HADLEY": {t: 377190},
  "HUNTLEY": {t: 166320},
  "HUNTLEY 2.0": {t: 166320},
  "JOHNSON": {t: 169290},
  "MAPLE GROVE": {t: 331320},
  "MARTIN LODGE": {t: 232848},
  "MEADOWS END": {t: 242330},
  "MINI PETTUS": {t: 225060},
  "NORTHVIEW LODGE": {t: 190080},
  "PETTUS": {t: 272026},
  "THE PETTUS": {t: 272026},
  "PINEY CREEK": {t: 165528},
  "RIDGECREST": {t: 262636},
  "RIVERVIEW COTTAGE": {t: 184437},
  "ROBERTSON": {t: 222750},
  "ROBERTSON DELUXE": {t: 247500},
  "ROCKY TOP": {t: 250958},
  "SHADY MEADOWS": {t: 115500},
  "SOUTHERN MONITOR": {t: 233035},
  "THE SOUTHERN MONITOR": {t: 233035},
  "SUMMER BREEZE": {t: 402380},
  "THOMPSON": {t: 250800},
  "TIMBER CREST": {t: 123585},
  "WESTVIEW MANOR": {t: 389158},
  "WHISPERING PINES": {t: 198000},
  "WILLOW CREEK": {t: 137445},
  "WOODSIDE SPECIAL": {t: 190080},
  "WOODSIDE SPECIAL DELUXE": {t: 179520}
};

var MFT_PCT = {
  "ARROWHEAD LODGE": 0.15,
  "THE BERKLEY": 0.15,
  "BLUEWATER": 0.15,
  "BROOKSIDE": 0.15,
  "BUFFALO RUN": 0.15,
  "CAJUN": 0.15,
  "CEDAR RIDGE": 0.22,
  "COTTONWOOD BEND": 0.15,
  "CREEKSIDE SPECIAL": 0.15,
  "DAUGHERTY": 0.22,
  "EAST FORK DELUXE": 0.15,
  "FOX RUN BARNDOMINIUM": 0.20,
  "FRANKS BARNDOMINIUM": 0.22,
  "THE HADLEY": 0.22,
  "HUNTLEY": 0.15,
  "HUNTLEY 2.0": 0.15,
  "JOHNSON": 0.15,
  "MAPLE GROVE": 0.22,
  "MARTIN LODGE": 0.20,
  "MEADOWS END": 0.20,
  "MINI PETTUS": 0.20,
  "NORTHVIEW LODGE": 0.15,
  "PETTUS": 0.22,
  "THE PETTUS": 0.22,
  "PINEY CREEK": 0.15,
  "RIDGECREST": 0.22,
  "RIVERVIEW COTTAGE": 0.15,
  "ROBERTSON": 0.20,
  "ROBERTSON DELUXE": 0.20,
  "ROCKY TOP": 0.20,
  "SHADY MEADOWS": 0.15,
  "SOUTHERN MONITOR": 0.20,
  "THE SOUTHERN MONITOR": 0.20,
  "SUMMER BREEZE": 0.22,
  "THOMPSON": 0.20,
  "TIMBER CREST": 0.15,
  "WESTVIEW MANOR": 0.22,
  "WHISPERING PINES": 0.20,
  "WILLOW CREEK": 0.15,
  "WOODSIDE SPECIAL": 0.15,
  "WOODSIDE SPECIAL DELUXE": 0.15
};

function isRemoteBranch(){
  return STATE.branch === "morristown" || STATE.branch === "hopkinsville";
}

function getIntContractForBranch(model){
  var m = canonicalModel(model || STATE.model);
  if(isRemoteBranch()){
    var remote = INT_CONTRACT_REMOTE[m];
    if(remote && typeof remote.t === "number") return remote.t;
  }
  var base = INT_CONTRACT[m];
  return (base && typeof base.t === "number") ? base.t : 0;
}

function getMFTMarkup(model){
  if(!isRemoteBranch()) return 0;
  var m = canonicalModel(model || STATE.model);
  var pct = MFT_PCT[m] || 0;
  return Math.round(pn(STATE.customer.p10) * pct);
}

function buildSalesItems(S){
  S = S || STATE;
  var E = S.ext, s = P.sales, over100 = S.miles >= 1, items = [];
  function add(l,q,r,u,sec){ if(q<=0||r<=0) return; items.push({label:l,qty:q,rate:r,cost:q*r,unit:u,section:sec||"Labor"}); }
  var m = canonicalModel(S.model);
  var preset = PRESET_LABOR[m];

  if(preset && m !== "CUSTOM FLOOR PLAN"){
    items.push({label:"Base Customer Labor - "+m, qty:1, rate:preset, cost:preset, unit:"ea", section:"Labor"});
    if(rfSsSF(E) > 0) add("Standing seam roof add", rfSsSF(E), s.ssAdd, "SF");
    if(E.wallType !== "Metal") add("Siding upgrade ("+E.wallType+")", pn(E.wallTuff), s.sidingAdd, "SF");
    if(E.stoneUpg && pn(E.wallStone) > 0) add("Stone area", pn(E.wallStone), over100 ? s.stoneO : s.stoneW, "SF");
    if(pn(E.chimQty) > 0) add("Stone chimney/roofline lifts", pn(E.chimQty), s.stoneLift, "ea");
    if(tgSF(E) > 0) add("T&G porch ceilings", tgSF(E), s.tg, "SF");
    if(pn(E.awnQty) > 0) add("Timber framed awnings", pn(E.awnQty), s.awning, "ea");
    if(pn(E.cupQty) > 0) add("Cupola installation", pn(E.cupQty), s.cupola, "ea");
  } else {
    var bSF = baseSF(E);
    add("Base labor ("+$(bSF)+" SF)", bSF, s.base, "SF");
    if(E.foundType === "crawl") add("Framing over crawl/basement", cSF(E), s.crawl, "SF");
    if(rfSteep(E) > 0) add("Roof 9/12+ pitch add", rfSteep(E), s.steepAdd, "SF");
    if(rfSsSF(E) > 0) add("Standing seam roof add", rfSsSF(E), s.ssAdd, "SF");
    if(E.wallType !== "Metal") add("Siding upgrade ("+E.wallType+")", pn(E.wallTuff), s.sidingAdd, "SF");
    if(E.stoneUpg && pn(E.wallStone) > 0) add("Stone area", pn(E.wallStone), over100 ? s.stoneO : s.stoneW, "SF");
    if(pn(E.chimQty) > 0) add("Stone chimney/roofline lifts", pn(E.chimQty), s.stoneLift, "ea");
    if(tgSF(E) > 0) add("T&G porch ceilings", tgSF(E), s.tg, "SF");
    if(pn(E.awnQty) > 0) add("Timber framed awnings", pn(E.awnQty), s.awning, "ea");
    if(pn(E.cupQty) > 0) add("Cupola installation", pn(E.cupQty), s.cupola, "ea");
  }
  // Concrete pass-through
  buildConcItems(S).forEach(function(ci){ items.push(ci); });
  // Punch is a separate line only in calculator-mode models.
  if(!preset || m === "CUSTOM FLOOR PLAN"){
    var pa = Math.max(P.punch, pn(E.punchAmt) || 0);
    add("Punch", 1, pa, "ea", "Other");
  }
  (E.customCharges || []).forEach(function(cc){
    if(pn(cc.qty) > 0 && pn(cc.rate) > 0)
      add(cc.desc || "Custom charge", pn(cc.qty), pn(cc.rate), cc.unit || "SF", "Custom");
  });
  return items;
}

function buildCtrItems(S){
  S = S || STATE;
  var E = S.ext, cr = P.ctr, b = S.miles >= 1 ? "o" : "u";
  var ctrOv = E.ctrOverrides || {};
  var items = [];
  function add(key, sec, lbl, qty, rate, unit){
    var q = (ctrOv[key] !== undefined) ? pn(ctrOv[key]) : qty;
    items.push({key:key, section:sec, label:lbl, qty:q, dflt:qty, rate:rate, cost:q*rate, unit:unit});
  }
  var slb = livSF(E) + garSF(E);
  var bon = bonSF(E);
  // FRAMING
  add("fSlab","Framing","Framing per sq ft of usable floor space on a slab",slb,cr.fSlab[b],"SF");
  add("rafter","Framing","Rafter roof framing per sq ft",0,cr.fRafter[b],"SF");
  add("fUp","Framing","Framing per sq ft upstairs",bon,cr.fUp[b],"SF");
  add("fBsmt","Framing","Framing over a basement or crawlspace", E.foundType === "crawl" ? cSF(E) : 0, cr.fBsmt[b],"SF");
  add("bsmtLf","Framing","Framing rooms in basement (linear ft)",0,cr.bsmtLf,"LF");
  add("fAttic","Framing","Open attic (no framed stairs) & carport framing",carSF(E),cr.fAttic[b],"SF");
  add("fPorch","Framing","Timber framed porch roof system on a slab",porSF(E),cr.fPorch[b],"SF");
  add("deckRoof","Framing","Wood framed deck incl. railing, staircase & roof system",0,cr.deckRoof[b],"SF");
  add("awnU","Framing","Timber awnings built on site under 8' (qty)",0,cr.awnU,"ea");
  add("awnO","Framing","Timber awnings built on site over 8' (qty)",pn(E.awnQty),cr.awnO,"ea");
  // SHEATHING — uses baseSF (flat footprint), not slope-adjusted totRoof
  add("osb","Sheathing","OSB/Plywood sheathing on roof (sq ft)", E.sheath ? baseSF(E) : 0, cr.osb,"SF");
  // ROOF — per-row type × pitch tier
  var stdRate = E.g26 ? 1.5 : cr.r612[b];
  add("rStd","Roof","Roof metal 7/12 or under (sq ft)",rfMetalStd(E),stdRate,"SF");
  add("rSteep","Roof","Roof metal 8/12 or greater (sq ft)",rfMetalSteep(E),cr.r812[b],"SF");
  add("ssStd","Roof","Standing seam 7/12 or under (sq ft)",rfSsStd(E),cr.ss[b],"SF");
  add("ssSteep","Roof","Standing seam 8/12 or greater (sq ft)",rfSsSteep(E),cr.ss912[b],"SF");
  add("shingSF","Roof","Shingles (sq ft)",rfShAll(E),cr.shing[b],"SF");
  // WALLS — mWall uses gross wall SF
  add("mWall","Walls","Metal installation walls (sq ft of coverage)",grossWallSF(E),cr.mWall[b],"SF");
  add("mCeil","Walls","Metal installation ceiling (sq ft of coverage)",garSF(E),cr.mCeil[b],"SF");
  add("bb","Walls","Board & Batten (per sq ft)", E.wallType === "Board and Batten" ? pn(E.wallTuff) : 0, cr.bb[b],"SF");
  add("lph","Walls","LP & Hardie siding (per sq ft)", (E.wallType === "LP" || E.wallType === "Hardie Siding") ? pn(E.wallTuff) : 0, cr.lph[b],"SF");
  add("vinyl","Walls","Vinyl siding (per sq ft)", E.wallType === "Vinyl Siding" ? pn(E.wallTuff) : 0, cr.vinyl[b],"SF");
  add("bw","Walls","Beam wrap (per linear ft)",0,cr.bw[b],"LF");
  add("sof","Walls","Soffit (per linear ft)",sofLF(E),cr.sof[b],"LF");
  // STONE
  add("stoneLbr","Stone","Stone labor (per sq ft of coverage)", E.stoneUpg ? pn(E.wallStone) : 0, cr.stone[b],"SF");
  // DOORS & WINDOWS
  add("dblD","Doors & Windows","Double door (qty)",pn(E.dblD),cr.dblD,"ea");
  add("sglD","Doors & Windows","Single door (qty)",pn(E.sglD),cr.sglD,"ea");
  add("dblW","Doors & Windows","Double window (qty)",pn(E.dblW),cr.dblW,"ea");
  add("sglW","Doors & Windows","Single window (qty)",pn(E.sglW),cr.sglW,"ea");
  add("s2s","Doors & Windows","Second-story window over 12' from ground (single)",pn(E.s2s),cr.s2s,"ea");
  add("s2d","Doors & Windows","Second-story window over 12' from ground (double)",pn(E.s2d),cr.s2d,"ea");
  // OTHER
  add("cup","Other","Cupola installation (qty)",pn(E.cupQty),cr.cup,"ea");
  add("tgC","Other","T&G porch ceilings (sq ft)",tgSF(E),cr.tgC,"SF");
  add("deckNR","Other","Wood decks without roof (sq ft)",0,cr.deckNR,"SF");
  add("trex","Other","TREX decking (sq ft)",0,cr.trex,"SF");
  // CUSTOM — pass through from Plans tab at customer rate
  (E.customCharges || []).forEach(function(cc, i){
    if(pn(cc.qty) > 0 && pn(cc.rate) > 0)
      add("custom_"+i, "Custom", cc.desc || "Custom charge", pn(cc.qty), pn(cc.rate), cc.unit || "SF");
  });
  return items;
}

function sumItems(items){ var t=0; items.forEach(function(i){ t += i.cost; }); return t; }
function sumSection(items, sec){ var t=0; items.forEach(function(i){ if(i.section===sec) t+=i.cost; }); return t; }
function getSections(items){ var seen={}, out=[]; items.forEach(function(i){ if(!seen[i.section]){ seen[i.section]=1; out.push(i.section); } }); return out; }
function defaultRoofName(){ return (ROOF_AREA_NAMES && ROOF_AREA_NAMES.length) ? ROOF_AREA_NAMES[0] : ""; }
function defaultRoofType(){ return (ROOF_TYPES && ROOF_TYPES.length) ? ROOF_TYPES[0].v : ""; }

/* ═══════════════════════════════════════════════════════════════
   LOAD MODEL — populates STATE from PM/MD/RD/P10 for the canonical model.
   Handles CUSTOM FLOOR PLAN (leaves exterior blank; user enters manually).
   ═══════════════════════════════════════════════════════════════ */
function loadModel(m){
  STATE.model = m;
  // Reset interior metrics so they rebuild fresh on Step 5 entry
  STATE.int = null;
  STATE.cabUpgrades = null;
  STATE.ct = {areas:[], notes:""};
  STATE.cadCharges = [];

  if(m === "CUSTOM FLOOR PLAN"){
    // Custom Floor Plan — leave all exterior empty, let the user enter everything.
    // Still reset ext to clean defaults so stale data from a prior model doesn't linger.
    STATE.ext = defaultState().ext;
    STATE.customer.p10 = 0;
    return;
  }

  var p = PM[m] || {};
  STATE.ext.stories = p.st || 1;
  STATE.ext.slab = (MD[m] && MD[m].sqft ? MD[m].sqft : []).map(function(s){return {n:s.n, sf:s.sf, tg:0}});
  STATE.ext.roof = (RD[m] || []).map(function(r){return {n:r.n, steep:0, type:defaultRoofType(), sf:r.sf}});
  if(STATE.ext.roof.length === 0) STATE.ext.roof = [{n:defaultRoofName(), steep:0, type:defaultRoofType(), sf:0}];
  STATE.ext.wallTuff = p.ew || 0;
  STATE.ext.wallRock = 0;
  STATE.ext.wallStone = 0;
  STATE.ext.wallType = "Metal";
  STATE.ext.stoneUpg = 0;
  STATE.ext.wainscotUpg = 0;
  STATE.ext.dblD = p.dd || 0;
  STATE.ext.sglD = p.sd || 0;
  STATE.ext.dblW = p.dw || 0;
  STATE.ext.sglW = p.sw || 0;
  STATE.ext.s2s = 0; STATE.ext.s2d = 0;
  STATE.ext.win12 = 0; STATE.ext.deckShown = 0; STATE.ext.detShop = 0;
  STATE.ext.awnQty = 0; STATE.ext.cupQty = 0; STATE.ext.chimQty = 0;
  STATE.ext.foundType = "concrete"; STATE.ext.bsmtFrame = 0; STATE.ext.crawlSF = 0;
  STATE.ext.sheath = 0; STATE.ext.g26 = 0;
  STATE.ext.punchAmt = pn(P.punch);
  STATE.ext.customCharges = [];
  STATE.ext.ctrOverrides = {};

  // Auto-fill P10 from preset (user can still edit)
  STATE.customer.p10 = P10[m] || 0;

  // If the user was on Turnkey mode but selected a turnkey-ineligible model, bump them to Shell.
  if(STATE.jobMode === "turnkey" && !isTurnkeyEligible(m)){
    STATE.jobMode = "shell";
    showToast("Interior turnkey not yet priced for "+m+" — switched to Shell Only.");
  }
}

/* ═══════════════════════════════════════════════════════════════
   WIZARD FRAMEWORK
  Shell Only: 6 visible steps (1→2→3→4→Contract→Budget, internally step 9)
   Turnkey:   9 visible steps (1→2→3→4→5→6→7→8 Contract→9 Budget)
   The internal step IDs map to Step 1 renderers for Shell's Contract at renderStep8.
   ═══════════════════════════════════════════════════════════════ */
var STEP_DEFS = {
  1:{label:"Customer & Model", render:renderStep1},
  2:{label:"Slab & Foundation",render:renderStep2},
  3:{label:"Roof & Exterior",  render:renderStep3},
  4:{label:"Concrete",         render:renderStep4},
  5:{label:"Interior",         render:renderStep5},
  6:{label:"Cabinets",         render:renderStep6},
  7:{label:"Selections",       render:renderStep7},
  8:{label:"Contract",         render:renderStep8},
  9:{label:"Budget",           render:renderStep9}
};

function activeStepIds(){
  return STATE.jobMode === "shell" ? [1,2,3,4,8,9] : [1,2,3,4,5,6,7,8,9];
}
function currentStepId(){
  var ids = activeStepIds();
  var i = Math.max(0, Math.min(STATE._stepIdx, ids.length - 1));
  return ids[i];
}
function canAdvanceFromStep(sid){
  if(sid === 1) return !!STATE.model && pn(STATE.customer.p10) > 0;
  return true;
}

function advanceBlockReason(sid){
  // Returns a user-facing message if step cannot advance, or "" if OK
  if(sid === 1){
    if(!STATE.model) return "Select a model before continuing.";
    if(pn(STATE.customer.p10) <= 0) return "Enter the P10 Material Total before continuing.";
  }
  return "";
}

function renderProgressBar(){
  var el = document.getElementById("progressBar");
  var ids = activeStepIds();
  var cur = STATE._stepIdx;
  var h = "";
  ids.forEach(function(sid, i){
    var state = i < cur ? "done" : (i === cur ? "active" : "");
    // Sequential lock: can click on current, previous, or next if advance allowed
    var locked = i > cur && !canAdvanceFromStep(currentStepId());
    // Display number is visible position (1-based), not internal step ID, per spec §2
    var displayNum = i + 1;
    h += '<button class="prog-step '+state+'" '+(locked?'disabled':'')
       + ' onclick="wizGoTo('+i+')">'
       + '<div class="prog-num"><span class="prog-num-txt">'+displayNum+'</span></div>'
       + '<div class="prog-label">'+esc(STEP_DEFS[sid].label)+'</div>'
       + '</button>';
    if(i < ids.length - 1) h += '<div class="prog-sep '+(i<cur?"done":"")+'"></div>';
  });
  el.innerHTML = h;
}

function renderCurrentStep(){
  var sid = currentStepId();
  var fn = STEP_DEFS[sid] && STEP_DEFS[sid].render;
  if(fn) fn(); else renderStepStub();
  renderProgressBar();
  renderNav();
  renderRunningTotal();
  scheduleSave();
}

function renderNav(){
  var prev = document.getElementById("navPrev");
  var next = document.getElementById("navNext");
  var status = document.getElementById("navStatus");
  var ids = activeStepIds();
  var cur = STATE._stepIdx;
  prev.disabled = cur === 0;
  var sid = currentStepId();
  var atEnd = cur === ids.length - 1;
  next.disabled = atEnd || !canAdvanceFromStep(sid);
  if(atEnd){ next.textContent = "— End —"; } else { next.textContent = "Next →"; }
  status.textContent = "Step "+(cur+1)+" of "+ids.length+" · "+STEP_DEFS[sid].label;
}

function wizNext(){
  var sid = currentStepId();
  var reason = advanceBlockReason(sid);
  if(reason){ showToast(reason); return; }
  var ids = activeStepIds();
  // Force Contract -> Budget transition when Budget exists in the active flow.
  if(sid === 8){
    var budgetIdx = ids.indexOf(9);
    if(budgetIdx >= 0 && STATE._stepIdx < budgetIdx){
      STATE._stepIdx = budgetIdx;
      renderCurrentStep();
      window.scrollTo({top:0, behavior:"smooth"});
      return;
    }
  }
  if(STATE._stepIdx < ids.length - 1){
    STATE._stepIdx++;
    renderCurrentStep();
    window.scrollTo({top:0, behavior:"smooth"});
  }
}
function wizPrev(){
  if(STATE._stepIdx > 0){
    STATE._stepIdx--;
    renderCurrentStep();
    window.scrollTo({top:0, behavior:"smooth"});
  }
}
function wizGoTo(idx){
  var ids = activeStepIds();
  if(idx < 0 || idx >= ids.length) return;
  // Allow jumping back freely, forward only if current step allows advance
  if(idx > STATE._stepIdx){
    for(var i = STATE._stepIdx; i < idx; i++){
      var ids2 = activeStepIds();
      var reason = advanceBlockReason(ids2[i]);
      if(reason){ showToast(reason); return; }
    }
  }
  STATE._stepIdx = idx;
  renderCurrentStep();
  window.scrollTo({top:0, behavior:"smooth"});
}

/* ═══════════════════════════════════════════════════════════════
   RUNNING TOTAL (header)
   Step 1 pass: only P10 has been entered. Shell total = P10 alone
   until Steps 2–4 wire in customer labor + concrete in Step 2 build.
   ═══════════════════════════════════════════════════════════════ */
function computeShellTotal(){
  // Shell = P10 Material + MFT (remote only) + customer labor + optional detached-shop adders.
  var p10 = pn(STATE.customer.p10);
  var mft = getMFTMarkup();
  var detP10 = pn(STATE.ext.detShopP10 || 0);
  var detLabor = pn(STATE.ext.detShopLabor || 0);
  if(!STATE.model) return p10 + mft + detP10 + detLabor;
  var labor = sumItems(buildSalesItems());
  return p10 + mft + labor + detP10 + detLabor;
}
function computeTurnkeyTotal(){
  // Shell + interior contract (preset INT_CONTRACT + CAD, or custom reverse-margin)
  return computeShellTotal() + computeInteriorContractPrice();
}

function renderRunningTotal(){
  var hdrTotal = document.getElementById("hdrTotal");
  var hdrSub = document.getElementById("hdrSub");
  var hdrSplit = document.getElementById("hdrSplit");
  if(STATE.jobMode === "shell"){
    var shell = computeShellTotal();
    hdrTotal.textContent = fmt(shell);
    hdrSub.textContent = "Total Exterior Shell Package";
    hdrSplit.style.display = "none";
  } else {
    var shellT = computeShellTotal();
    var intC = computeInteriorContractPrice();
    var total = shellT + intC;
    hdrTotal.textContent = fmt(total);
    hdrSub.textContent = "Total Contracted Amount";
    if(STATE.model){
      hdrSplit.style.display = "block";
      hdrSplit.textContent = "Shell: "+fmt(shellT)+"  ·  INT: "+fmt(intC);
    } else {
      hdrSplit.style.display = "none";
    }
  }
}

/* ═══════════════════════════════════════════════════════════════
   STEP 1 — CUSTOMER & MODEL
   ═══════════════════════════════════════════════════════════════ */
function renderStep1(){
  var c = STATE.customer;
  var sel = STATE.model;
  var branch = STATE.branch;
  var milesChk = STATE.miles >= 1 ? "checked" : "";

  // Build model dropdown: alphabetized presets + CUSTOM FLOOR PLAN pinned at bottom
  var options = '<option value="">— Select a model —</option>';
  CANONICAL_MODELS.forEach(function(m){
    var tkMark = isTurnkeyEligible(m) ? "" : "  (shell only)";
    options += '<option value="'+esc(m)+'"'+(m===sel?' selected':'')+'>'+esc(m)+tkMark+'</option>';
  });
  options += '<option value="CUSTOM FLOOR PLAN"'+(sel==="CUSTOM FLOOR PLAN"?' selected':'')+'>CUSTOM FLOOR PLAN</option>';

  // Branch dropdown
  var branchOpts = "";
  Object.keys(BRANCHES).forEach(function(k){
    branchOpts += '<option value="'+k+'"'+(k===branch?' selected':'')+'>'+esc(BRANCHES[k].label)+'</option>';
  });

  // Job scope toggle — disable Turnkey if model is ineligible
  var tkEligible = !sel || isTurnkeyEligible(sel);
  var shellActive = STATE.jobMode === "shell" ? " active" : "";
  var tkActive = STATE.jobMode === "turnkey" ? " active" : "";
  var tkDisabled = (sel && !tkEligible) ? " disabled" : "";
  var tkDisabledNote = (sel && !tkEligible)
    ? '<div class="scope-btn-note" style="font-size:10px;color:var(--amber-dark);margin-top:4px;font-style:italic">Interior turnkey not yet priced for this model</div>'
    : '';

  var h = '';
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Customer & Model</span><span class="badge">Step 1</span></div>';
  h +=   '<div class="customer-grid">';
  h +=     '<div class="field full"><label class="field-lbl">Customer Name</label><input class="inp" type="text" id="custName" placeholder="Enter customer name" value="'+esc(c.name)+'" oninput="onCustField(\'name\',this.value)"></div>';
  h +=     '<div class="field full"><label class="field-lbl">Sales Rep</label><input class="inp" type="text" id="custRep" placeholder="Sales rep name" value="'+esc(c.rep)+'" oninput="onCustField(\'rep\',this.value)"></div>';
  h +=     '<div class="field full"><label class="field-lbl">Address</label><div class="inline-row"><input class="inp" type="text" id="custAddr" placeholder="Street, City, State" value="'+esc(c.addr)+'" oninput="onCustField(\'addr\',this.value)"><label class="chk"><input type="checkbox" id="milesChk" '+milesChk+' onchange="onMilesToggle(this.checked)">&gt; 100 Miles</label></div></div>';
  h +=     '<div class="field"><label class="field-lbl">Order #</label><input class="inp" type="text" id="custOrder" placeholder="Order number" value="'+esc(c.order)+'" oninput="onCustField(\'order\',this.value)"></div>';
  h +=     '<div class="field"><label class="field-lbl">P10 Material Total</label><input class="inp mono num" type="text" id="custP10" inputmode="decimal" placeholder="$0" value="'+(c.p10>0?fmtC(c.p10):"")+'" oninput="onP10Input(this.value)" onblur="onP10Blur(this)"></div>';
  h +=     '<div class="field"><label class="field-lbl">Branch Location</label><select class="sel" id="branchSel" onchange="onBranchChange(this.value)">'+branchOpts+'</select></div>';
  h +=     '<div class="field"><label class="field-lbl">Model</label><select class="sel" id="modelSel" onchange="onModelChange(this.value)">'+options+'</select></div>';
  h +=   '</div>';
  h +=   '<div class="scope-wrap">';
  h +=     '<div class="field-lbl" style="margin-bottom:8px">Job Scope</div>';
  h +=     '<div class="scope-grid">';
  h +=       '<button class="scope-btn'+shellActive+'" onclick="setJobMode(\'shell\')">';
  h +=         '<div class="scope-title"><span class="scope-icon">🏗️</span>Shell Only</div>';
  h +=         '<div class="scope-sub">Exterior structure + concrete</div>';
  h +=       '</button>';
  h +=       '<button class="scope-btn'+tkActive+tkDisabled+'" '+(tkDisabled?'disabled':'')+' onclick="'+(tkDisabled?'':'setJobMode(\'turnkey\')')+'">';
  h +=         '<div class="scope-title"><span class="scope-icon">🏠</span>Turnkey Interior</div>';
  h +=         '<div class="scope-sub">Shell + full interior build</div>';
  h +=         tkDisabledNote;
  h +=       '</button>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // Empty state guidance
  if(!sel){
    h += '<div class="banner banner-empty">Select a model above to begin. Steps 2–4 unlock once a model is chosen.</div>';
  } else if(sel === "CUSTOM FLOOR PLAN"){
    h += '<div class="banner banner-info"><strong>Custom Floor Plan mode.</strong> All exterior and interior fields start blank — enter every value from your CAD drawings. '+(STATE.jobMode==="turnkey"?"Interior contract price uses the 30% reverse-margin formula on true build cost.":"")+'</div>';
  } else {
    var p = PM[sel] || {};
    var liv = 0;
    (MD[sel] && MD[sel].sqft || []).forEach(function(s){ if(s.n==="1st Floor Living Area"||s.n==="2nd Floor Area"||s.n==="Bonus Room") liv += s.sf; });
    var tkEl = isTurnkeyEligible(sel);
    h += '<div class="banner banner-info"><strong>'+esc(sel)+' loaded.</strong> '
      + (liv>0?('Living: <strong>'+$(liv)+' SF</strong> · '):'')
      + 'Stories: <strong>'+(p.st||1)+'</strong> · '
      + 'Ext Wall: <strong>'+$(p.ew||0)+' SF</strong> · '
      + 'P10 Material: <strong>'+fmt(P10[sel]||0)+'</strong>'
      + (tkEl?'':' · <em>Shell Only — no interior contract available</em>')+'</div>';
  }

  document.getElementById("stepContainer").innerHTML = h;
}

/* ═══════════════════════════════════════════════════════════════
   STEP 1 — EVENT HANDLERS
   ═══════════════════════════════════════════════════════════════ */
function onCustField(k, v){ STATE.customer[k] = v; scheduleSave(); }

function onMilesToggle(checked){
  STATE.miles = checked ? 1 : 0;
  refreshLiveTotals();
  scheduleSave();
}

function onP10Input(v){
  // Strip non-numeric chars on input; store raw number
  var raw = v.replace(/[^0-9.]/g, "");
  STATE.customer.p10 = pn(raw);
  renderRunningTotal();
  scheduleSave();
}
function onP10Blur(inp){
  // Format as currency on blur
  inp.value = STATE.customer.p10 > 0 ? fmtC(STATE.customer.p10) : "";
}

function onBranchChange(k){
  STATE.branch = k;
  var b = BRANCHES[k];
  if(b){
    // Auto-set miles from branch default (matches HTML V9: remote branches like
    // Morristown/Hopkinsville flip to "over 100 miles" contractor rates so the
    // ctr labor budget in Step 9 Part A comes out right). User can still
    // override via the "> 100 Miles" checkbox on Step 1.
    STATE.miles = b.miles || 0;
    STATE.conc.zone = b.zone || 1;
  }
  renderCurrentStep();
}

function onModelChange(m){
  if(!m){ STATE.model=""; STATE.int=null; renderCurrentStep(); return; }
  loadModel(m);
  renderCurrentStep();
}

function setJobMode(mode){
  if(__WIZ_LOCK_MODE && mode !== __WIZ_LOCK_MODE){
    showToast("This page is locked to " + __WIZ_LOCK_MODE + " mode.");
    return;
  }
  if(mode === STATE.jobMode) return;
  if(mode === "turnkey" && STATE.model && !isTurnkeyEligible(STATE.model)){
    showToast("Interior turnkey not yet priced for "+STATE.model);
    return;
  }
  STATE.jobMode = mode;
  // Snap step index back to Step 1 if we'd be past the new mode's length
  var ids = activeStepIds();
  if(STATE._stepIdx >= ids.length) STATE._stepIdx = 0;
  renderCurrentStep();
}

/* ═══════════════════════════════════════════════════════════════
   SHARED UI BUILDERS
   ═══════════════════════════════════════════════════════════════ */
function stepperHTML(id, qty, handler){
  // id is a dotted path into STATE (e.g. "ext.awnQty") — resolved by the handler.
  qty = pi(qty);
  return '<div class="est-qty-wrap">'
       +   '<button class="est-qty-btn" '+(qty<=0?'disabled':'')+' onclick="'+handler+'(\''+id+'\', -1)">−</button>'
       +   '<span class="est-qty-val">'+qty+'</span>'
       +   '<button class="est-qty-btn" onclick="'+handler+'(\''+id+'\', 1)">+</button>'
       + '</div>';
}

function resolvePdfSource(model){
  var entry = PDF_FILES[model];
  if(!entry) return null;

  if(typeof entry === "string"){
    if(/^https?:\/\//i.test(entry) || entry.charAt(0) === "/"){
      return {url: entry, filename: entry.split("/").pop()};
    }
    return {url: "pdfs/" + entry, filename: entry};
  }

  if(typeof entry === "object"){
    var url = entry.url || "";
    var filename = entry.filename || "";
    if(!url && filename){
      url = "pdfs/" + filename;
    }
    if(!url) return null;
    return {url: url, filename: filename || url.split("/").pop()};
  }

  return null;
}

function renderFloorPlanViewerCard(model, title){
  var src = resolvePdfSource(model);
  if(!src) return "";

  var fileLabel = src.filename || "floor-plan.pdf";
  var h = '';
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>'+esc(title || ("Floor Plan — " + model))+'</span>';
  h +=     '<a class="badge" style="cursor:pointer;border:none;background:rgba(255,255,255,.22);color:#fff;text-decoration:none" href="'+esc(src.url)+'" target="_blank" rel="noopener">Open in New Window ↗</a>';
  h +=   '</div>';
  h +=   '<iframe src="'+esc(src.url)+'" style="width:100%;height:75vh;border:none;display:block;background:var(--g100)"></iframe>';
  h +=   '<div style="padding:8px 14px;font-size:11px;color:var(--g500);background:var(--g50);border-top:1px solid var(--g200)">Viewing: <strong>'+esc(fileLabel)+'</strong>. If preview does not load, use Open in New Window.</div>';
  h += '</div>';
  return h;
}

function radioPillsHTML(groupName, options, current, handler){
  // options: [{v:"concrete", l:"Concrete"}, ...]
  return '<div class="radio-pills">'
       + options.map(function(o){
           var active = o.v === current ? ' active' : '';
           return '<button class="radio-pill'+active+'" onclick="'+handler+'(\''+groupName+'\', \''+o.v+'\')">'+esc(o.l)+'</button>';
         }).join('')
       + '</div>';
}

function yesNoSelectHTML(id, val, handler){
  // Yes=1, No=0. Handler takes the new numeric value.
  var v = val ? 1 : 0;
  return '<select class="sel" onchange="'+handler+'(\''+id+'\', parseInt(this.value,10))">'
       +   '<option value="0"'+(v===0?' selected':'')+'>No</option>'
       +   '<option value="1"'+(v===1?' selected':'')+'>Yes</option>'
       + '</select>';
}

/* Universal stepper handler — walks the dotted path into STATE */
function stepQty(path, delta){
  var parts = path.split('.');
  var obj = STATE;
  for(var i = 0; i < parts.length - 1; i++){ obj = obj[parts[i]]; }
  var key = parts[parts.length - 1];
  var cur = pi(obj[key]);
  var next = Math.max(0, cur + delta);
  obj[key] = next;
  renderCurrentStep();
}

/* Universal number-input handler — for SF / rate / qty inputs that update live */
function updNum(path, val){
  var parts = path.split('.');
  var obj = STATE;
  for(var i = 0; i < parts.length - 1; i++){ obj = obj[parts[i]]; }
  obj[parts[parts.length - 1]] = pn(val);
  // Light refresh — just recompute summaries and running total without full re-render
  refreshLiveTotals();
}

/* Universal text-input handler — for custom charge descriptions etc. */
function updText(path, val){
  var parts = path.split('.');
  var obj = STATE;
  for(var i = 0; i < parts.length - 1; i++){ obj = obj[parts[i]]; }
  obj[parts[parts.length - 1]] = val;
  scheduleSave();
}

/* Universal select handler — dropdowns that trigger structural changes get a re-render */
function updSelect(path, val){
  var parts = path.split('.');
  var obj = STATE;
  for(var i = 0; i < parts.length - 1; i++){ obj = obj[parts[i]]; }
  obj[parts[parts.length - 1]] = val;
  renderCurrentStep();
}

/* For text inputs that DON'T need re-render (descriptions, notes) */
function refreshLiveTotals(){
  renderRunningTotal();
  // Update any live-sum spans on the current step by ID
  document.querySelectorAll('[data-livesum]').forEach(function(el){
    var kind = el.getAttribute('data-livesum');
    el.textContent = liveSumText(kind);
  });
  scheduleSave();
}

function liveSumText(kind){
  switch(kind){
    case "livSF": return $(livSF())+" SF";
    case "garSF": return $(garSF())+" SF";
    case "porSF": return $(porSF())+" SF";
    case "carSF": return $(carSF())+" SF";
    case "tgSF":  return $(tgSF())+" SF";
    case "totSlab": return $(totSlab())+" SF";
    case "totRoof": return $(totRoof())+" SF";
    case "totEW": return $(totEW())+" SF";
    case "wallTuffSF": return $(pn(STATE.ext.wallTuff))+" SF";
    case "wallRockSF": return $(pn(STATE.ext.wallRock))+" SF";
    case "wallStoneSF": return $(pn(STATE.ext.wallStone))+" SF";
    case "totWin": return $(pn(STATE.ext.sglW)+pn(STATE.ext.dblW)+pn(STATE.ext.s2s)+pn(STATE.ext.s2d));
    case "sglW": return $(pn(STATE.ext.sglW));
    case "dblW": return $(pn(STATE.ext.dblW));
    case "s2s": return $(pn(STATE.ext.s2s));
    case "s2d": return $(pn(STATE.ext.s2d));
    case "totDoor": return $(pn(STATE.ext.sglD)+pn(STATE.ext.dblD));
    case "sglD": return $(pn(STATE.ext.sglD));
    case "dblD": return $(pn(STATE.ext.dblD));
    default: return "";
  }
}

/* ═══════════════════════════════════════════════════════════════
   STEP 2 — SLAB & FOUNDATION
   ═══════════════════════════════════════════════════════════════ */
function renderStep2(){
  var E = STATE.ext;
  var h = '';

  // ── SECTION: FOUNDATION TYPE ─────────────────────
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Foundation Type</span></div>';
  h +=   '<div class="sec">';
  h +=     radioPillsHTML('ext.foundType',
             [{v:"concrete",l:"Concrete"},{v:"crawl",l:"Crawlspace / Basement"}],
             E.foundType, 'updSelect');
  if(E.foundType === "crawl"){
    h +=     '<div style="margin-top:14px" class="field-row">';
    h +=       '<div class="field"><label class="field-lbl">Framing in Basement</label>'
             +   yesNoSelectHTML('ext.bsmtFrame', E.bsmtFrame, 'updSelect')
             + '</div>';
    h +=       '<div class="field"><label class="field-lbl">Crawlspace SF</label>'
             +   '<input class="inp mono num" type="number" min="0" value="'+(pn(E.crawlSF)||"")+'"'
             +   ' placeholder="'+$(livSF())+'" oninput="updNum(\'ext.crawlSF\', this.value)">'
             +   '<div class="field-hint">Defaults to Living SF. Billed at $3/SF = '+fmt(cSF(E)*3)+'</div>'
             + '</div>';
    h +=     '</div>';
  }
  h +=   '</div>';

  // ── SECTION: STORIES ─────────────────────────────
  h +=   '<div class="sec">';
  h +=     '<div class="sec-title"><span>Stories</span></div>';
  h +=     '<select class="sel" style="max-width:180px" onchange="onStoriesChange(parseFloat(this.value))">';
  [1, 1.5, 2].forEach(function(n){
    h +=     '<option value="'+n+'"'+(E.stories==n?' selected':'')+'>'+(n===1?"1 Story":(n===1.5?"1.5 Stories":"2 Stories"))+'</option>';
  });
  h +=     '</select>';
  if(E.stories > 1){
    h +=     '<div class="field-hint">Cascades to interior drywall (×1.15 story multiplier) on Step 9 budget.</div>';
  }
  h +=   '</div>';
  h += '</div>';

  // ── SECTION: SLAB SQFT SCHEDULE ──────────────────
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Slab SQFT Schedule</span><span class="badge" data-livesum="totSlab">'+$(totSlab())+' SF</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Living SQFT</div><div class="sum-val" data-livesum="livSF">'+$(livSF())+' SF</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Garage / Carport</div><div class="sum-val" data-livesum="garSF">'+$(garSF()+carSF())+' SF</div><div class="sum-sub">G: '+$(garSF())+' · C: '+$(carSF())+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Porch SQFT</div><div class="sum-val" data-livesum="porSF">'+$(porSF())+' SF</div></div>';
  h +=     '</div>';
  h +=     '<div class="row-table">';
  h +=       '<div class="row-hdr slab-row-hdr"><div>Area</div><div style="text-align:right">SF</div><div>T&G Ceiling</div><div></div></div>';
  E.slab.forEach(function(r, i){
    var isPorch = (r.n === "Front Porch Area" || r.n === "Back Porch Area");
    h +=       '<div class="row-line slab-row">';
    // Area dropdown
    h +=         '<select class="sel" onchange="onSlabRowArea('+i+', this.value)">';
    SA.forEach(function(a){ h += '<option value="'+esc(a)+'"'+(a===r.n?' selected':'')+'>'+esc(a)+'</option>'; });
    h +=         '</select>';
    // SF input
    h +=         '<input class="inp mono num" type="number" min="0" value="'+(pn(r.sf)||"")+'" oninput="onSlabRowSF('+i+', this.value)">';
    // T&G toggle (porch only)
    if(isPorch){
      h +=       '<select class="sel" onchange="onSlabRowTG('+i+', parseInt(this.value,10))">';
      h +=         '<option value="0"'+(!r.tg?' selected':'')+'>No</option>';
      h +=         '<option value="1"'+(r.tg?' selected':'')+'>Yes</option>';
      h +=       '</select>';
    } else {
      h +=       '<div style="text-align:center;color:var(--g400);font-family:var(--font-mono)">—</div>';
    }
    // Delete (disabled if only 1 row)
    h +=         '<button class="row-del" '+(E.slab.length<=1?'disabled':'')+' onclick="onSlabRowDelete('+i+')" title="Remove row">×</button>';
    h +=       '</div>';
  });
  h +=     '</div>';
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="onSlabRowAdd()">+ Add Area</button></div>';
  if(tgSF(E) > 0){
    h +=     '<div class="field-hint" style="margin-top:8px">T&G ceilings: '+$(tgSF())+' SF × $5/SF = '+fmt(tgSF()*P.sales.tg)+' customer charge</div>';
  }
  h +=   '</div>';
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function onStoriesChange(v){
  STATE.ext.stories = v;
  // Auto-add 2nd Floor Area row if stories > 1 and not already present
  if(v > 1){
    var has2nd = STATE.ext.slab.some(function(s){ return s.n === "2nd Floor Area"; });
    if(!has2nd){
      STATE.ext.slab.push({n:"2nd Floor Area", sf:0, tg:0});
    }
  }
  renderCurrentStep();
}

function onSlabRowArea(i, v){ STATE.ext.slab[i].n = v; renderCurrentStep(); }
function onSlabRowSF(i, v){ STATE.ext.slab[i].sf = pn(v); refreshLiveTotals(); }
function onSlabRowTG(i, v){ STATE.ext.slab[i].tg = v; refreshLiveTotals(); }
function onSlabRowAdd(){ STATE.ext.slab.push({n:"Custom", sf:0, tg:0}); renderCurrentStep(); }
function onSlabRowDelete(i){
  if(STATE.ext.slab.length <= 1) return;
  STATE.ext.slab.splice(i, 1);
  renderCurrentStep();
}

/* ═══════════════════════════════════════════════════════════════
   STEP 3 — ROOF & EXTERIOR
   ═══════════════════════════════════════════════════════════════ */
var ROOF_AREA_NAMES = __wizRequired("ROOF_AREA_NAMES");
var ROOF_TYPES = __wizRequired("ROOF_TYPES");

function renderStep3(){
  var E = STATE.ext;
  var h = '';
  var over100 = STATE.miles >= 1;

  // ══ ROOF SCHEDULE ══
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Roof Schedule</span><span class="badge" data-livesum="totRoof">'+$(totRoof())+' SF</span></div>';
  h +=   '<div class="sec">';
  // Roof summary boxes — dynamic per row
  h +=     '<div class="sum-grid">';
  E.roof.forEach(function(r){
    var typeLbl = (r.type==="ss"?" · SS":(r.type==="shingles"?" · Shingles":(r.steep?" · Steep":"")));
    h +=     '<div class="sum-box"><div class="sum-lbl">'+esc(r.n)+typeLbl+'</div><div class="sum-val">'+$(pn(r.sf))+' SF</div></div>';
  });
  h +=     '</div>';
  // Roof options (sheathing + 26ga)
  h +=     '<div class="field-row" style="margin-top:6px;margin-bottom:10px">';
  h +=       '<label class="chk"><input type="checkbox" '+(E.sheath?"checked":"")+' onchange="onExtToggle(\'sheath\', this.checked)">Add Sheathing'+(E.sheath?' <span class="live-cost">+'+fmt(baseSF(E)*0.5)+' ctr</span>':'')+'</label>';
  h +=       '<label class="chk"><input type="checkbox" '+(E.g26?"checked":"")+' onchange="onExtToggle(\'g26\', this.checked)">26 Gauge Roof</label>';
  h +=     '</div>';
  // Roof rows
  h +=     '<div class="row-table">';
  h +=       '<div class="row-hdr roof-row-hdr"><div>Area</div><div>Type</div><div>Pitch Tier</div><div style="text-align:right">SF</div><div></div></div>';
  E.roof.forEach(function(r, i){
    h +=     '<div class="row-line roof-row"'+(r.steep?' style="background:#FEF2F2"':'')+'>';
    // Area
    h +=       '<select class="sel" onchange="onRoofRowArea('+i+', this.value)">';
    ROOF_AREA_NAMES.forEach(function(a){ h += '<option value="'+esc(a)+'"'+(a===r.n?' selected':'')+'>'+esc(a)+'</option>'; });
    h +=       '</select>';
    // Type
    h +=       '<select class="sel" onchange="onRoofRowType('+i+', this.value)">';
    ROOF_TYPES.forEach(function(t){ h += '<option value="'+t.v+'"'+(t.v===r.type?' selected':'')+'>'+t.l+'</option>'; });
    h +=       '</select>';
    // Pitch tier
    h +=       '<select class="sel" onchange="onRoofRowSteep('+i+', parseInt(this.value,10))">';
    h +=         '<option value="0"'+(!r.steep?' selected':'')+'>7/12 or under</option>';
    h +=         '<option value="1"'+(r.steep?' selected':'')+'>8/12 or greater</option>';
    h +=       '</select>';
    // SF
    h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(r.sf)||"")+'" oninput="onRoofRowSF('+i+', this.value)">';
    // Delete
    h +=       '<button class="row-del" '+(E.roof.length<=1?'disabled':'')+' onclick="onRoofRowDelete('+i+')" title="Remove row">×</button>';
    h +=     '</div>';
  });
  h +=     '</div>';
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="onRoofRowAdd()">+ Add Roof Area</button></div>';
  h +=   '</div>';

  // ══ ROOF ADD-ONS ══
  h +=   '<div class="sec">';
  h +=     '<div class="sec-title"><span>Roof Add-Ons</span></div>';
  [
    {key:"awnQty", lbl:"Timber Framed Awnings", rate:P.sales.awning, unit:"ea"},
    {key:"cupQty", lbl:"Cupola Installation", rate:P.sales.cupola, unit:"ea"},
    {key:"chimQty",lbl:"Stone Chimney / Roofline Lifts", rate:P.sales.stoneLift, unit:"ea"}
  ].forEach(function(u){
    var q = pn(E[u.key]);
    h +=   '<div class="upg-row">';
    h +=     '<span class="upg-label">'+esc(u.lbl)+' ('+fmt(u.rate)+'/'+u.unit+')</span>';
    h +=     stepperHTML('ext.'+u.key, q, 'stepQty');
    h +=     '<span class="upg-cost'+(q===0?' zero':'')+'">'+(q===0?"—":fmt(q*u.rate))+'</span>';
    h +=   '</div>';
  });
  h +=   '</div>';
  h += '</div>';

  // ══ EXTERIOR WALL AREA ══
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Exterior Wall Area</span><span class="badge" data-livesum="totEW">'+$(totEW())+' SF</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Tuff Rib SF</div><div class="sum-val" data-livesum="wallTuffSF">'+$(pn(E.wallTuff))+' SF</div></div>';
  if(E.wainscotUpg){
    h +=     '<div class="sum-box"><div class="sum-lbl">Rock Wains SF</div><div class="sum-val" data-livesum="wallRockSF">'+$(pn(E.wallRock))+' SF</div></div>';
    h +=     '<div class="sum-box"><div class="sum-lbl">Stone Wains SF</div><div class="sum-val" data-livesum="wallStoneSF">'+$(pn(E.wallStone))+' SF</div></div>';
  }
  h +=     '</div>';
  h +=     '<div class="sec-title"><span>Wall Type</span></div>';
  h +=     radioPillsHTML('ext.wallType',
             [{v:"Metal",l:"Standard Metal (Tuff Rib)"},{v:"Board and Batten",l:"Board & Batten"},{v:"LP",l:"LP Siding"},{v:"Hardie Siding",l:"Hardie Siding"},{v:"Vinyl Siding",l:"Vinyl Siding"}],
             E.wallType, 'updSelect');
  h +=     '<div class="field-row" style="margin-top:14px">';
  h +=       '<div class="field"><label class="field-lbl">Exterior Wall Area (SF)</label>'
           +   '<input class="inp mono num" type="number" min="0" value="'+(pn(E.wallTuff)||"")+'" oninput="updNum(\'ext.wallTuff\', this.value)">'
           + '</div>';
  h +=       '<div class="field"><label class="field-lbl">Rock or Stone Wainscot</label>'
           +   yesNoSelectHTML('ext.wainscotUpg', E.wainscotUpg, 'updSelect')
           + '</div>';
  h +=     '</div>';
  if(E.wainscotUpg){
    h +=   '<div class="field-row">';
    h +=     '<div class="field"><label class="field-lbl">Rock Wainscot SF</label>'
           +   '<input class="inp mono num" type="number" min="0" value="'+(pn(E.wallRock)||"")+'" oninput="updNum(\'ext.wallRock\', this.value)">'
           + '</div>';
    h +=     '<div class="field"><label class="field-lbl">Stone Wainscot SF</label>'
           +   '<input class="inp mono num" type="number" min="0" value="'+(pn(E.wallStone)||"")+'" oninput="updNum(\'ext.wallStone\', this.value)">'
           + '</div>';
    h +=   '</div>';
  }
  h +=     '<div class="field-row">';
  h +=       '<div class="field"><label class="field-lbl">Stone Upgrade</label>'
           +   yesNoSelectHTML('ext.stoneUpg', E.stoneUpg, 'updSelect')
           + '</div>';
  if(E.stoneUpg){
    var stoneRate = over100 ? P.sales.stoneO : P.sales.stoneW;
    h +=     '<div class="field"><label class="field-lbl">Stone Area SF</label>'
           +   '<input class="inp mono num" type="number" min="0" value="'+(pn(E.wallStone)||"")+'" oninput="updNum(\'ext.wallStone\', this.value)">'
           +   '<div class="field-hint">'+fmt(stoneRate)+'/SF '+(over100?"(>100mi)":"(≤100mi)")+' = '+fmt(pn(E.wallStone)*stoneRate)+' customer charge</div>'
           + '</div>';
  }
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // ══ WINDOW SCHEDULE ══
  var totWin = pn(E.sglW)+pn(E.dblW)+pn(E.s2s)+pn(E.s2d);
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Window Schedule</span><span class="badge" data-livesum="totWin">'+$(totWin)+'</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Single</div><div class="sum-val" data-livesum="sglW">'+$(pn(E.sglW))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Double / Twin</div><div class="sum-val" data-livesum="dblW">'+$(pn(E.dblW))+'</div></div>';
  if(E.win12){
    h +=     '<div class="sum-box"><div class="sum-lbl">Single &gt; 12\'</div><div class="sum-val" data-livesum="s2s">'+$(pn(E.s2s))+'</div></div>';
    h +=     '<div class="sum-box"><div class="sum-lbl">Double &gt; 12\'</div><div class="sum-val" data-livesum="s2d">'+$(pn(E.s2d))+'</div></div>';
  }
  h +=     '</div>';
  [{key:"sglW",lbl:"Single Windows",rate:P.ctr.sglW},{key:"dblW",lbl:"Double / Twin Windows",rate:P.ctr.dblW}].forEach(function(w){
    var q = pn(E[w.key]);
    h +=   '<div class="upg-row">';
    h +=     '<span class="upg-label">'+esc(w.lbl)+'</span>';
    h +=     stepperHTML('ext.'+w.key, q, 'stepQty');
    h +=     '<span class="upg-cost zero">'+q+'</span>';
    h +=   '</div>';
  });
  h +=     '<div style="margin-top:10px"><div class="field"><label class="field-lbl">Windows Above 12\'</label>'
         +   yesNoSelectHTML('ext.win12', E.win12, 'updSelect')
         + '</div></div>';
  if(E.win12){
    [{key:"s2s",lbl:"Single Windows Above 12' (ground access only — no roof to stand on)"},
     {key:"s2d",lbl:"Double Windows Above 12'"}].forEach(function(w){
      var q = pn(E[w.key]);
      h += '<div class="upg-row">';
      h +=   '<span class="upg-label">'+esc(w.lbl)+'</span>';
      h +=   stepperHTML('ext.'+w.key, q, 'stepQty');
      h +=   '<span class="upg-cost zero">'+q+'</span>';
      h += '</div>';
    });
  }
  h +=   '</div>';
  h += '</div>';

  // ══ DOOR SCHEDULE ══
  var totDoor = pn(E.sglD)+pn(E.dblD);
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Door Schedule</span><span class="badge" data-livesum="totDoor">'+$(totDoor)+'</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Double Ext (6ft+)</div><div class="sum-val" data-livesum="dblD">'+$(pn(E.dblD))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Single Ext (3ft)</div><div class="sum-val" data-livesum="sglD">'+$(pn(E.sglD))+'</div></div>';
  h +=     '</div>';
  [{key:"dblD",lbl:"Double Ext Doors (6ft+)"},{key:"sglD",lbl:"Single Ext Doors (3ft)"}].forEach(function(d){
    var q = pn(E[d.key]);
    h +=   '<div class="upg-row">';
    h +=     '<span class="upg-label">'+esc(d.lbl)+'</span>';
    h +=     stepperHTML('ext.'+d.key, q, 'stepQty');
    h +=     '<span class="upg-cost zero">'+q+'</span>';
    h +=   '</div>';
  });
  h +=   '</div>';
  h += '</div>';

  // ══ PUNCH & CUSTOM CHARGES ══
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Punch & Custom Charges</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="field" style="max-width:260px"><label class="field-lbl">Punch Amount (min $'+$(P.punch)+')</label>'
         +   '<input class="inp mono num" type="number" min="'+P.punch+'" value="'+(pn(E.punchAmt)||P.punch)+'" oninput="onPunchInput(this.value)">'
         +   '<div class="field-hint">'+fmt(Math.max(P.punch, pn(E.punchAmt)))+' — added to customer contract</div>'
         + '</div>';
  h +=   '</div>';
  h +=   '<div class="sec">';
  h +=     '<div class="sec-title"><span>Custom Charges</span></div>';
  h +=     '<div class="row-table">';
  h +=       '<div class="row-hdr custom-row-hdr"><div>Description</div><div style="text-align:right">Rate</div><div>Unit</div><div style="text-align:right">Qty</div><div style="text-align:right">Cost</div><div></div></div>';
  E.customCharges.forEach(function(cc, i){
    var cost = pn(cc.rate)*pn(cc.qty);
    h +=     '<div class="row-line custom-row">';
    h +=       '<input class="inp" type="text" placeholder="Description" value="'+esc(cc.desc)+'" oninput="onCustChargeField('+i+', \'desc\', this.value)">';
    h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(cc.rate)||"")+'" placeholder="0" oninput="onCustChargeField('+i+', \'rate\', this.value)">';
    h +=       '<select class="sel" onchange="onCustChargeField('+i+', \'unit\', this.value)">';
    ["SF","LF","Each"].forEach(function(u){ h += '<option value="'+u+'"'+((cc.unit||"SF")===u?' selected':'')+'>'+u+'</option>'; });
    h +=       '</select>';
    h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(cc.qty)||"")+'" placeholder="0" oninput="onCustChargeField('+i+', \'qty\', this.value)">';
    h +=       '<div class="row-cost">'+(cost>0?fmt(cost):"—")+'</div>';
    h +=       '<button class="row-del" onclick="onCustChargeDelete('+i+')">×</button>';
    h +=     '</div>';
  });
  h +=     '</div>';
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="onCustChargeAdd()">+ Add Custom Charge</button></div>';
  h +=   '</div>';
  h += '</div>';

  // ══ ADDITIONAL FLAGS ══
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Additional Flags</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="field-row">';
  h +=       '<div class="field"><label class="field-lbl">Detached Shop / Garage</label>'
           +   yesNoSelectHTML('ext.detShop', E.detShop, 'updSelect')
           + '</div>';
  h +=       '<div class="field"><label class="field-lbl">Deck Shown on Plans</label>'
           +   yesNoSelectHTML('ext.deckShown', E.deckShown, 'updSelect')
           + '</div>';
  h +=     '</div>';
  if(E.detShop)    h += '<div class="banner banner-amber">Detached shop/garage flagged for contractor budget. Separate pricing to be added.</div>';
  if(E.deckShown)  h += '<div class="banner banner-amber">Deck flagged for contractor budget.</div>';
  h +=   '</div>';
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function onExtToggle(key, val){ STATE.ext[key] = val ? 1 : 0; renderCurrentStep(); }
function onRoofRowArea(i, v){ STATE.ext.roof[i].n = v; renderCurrentStep(); }
function onRoofRowType(i, v){ STATE.ext.roof[i].type = v; renderCurrentStep(); }
function onRoofRowSteep(i, v){ STATE.ext.roof[i].steep = v; renderCurrentStep(); }
function onRoofRowSF(i, v){ STATE.ext.roof[i].sf = pn(v); refreshLiveTotals(); }
function onRoofRowAdd(){ STATE.ext.roof.push({n:defaultRoofName(), steep:0, type:defaultRoofType(), sf:0}); renderCurrentStep(); }
function onRoofRowDelete(i){
  if(STATE.ext.roof.length <= 1) return;
  STATE.ext.roof.splice(i, 1);
  renderCurrentStep();
}
function onPunchInput(v){ STATE.ext.punchAmt = Math.max(P.punch, pn(v)); refreshLiveTotals(); }
function onCustChargeField(i, field, val){
  var cc = STATE.ext.customCharges[i];
  if(field === "desc" || field === "unit") cc[field] = val;
  else cc[field] = pn(val);
  if(field === "unit") renderCurrentStep(); else refreshLiveTotals();
}
function onCustChargeAdd(){
  STATE.ext.customCharges.push({desc:"", rate:0, unit:"SF", qty:0});
  renderCurrentStep();
}
function onCustChargeDelete(i){
  STATE.ext.customCharges.splice(i, 1);
  renderCurrentStep();
}

/* ═══════════════════════════════════════════════════════════════
   STEP 4 — CONCRETE
   ═══════════════════════════════════════════════════════════════ */
var CONC_TYPES = __wizRequired("CONC_TYPES");

function renderStep4(){
  var c = STATE.conc;
  var h = '';
  var cItems = buildConcItems();
  var cTotal = sumItems(cItems);
  var slabTot = totSlab();
  var sqftMismatch = (slabTot > 0 && pn(c.sqft) !== slabTot);

  h += '<div class="banner banner-info"><strong>Concrete.</strong> Customer-facing, pass-through pricing. All fields flow to the Contract total.</div>';

  // ── CONFIG ──
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Concrete Configuration</span>'
       +   (cTotal>0?'<span class="badge">'+fmt(cTotal)+'</span>':'')
       + '</div>';
  h +=   '<div class="sec">';
  h +=     '<div class="field-row">';
  h +=       '<div class="field" style="min-width:240px"><label class="field-lbl">Concrete Area (SF)</label>';
  h +=         '<div class="inline-row">';
  h +=           '<input class="inp mono num" type="number" min="0" value="'+(pn(c.sqft)||"")+'" oninput="updNum(\'conc.sqft\', this.value)">';
  if(slabTot > 0){
    h +=         '<button class="nav-btn" style="padding:7px 12px;font-size:12px" onclick="onConcUseSlab()">Use '+$(slabTot)+' SF</button>';
  }
  h +=         '</div>';
  if(sqftMismatch){
    h +=       '<div class="field-hint" style="color:var(--amber-dark)">⚠ Differs from slab total of '+$(slabTot)+' SF</div>';
  }
  h +=       '</div>';
  h +=       '<div class="field"><label class="field-lbl">Type</label>'
           +   '<select class="sel" onchange="updSelect(\'conc.type\', this.value)">';
  CONC_TYPES.forEach(function(t){ h += '<option value="'+t.v+'"'+(t.v===c.type?' selected':'')+'>'+esc(t.l)+'</option>'; });
  h +=         '</select></div>';
  h +=       '<div class="field"><label class="field-lbl">Zone</label>'
           +   '<select class="sel" onchange="onConcZone(parseInt(this.value,10))">';
  [1,2,3].forEach(function(z){
    var lbl = z===1?"Zone 1 (Middle TN)":(z===2?"Zone 2 (East & West TN)":"Zone 3 (KY & IN)");
    h +=         '<option value="'+z+'"'+(c.zone===z?' selected':'')+'>'+lbl+'</option>';
  });
  h +=         '</select></div>';
  h +=     '</div>';
  h +=     '<div class="field-row" style="margin-top:4px">';
  h +=       '<label class="chk"><input type="checkbox" '+(c.lp?"checked":"")+' onchange="onConcPump(\'lp\', this.checked)">Line Pump ($'+$(P.conc.lp)+')</label>';
  h +=       '<label class="chk"><input type="checkbox" '+(c.bp?"checked":"")+' onchange="onConcPump(\'bp\', this.checked)">Boom Pump ($'+$(P.conc.bp)+')</label>';
  h +=       '<label class="chk"><input type="checkbox" '+(c.wire?"checked":"")+' onchange="onConcFlag(\'wire\', this.checked)">Wire on 4\' Grid'
           + (c.wire && pn(c.sqft)>0 ? ' <span class="live-cost">+'+fmt(pn(c.sqft)*P.conc.wire)+'</span>' : '') + '</label>';
  h +=       '<label class="chk"><input type="checkbox" '+(c.rebar?"checked":"")+' onchange="onConcFlag(\'rebar\', this.checked)">Rebar on 4\' Grid'
           + (c.rebar && pn(c.sqft)>0 ? ' <span class="live-cost">+'+fmt(pn(c.sqft)*P.conc.rebar)+'</span>' : '') + '</label>';
  h +=     '</div>';
  h +=     '<div class="field-row">';
  h +=       '<div class="field" style="max-width:260px"><label class="field-lbl">2" Foam Perimeter (LF)</label>'
           +   '<input class="inp mono num" type="number" min="0" value="'+(pn(c.foam)||"")+'" oninput="updNum(\'conc.foam\', this.value)">'
           +   (pn(c.foam)>0 ? '<div class="field-hint">'+fmt(pn(c.foam)*P.conc.foam)+' = '+$(pn(c.foam))+' LF × '+fmt(P.conc.foam)+'/LF</div>' : '')
           + '</div>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // ── CUSTOM CONCRETE CHARGES ──
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Custom Concrete Charges</span></div>';
  h +=   '<div class="sec">';
  h +=     '<div class="row-table">';
  h +=       '<div class="row-hdr custom-row-hdr"><div>Description</div><div style="text-align:right">Rate</div><div>Unit</div><div style="text-align:right">Qty</div><div style="text-align:right">Cost</div><div></div></div>';
  (c.customCharges || []).forEach(function(cc, i){
    var cost = pn(cc.rate)*pn(cc.qty);
    h +=     '<div class="row-line custom-row">';
    h +=       '<input class="inp" type="text" placeholder="Description" value="'+esc(cc.desc)+'" oninput="onConcCustomField('+i+', \'desc\', this.value)">';
    h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(cc.rate)||"")+'" placeholder="0" oninput="onConcCustomField('+i+', \'rate\', this.value)">';
    h +=       '<select class="sel" onchange="onConcCustomField('+i+', \'unit\', this.value)">';
    ["SF","LF","Each"].forEach(function(u){ h += '<option value="'+u+'"'+((cc.unit||"SF")===u?' selected':'')+'>'+u+'</option>'; });
    h +=       '</select>';
    h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(cc.qty)||"")+'" placeholder="0" oninput="onConcCustomField('+i+', \'qty\', this.value)">';
    h +=       '<div class="row-cost" id="concCost_'+i+'">'+(cost>0?fmt(cost):"—")+'</div>';
    h +=       '<button class="row-del" onclick="onConcCustomDelete('+i+')">×</button>';
    h +=     '</div>';
  });
  h +=     '</div>';
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="onConcCustomAdd()">+ Add Custom Concrete Charge</button></div>';
  h +=   '</div>';
  h += '</div>';

  // ── SUMMARY (read-only) ──
  h += '<div id="concSummaryCard">';
  h += buildConcSummaryHTML(cItems, cTotal);
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function buildConcSummaryHTML(cItems, cTotal){
  if(!cItems || cItems.length === 0) return '';
  var h = '';
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Concrete Summary</span></div>';
  h +=   '<div class="sec" style="padding:0">';
  h +=     '<table class="ps-table">';
  h +=       '<thead><tr><th>Description</th><th style="text-align:right">Details</th><th style="text-align:right">Amount</th></tr></thead>';
  h +=       '<tbody>';
  cItems.forEach(function(it){
    h +=     '<tr><td>'+esc(it.label)+'</td><td class="num">'+$(it.qty)+' '+it.unit+' × '+fmtC(it.rate)+'</td><td class="cost">'+fmt(it.cost)+'</td></tr>';
  });
  h +=       '</tbody>';
  h +=     '</table>';
  h +=   '</div>';
  h +=   '<div style="padding:0 16px 16px"><div class="total-bar"><span class="total-lbl">Concrete Total</span><span class="total-val">'+fmt(cTotal)+'</span></div></div>';
  h += '</div>';
  return h;
}

function onConcUseSlab(){ STATE.conc.sqft = totSlab(); renderCurrentStep(); }
function onConcZone(v){ STATE.conc.zone = v; renderCurrentStep(); }
function onConcPump(which, checked){
  // Line/Boom pump are mutually exclusive
  if(checked){
    STATE.conc.lp = (which === "lp");
    STATE.conc.bp = (which === "bp");
  } else {
    STATE.conc[which] = false;
  }
  renderCurrentStep();
}
function onConcFlag(k, v){ STATE.conc[k] = !!v; renderCurrentStep(); }
function onConcCustomField(i, field, val){
  var cc = STATE.conc.customCharges[i];
  if(field === "desc" || field === "unit") cc[field] = val;
  else cc[field] = pn(val);
  if(field === "unit"){
    renderCurrentStep();
    return;
  }
  // Update cost cell in-place (no focus loss)
  if(field === "rate" || field === "qty"){
    var costEl = document.getElementById("concCost_"+i);
    if(costEl){
      var cost = pn(cc.rate) * pn(cc.qty);
      costEl.textContent = cost > 0 ? fmt(cost) : "—";
    }
    // Re-render the summary card in-place
    var summaryEl = document.getElementById("concSummaryCard");
    if(summaryEl){
      var cItems = buildConcItems();
      var cTotal = sumItems(cItems);
      summaryEl.innerHTML = buildConcSummaryHTML(cItems, cTotal);
    }
  }
  renderRunningTotal();
  scheduleSave();
}
function onConcCustomAdd(){
  STATE.conc.customCharges.push({desc:"", rate:0, unit:"SF", qty:0});
  renderCurrentStep();
}
function onConcCustomDelete(i){
  STATE.conc.customCharges.splice(i, 1);
  renderCurrentStep();
}

/* ═══════════════════════════════════════════════════════════════
   STEP 8 — CONTRACT (Shell mode: Part A + draw schedule; Turnkey: stub for later passes)
   ═══════════════════════════════════════════════════════════════ */
/* ═══════════════════════════════════════════════════════════════
   INTERIOR COMPUTE ENGINE (Step 5-9 foundation)
   ═══════════════════════════════════════════════════════════════ */

function initInteriorState(){
  // Lazy: called when Step 5 renders and STATE.int is null (fresh model load).
  var m = STATE.model;
  var pm = PLAN_METRICS[m] || {};
  var mdl = MODELS[m] || {};
  var isCustom = isCustomFloorPlan();
  var living = livSF();
  // Auto-estimate bedrooms from Living SF (spec §5)
  var autoBeds = living >= 2400 ? 4 : (living >= 1600 ? 3 : 2);
  // From PLAN_METRICS (fall back to sensible defaults for custom)
  var fullBaths = pi(pm["Bath Count"]) || (isCustom ? 0 : 2);
  var halfBaths = pi(pm["Half Bath Count"]) || 0;
  var doors = pi(pm["Interior Slabs"]) || (isCustom ? 0 : 12);
  // Custom Floor Plan starts all CAD fields at zero so the user enters them fresh.
  var cabLF = isCustom ? 0 : pn(mdl.cabinetryLFNum);
  var islandDepth = isCustom ? 0 : pn(mdl.island && mdl.island.depth);
  var islandWidth = isCustom ? 0 : pn(mdl.island && mdl.island.width);

  STATE.int = {
    bedrooms: autoBeds,
    fullBaths: fullBaths,
    halfBaths: halfBaths,
    fixtures: fullBaths * 2 + halfBaths * 2 + 4,
    closetQty: autoBeds,
    doors: doors,
    laundrySink: 1,    // default yes
    cabLF: cabLF,
    islandDepth: islandDepth,
    islandWidth: islandWidth,
    islandAddon: "",
    applianceConfig: "standard_range_mw",
    // Computed metrics — populated by applyIntMetrics() next
    counterSF: 0, flooringSF: 0, trimLF: 0, drywallSF: 0,
    dwSheets: 0, paintSF: 0, hvacTons: 0, insulationSF: 0
  };
  applyIntMetrics();
}

function buildIntMetrics(S){
  // Pure function: returns the derived metrics object given current STATE.
  S = S || STATE;
  var I = S.int || {};
  var living = livSF(S.ext);
  var stories = pn(S.ext.stories) || 1;
  var fullBaths = pi(I.fullBaths);
  var halfBaths = pi(I.halfBaths);
  var doors = pi(I.doors);
  var cabLF = pn(I.cabLF);
  var storyMult = stories > 1 ? 1.15 : 1.0;
  // Fixture formula per user directive: (full×2) + (half×2) + 4
  var fixtures = fullBaths * 2 + halfBaths * 2 + 4;
  return {
    fixtures: fixtures,
    counterSF: Math.round(cabLF * 2),
    flooringSF: Math.round(living * 0.82),
    trimLF: Math.round(living * 0.286),
    drywallSF: Math.round((living * 2.4 + doors * 50 + fullBaths * 100 + halfBaths * 50) * storyMult * 1.05),
    dwSheets: Math.ceil((living * 2.4 + doors * 50 + fullBaths * 100 + halfBaths * 50) * storyMult * 1.05 / 32),
    paintSF: Math.round(living * 4.057),
    hvacTons: Math.ceil((living / 700) * 2) / 2,
    insulationSF: living
  };
}

function applyIntMetrics(){
  // Mutates STATE.int with the recomputed metrics (fixtures + all derived fields).
  if(!STATE.int) return;
  var m = buildIntMetrics(STATE);
  Object.keys(m).forEach(function(k){ STATE.int[k] = m[k]; });
}

function computeCadCharges(S){
  // Returns an array of CAD-based charge items: [{label, cost, trade}, ...]
  // Behavior differs for preset vs. custom:
  //   Preset: delta-based (only charges if modified > standard)
  //   Custom: full-entered charges (no standard to subtract against)
  S = S || STATE;
  if(!S.int) return [];
  var m = S.model;
  var mdl = MODELS[m] || {};
  var isCustom = isCustomFloorPlan();
  var charges = [];

  // Cabinet LF
  var stdLF = isCustom ? 0 : pn(mdl.cabinetryLFNum);
  var modLF = pn(S.int.cabLF);
  if(isCustom){
    if(modLF > 0) charges.push({label:"Cabinet LF — "+modLF.toFixed(1)+" LF × $330", cost: Math.round(modLF * 330), trade:"cabinets"});
  } else {
    var deltaLF = modLF - stdLF;
    if(deltaLF > 1){
      charges.push({label:"Added Cabinet LF — "+deltaLF.toFixed(1)+" LF × $330", cost: Math.round(deltaLF * 330), trade:"cabinets"});
    }
  }

  // Island SF
  var stdD = isCustom ? 0 : pn(mdl.island && mdl.island.depth);
  var stdW = isCustom ? 0 : pn(mdl.island && mdl.island.width);
  var modD = pn(S.int.islandDepth);
  var modW = pn(S.int.islandWidth);
  var stdIslandSF = stdD * stdW;
  var modIslandSF = modD * modW;
  if(isCustom){
    if(modIslandSF > 0){
      charges.push({label:"Island — "+modIslandSF+" SF × $225", cost: Math.round(modIslandSF * 225), trade:"cabinets"});
    }
  } else {
    var deltaSF = modIslandSF - stdIslandSF;
    if(deltaSF > 0){
      charges.push({label:"Enlarged Island — "+deltaSF+" SF × $225", cost: Math.round(deltaSF * 225), trade:"cabinets"});
    }
  }

  // Island add-ons
  var addon = S.int.islandAddon;
  if(addon === "sink" || addon === "sink_microwave"){
    charges.push({label:"Sink in Island", cost:500, trade:"plumbing"});
  }
  if(addon === "microwave" || addon === "sink_microwave"){
    charges.push({label:"Microwave in Island", cost:500, trade:"cabinets"});
  }

  // Appliance config upgrade
  var appCost = APPLIANCE_COSTS[S.int.applianceConfig] || 0;
  if(appCost > 0){
    charges.push({label:APPLIANCE_LABELS[S.int.applianceConfig] || "Appliance upgrade", cost: appCost, trade:"cabinets"});
  }

  return charges;
}

// Interior trade groups that drive Step 9 base budget calculations.
var INT_TRADE_GROUPS = __wizRequired("INT_TRADE_GROUPS");

function calcIntTradeBase(tg, S){
  // Sum of (rate × driver) for every rate in the trade group.
  S = S || STATE;
  var I = S.int || {};
  var drivers = {
    livingSF: livSF(S.ext),
    cabLF: pn(I.cabLF),
    counterSF: pn(I.counterSF),
    drywallSF: pn(I.drywallSF),
    trimLF: pn(I.trimLF),
    doors: pn(I.doors),
    bathCount: pi(I.fullBaths) + pi(I.halfBaths),
    fixtures: pn(I.fixtures) + getSelectionFixturePoints(S),
    hvacTons: pn(I.hvacTons),
    flat: 1
  };
  var total = 0;
  (tg.rates || []).forEach(function(rk){
    var r = INT_RC[rk];
    if(!r) return;
    var q = drivers[r.driver] || 0;
    total += r.rate * q;
  });
  return total;
}

function getSelectionFixturePoints(S){
  // Sums fixture points from Pill 3 plumbing stubs (items with fp property)
  S = S || STATE;
  if(!S.sel || !S.sel.plumbing) return 0;
  var sel = S.sel.plumbing;
  var defs = SEL_DEFS.plumbing;
  if(!defs) return 0;
  var total = 0;
  defs.sections.forEach(function(sec){
    (sec.items || []).forEach(function(it){
      if(!it.fp) return;
      if(it.type === "toggle" && sel.toggles && sel.toggles[it.id]) total += it.fp;
      if(it.type === "qty" && sel.qtys) total += pi(sel.qtys[it.id]) * it.fp;
    });
  });
  return total;
}

// computeInteriorTrueCost and computeInteriorContractPrice are defined below in Step 6's compute engine.

/* ═══════════════════════════════════════════════════════════════
   STEP 5 — INTERIOR SELECTIONS
   Zones A (read-only from ext) + B (editable metrics) + C (standard ref) + D (CAD entries)
   + PDF viewer + live CAD charges preview + computed metrics readout.
   ═══════════════════════════════════════════════════════════════ */

function renderStep5(){
  // Initialize interior state on first visit, else recompute metrics from current STATE.int
  if(!STATE.int) initInteriorState();
  else applyIntMetrics();

  var m = STATE.model;
  var mdl = MODELS[m] || {};
  var pm = PLAN_METRICS[m] || {};
  var isCustom = isCustomFloorPlan();
  var I = STATE.int;
  var h = '';

  // ── PDF VIEWER (top) ──────────────────────────────
  h += renderFloorPlanViewerCard(m, "Floor Plan — " + m);

  // ── ZONE A: CAD-DRIVEN SCHEDULE (read-only) ───────
  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Zone A · CAD-Driven Schedule</span><span class="badge">from Steps 2–3</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Living SF</div><div class="sum-val">'+$(livSF())+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Garage + Carport</div><div class="sum-val">'+$(garSF()+carSF())+'</div><div class="sum-sub">G:'+$(garSF())+' · C:'+$(carSF())+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Porch SF</div><div class="sum-val">'+$(porSF())+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Stories</div><div class="sum-val">'+STATE.ext.stories+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Ext Wall SF</div><div class="sum-val">'+$(pn(STATE.ext.wallTuff))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Windows</div><div class="sum-val">'+$(pn(STATE.ext.sglW)+pn(STATE.ext.dblW)+pn(STATE.ext.s2s)+pn(STATE.ext.s2d))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Ext Doors</div><div class="sum-val">'+$(pn(STATE.ext.sglD)+pn(STATE.ext.dblD))+'</div></div>';
  h +=     '</div>';
  // Feature flags
  var flags = [];
  if(pm["Has Stairs"] === "Yes" || pn(STATE.ext.stories) > 1) flags.push("Stairs");
  if(pm["Has Fireplace"] === "Yes") flags.push("Fireplace");
  if(pm["Has Loft/Bonus"] === "Yes" || bonSF() > 0) flags.push("Loft / Bonus");
  if(flags.length > 0){
    h +=   '<div style="margin-top:12px">';
    flags.forEach(function(f){ h += '<span class="feat-chip">✓ '+esc(f)+'</span>'; });
    h +=   '</div>';
  }
  h +=   '</div>';
  h += '</div>';

  // ── ZONE B: INTERIOR PLAN METRICS (editable) ──────
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Zone B · Interior Plan Metrics (editable)</span></div>';
  h +=   '<div class="card-pad">';
  var metricFields = [
    {k:"bedrooms",  lbl:"Bedrooms",                hint:"Auto-estimated from Living SF — editable"},
    {k:"fullBaths", lbl:"Full Bathrooms",          hint:"From plan. Cascades to fixture points."},
    {k:"halfBaths", lbl:"Half Bathrooms",          hint:"From plan. Cascades to fixture points."},
    {k:"fixtures",  lbl:"Plumbing Fixture Points", hint:"Auto: fullBaths×2 + halfBaths×2 + 4 · override if needed"},
    {k:"closetQty", lbl:"Bedroom Closet Qty",      hint:"Defaults to bedroom count · drives closet rod budget"},
    {k:"doors",     lbl:"Interior Door Count",      hint:"Interior door slabs (prehung)"},
    {k:"laundrySink", lbl:"Laundry Sink Qty",      hint:"0 = no sink · 1 = laundry sink present"}
  ];
  metricFields.forEach(function(f){
    h += '<div class="upg-row">';
    h +=   '<span class="upg-label"><strong>'+esc(f.lbl)+'</strong>'
         +   (f.hint?' <span style="font-size:11px;color:var(--g500);margin-left:6px">· '+esc(f.hint)+'</span>':'')
         + '</span>';
    h +=   stepperHTML('int.'+f.k, pi(I[f.k]), 'stepIntMetric');
    h += '</div>';
  });
  h +=   '</div>';
  h += '</div>';

  // ── ZONE C: STANDARD PLAN (reference, read-only) ───
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Zone C · Standard Plan (reference)</span></div>';
  h +=   '<div class="card-pad">';
  if(isCustom){
    h += '<div class="banner banner-info"><strong>Custom Floor Plan.</strong> No preset baseline exists — enter all cabinet &amp; island values in Zone D from the CAD drawings. Cabinet charge = entered LF × $330; island charge = entered SF × $225.</div>';
  } else {
    h += '<div class="field-row">';
    h +=   '<div class="field"><label class="field-lbl">Standard Cabinet LF</label><div class="metric-readout">'+esc(mdl.cabinetryLF || "—")+' ('+(pn(mdl.cabinetryLFNum) || 0)+' LF)</div></div>';
    h +=   '<div class="field"><label class="field-lbl">Standard Island</label><div class="metric-readout">'+esc((mdl.island && mdl.island.label) || "—")+'</div></div>';
    h += '</div>';
  }
  h +=   '</div>';
  h += '</div>';

  // ── ZONE D: MODIFIED CAD ENTRIES ──────────────────
  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Zone D · Modified CAD Entries</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="field-row">';
  h +=       '<div class="field"><label class="field-lbl">Modified Cabinet LF</label>'
         +     '<input class="inp mono num" type="number" step="0.25" min="0" value="'+(pn(I.cabLF)||"")+'" oninput="updIntNum(\'cabLF\', this.value)">'
         +   '</div>';
  h +=       '<div class="field"><label class="field-lbl">Island Depth (ft)</label>'
         +     '<input class="inp mono num" type="number" step="0.5" min="0" value="'+(pn(I.islandDepth)||"")+'" oninput="updIntNum(\'islandDepth\', this.value)">'
         +   '</div>';
  h +=       '<div class="field"><label class="field-lbl">Island Width (ft)</label>'
         +     '<input class="inp mono num" type="number" step="0.5" min="0" value="'+(pn(I.islandWidth)||"")+'" oninput="updIntNum(\'islandWidth\', this.value)">'
         +   '</div>';
  h +=     '</div>';
  h +=     '<div class="field-row">';
  h +=       '<div class="field"><label class="field-lbl">Island Add-ons</label>'
         +     '<select class="sel" onchange="updIntSelect(\'int.islandAddon\', this.value)">'
         +       '<option value=""'+(I.islandAddon===""?' selected':'')+'>None</option>'
         +       '<option value="microwave"'+(I.islandAddon==="microwave"?' selected':'')+'>Microwave in Island ($500)</option>'
         +       '<option value="sink"'+(I.islandAddon==="sink"?' selected':'')+'>Sink in Island ($500)</option>'
         +       '<option value="sink_microwave"'+(I.islandAddon==="sink_microwave"?' selected':'')+'>Sink + Microwave ($1,000)</option>'
         +     '</select>'
         +   '</div>';
  h +=       '<div class="field"><label class="field-lbl">Appliance Configuration</label>'
         +     '<select class="sel" onchange="updIntSelect(\'int.applianceConfig\', this.value)">';
  Object.keys(APPLIANCE_LABELS).forEach(function(key){
    var cost = APPLIANCE_COSTS[key] || 0;
    h +=         '<option value="'+key+'"'+(I.applianceConfig===key?' selected':'')+'>'+esc(APPLIANCE_LABELS[key])+(cost>0?' (+'+fmt(cost)+')':'')+'</option>';
  });
  h +=         '</select></div>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // ── CAD CHARGES PREVIEW (live-updating) ──────────
  var charges = computeCadCharges();
  var cadTotal = charges.reduce(function(a,c){ return a+c.cost; }, 0);
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>CAD-Based Charges (auto-computed)</span>'
       +   '<span class="badge" id="cadChargesBadge">'+fmt(cadTotal)+'</span>'
       + '</div>';
  h +=   '<div class="card-pad" id="cadChargesPreview">'+renderCadChargesInline()+'</div>';
  h += '</div>';

  // ── COMPUTED METRICS READOUT (for reference; editable on Step 9) ──
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Computed Metrics</span><span class="badge">edit on Step 9 Budget if needed</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Countertop SF</div><div class="sum-val">'+$(I.counterSF)+'</div><div class="sum-sub">Cab LF × 2</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Flooring SF</div><div class="sum-val">'+$(I.flooringSF)+'</div><div class="sum-sub">Living × 0.82</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Trim LF</div><div class="sum-val">'+$(I.trimLF)+'</div><div class="sum-sub">Living × 0.286</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Drywall SF</div><div class="sum-val">'+$(I.drywallSF)+'</div><div class="sum-sub">'+I.dwSheets+' sheets</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Paint SF</div><div class="sum-val">'+$(I.paintSF)+'</div><div class="sum-sub">Living × 4.057</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">HVAC Tons</div><div class="sum-val">'+I.hvacTons.toFixed(1)+'</div><div class="sum-sub">Living ÷ 700 → 0.5</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Insulation SF</div><div class="sum-val">'+$(I.insulationSF)+'</div><div class="sum-sub">= Living SF</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Fixture Points</div><div class="sum-val">'+I.fixtures+'</div><div class="sum-sub">full×2 + half×2 + 4</div></div>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function renderCadChargesInline(){
  var charges = computeCadCharges();
  if(charges.length === 0){
    return '<div style="color:var(--g500);font-size:13px;padding:8px 0">No CAD-based charges yet. Modify Cabinet LF, Island dimensions, Add-ons, or Appliance Config above to see charges here.</div>';
  }
  var h = '';
  var total = 0;
  charges.forEach(function(c){
    total += c.cost;
    h += '<div class="upg-row cad-row">';
    h +=   '<span class="upg-label"><strong>'+esc(c.label)+'</strong> <span style="font-size:11px;color:var(--amber-dark);opacity:.8">→ '+esc(c.trade)+'</span></span>';
    h +=   '<span class="upg-cost">'+fmt(c.cost)+'</span>';
    h += '</div>';
  });
  h += '<div class="total-bar total-bar-sm" style="background:#78350F;margin-top:10px"><span class="total-lbl">CAD Charges Subtotal</span><span class="total-val">'+fmt(total)+'</span></div>';
  return h;
}

/* Step 5 handlers */
function stepIntMetric(path, delta){
  var key = path.split('.')[1];
  var cur = pi(STATE.int[key]);
  var next = Math.max(0, cur + delta);
  if(key === "laundrySink") next = Math.min(1, next);
  STATE.int[key] = next;
  // Cascade: full/half baths → fixture points (unless user manually overrode fixtures)
  if(key === "fullBaths" || key === "halfBaths"){
    STATE.int.fixtures = STATE.int.fullBaths * 2 + STATE.int.halfBaths * 2 + 4;
  }
  applyIntMetrics();
  renderCurrentStep();
}

function updIntNum(key, val){
  // For cabLF / islandDepth / islandWidth — these affect CAD charges live.
  STATE.int[key] = pn(val);
  applyIntMetrics();
  // Light refresh: don't re-render (would lose input focus). Update CAD preview + header.
  var preview = document.getElementById("cadChargesPreview");
  if(preview) preview.innerHTML = renderCadChargesInline();
  var badge = document.getElementById("cadChargesBadge");
  if(badge){
    var tot = computeCadCharges().reduce(function(a,c){ return a+c.cost; }, 0);
    badge.textContent = fmt(tot);
  }
  refreshLiveTotals();
}

function updIntSelect(path, val){
  var key = path.split('.')[1];
  STATE.int[key] = val;
  applyIntMetrics();
  renderCurrentStep();
}

/* ═══════════════════════════════════════════════════════════════
   STEP 6 — CABINETS & COUNTERTOPS (full implementation)
   ═══════════════════════════════════════════════════════════════ */

function initCabUpgradesState(){
  // Idempotent: fills in missing fields without overwriting existing ones.
  // Safe to call every render, which self-heals state from old autosaves / imports.
  if(!STATE.cabUpgrades) STATE.cabUpgrades = {};
  var cu = STATE.cabUpgrades;
  if(!cu.doorStyle) cu.doorStyle = {kitchen:"", island:"", laundry:"", baths:"", other:""};
  ["kitchen","island","laundry","baths","other"].forEach(function(a){
    if(cu.doorStyle[a] === undefined) cu.doorStyle[a] = "";
  });
  if(!Array.isArray(cu.customCraftRows)) cu.customCraftRows = [];
  if(!cu.kitchen) cu.kitchen = {};
  ["doorsToDrawers","fridgePanel","hoodVent","tallPantry","lazySusan"].forEach(function(k){
    if(cu.kitchen[k] === undefined) cu.kitchen[k] = 0;
  });
  if(!cu.inserts) cu.inserts = {};
  ["pullOut","drawerRoll","custom"].forEach(function(k){
    if(!cu.inserts[k]) cu.inserts[k] = {qty:0, note:""};
    else {
      if(cu.inserts[k].qty === undefined) cu.inserts[k].qty = 0;
      if(cu.inserts[k].note === undefined) cu.inserts[k].note = "";
    }
  });
  if(!cu.laundry) cu.laundry = {uppersWD:0, tallCab:0};
  else {
    if(cu.laundry.uppersWD === undefined) cu.laundry.uppersWD = 0;
    if(cu.laundry.tallCab === undefined) cu.laundry.tallCab = 0;
  }
  if(!cu.bath) cu.bath = {drawerVanity:0, tallLinen:0, makeupSeat:0};
  else {
    ["drawerVanity","tallLinen","makeupSeat"].forEach(function(k){
      if(cu.bath[k] === undefined) cu.bath[k] = 0;
    });
  }
  // Section 7 Part A (restructured): repeatable area rows with type dropdown + LF
  if(!Array.isArray(cu.customRows)) cu.customRows = [];
  // Migrate legacy customLF{uppersLowers, lowersOnly} → customRows if present
  if(cu.customLF){
    var ul = pn(cu.customLF.uppersLowers);
    var lo = pn(cu.customLF.lowersOnly);
    if(ul > 0) cu.customRows.push({area:"(migrated)", type:"uppersLowers", lf:ul});
    if(lo > 0) cu.customRows.push({area:"(migrated)", type:"lowersOnly", lf:lo});
    delete cu.customLF;
  }
  if(!Array.isArray(cu.customLines)) cu.customLines = [];
  if(cu.discount === undefined) cu.discount = 0;
  if(!STATE.ct) STATE.ct = {areas:[], notes:""};
  if(!Array.isArray(STATE.ct.areas)) STATE.ct.areas = [];
  if(STATE.ct.notes === undefined) STATE.ct.notes = "";
}

function computeCabSections(S){
  S = S || STATE;
  var cu = S.cabUpgrades;
  if(!cu) return {planCharges:0, doorStyleTotal:0, customCraftTotal:0, kitchenTotal:0, insertsTotal:0, laundryTotal:0, bathTotal:0, customTotal:0, discount:0, upgradesSubtotal:0, cabSummaryTotal:0};

  var m = S.model;
  var cr = CRAFTSMAN[m] || {paint:{}, stain:{}};

  var planCharges = 0;
  computeCadCharges(S).forEach(function(c){ planCharges += c.cost; });

  var doorStyleTotal = 0;
  ["kitchen","island","laundry","baths","other"].forEach(function(area){
    var f = cu.doorStyle[area];
    if(f === "paint") doorStyleTotal += pn(cr.paint && cr.paint[area]);
    else if(f === "stain") doorStyleTotal += pn(cr.stain && cr.stain[area]);
  });

  var customCraftTotal = 0;
  (cu.customCraftRows || []).forEach(function(r){
    var rate = r.finish === "stain" ? 45 : (r.finish === "paint" ? 35 : 0);
    customCraftTotal += pn(r.lf) * rate;
  });

  var k = cu.kitchen;
  var kitchenTotal = pi(k.doorsToDrawers)*250 + pi(k.fridgePanel)*350
                   + (k.hoodVent?2200:0) + (k.tallPantry?1200:0) + (k.lazySusan?850:0);

  var i = cu.inserts;
  var insertsTotal = pi(i.pullOut.qty)*350 + pi(i.drawerRoll.qty)*275 + pi(i.custom.qty)*500;

  var laundryTotal = (cu.laundry.uppersWD?1250:0) + (cu.laundry.tallCab?1200:0);

  var b = cu.bath;
  var bathTotal = pi(b.drawerVanity)*350 + pi(b.tallLinen)*1250 + pi(b.makeupSeat)*350;

  // Section 7 — Custom (per-area cabinetry rows + free-form line items)
  var customTotal = 0;
  (cu.customRows || []).forEach(function(r){
    var rate = r.type === "uppersLowers" ? 450 : (r.type === "lowersOnly" ? 350 : 0);
    customTotal += rate * pn(r.lf);
  });
  (cu.customLines || []).forEach(function(r){ customTotal += pn(r.amount); });

  var discount = pn(cu.discount);
  var upgradesSubtotal = doorStyleTotal + customCraftTotal + kitchenTotal + insertsTotal + laundryTotal + bathTotal + customTotal - discount;
  var cabSummaryTotal = planCharges + upgradesSubtotal;

  return {
    planCharges: planCharges, doorStyleTotal: doorStyleTotal, customCraftTotal: customCraftTotal,
    kitchenTotal: kitchenTotal, insertsTotal: insertsTotal, laundryTotal: laundryTotal,
    bathTotal: bathTotal, customTotal: customTotal, discount: discount,
    upgradesSubtotal: upgradesSubtotal, cabSummaryTotal: cabSummaryTotal
  };
}

function computeCtSections(S){
  S = S || STATE;
  if(!S.ct || !S.int) return {planCharge:0, areaUpgradesTotal:0, upgradesSubtotal:0, ctSummaryTotal:0, addedSF:0, stdSF:0, modSF:0};

  var m = S.model;
  var mdl = MODELS[m] || {};
  var isCustom = isCustomFloorPlan();

  var modCabLF = pn(S.int.cabLF);
  var modIsland = pn(S.int.islandDepth) * pn(S.int.islandWidth);
  var modSF = modCabLF * 2 + modIsland;
  var stdCabLF = isCustom ? 0 : pn(mdl.cabinetryLFNum);
  var stdIsland = isCustom ? 0 : (pn(mdl.island && mdl.island.depth) * pn(mdl.island && mdl.island.width));
  var stdSF = stdCabLF * 2 + stdIsland;
  var addedSF = Math.max(0, modSF - stdSF);
  var planCharge = isCustom ? 0 : Math.round(addedSF * 50);

  var areaUpgradesTotal = 0;
  (S.ct.areas || []).forEach(function(r){
    areaUpgradesTotal += pn(r.rate) * pn(r.sqft);
  });

  var upgradesSubtotal = areaUpgradesTotal;
  var ctSummaryTotal = planCharge + areaUpgradesTotal;

  return {
    planCharge: planCharge, areaUpgradesTotal: areaUpgradesTotal,
    upgradesSubtotal: upgradesSubtotal, ctSummaryTotal: ctSummaryTotal,
    addedSF: addedSF, stdSF: stdSF, modSF: modSF
  };
}

function getInteriorUpgradesTotal(S){
  // Customer-price sum of Step 6 cabinet + countertop + Step 7 selection upgrades (NOT credits).
  var cab = computeCabSections(S).upgradesSubtotal;
  var ct  = computeCtSections(S);
  var ctTotal = isCustomFloorPlan() ? ct.upgradesSubtotal : (ct.planCharge + ct.upgradesSubtotal);
  var sel = getSelectionsUpgradesTotal(S);
  return cab + ctTotal + sel;
}

function getInteriorCreditsTotal(S){
  S = S || STATE;
  if(!S.sel || !S.sel.custom) return 0;
  var total = 0;
  (S.sel.custom.credits || []).forEach(function(r){ total += pn(r.amount); });
  return total;
}

function getEffectiveCredits(S){
  // Per spec: adjusted INT can never fall below the model's standard turnkey adder.
  // Cap credits at total upgrades so base INT stays intact.
  var upgrades = getInteriorUpgradesTotal(S);
  return Math.min(getInteriorCreditsTotal(S), upgrades);
}

function computeInteriorTrueCost(S){
  // Base trade costs + CAD×0.80 + upgrades×0.80 - effectiveCredits.
  // For custom floor plans, cabinet CAD charges are excluded from true cost.
  S = S || STATE;
  if(!S.int) return 0;
  var total = 0;
  var custom = isCustomFloorPlan();
  INT_TRADE_GROUPS.forEach(function(tg){ total += calcIntTradeBase(tg, S); });
  computeCadCharges(S).forEach(function(c){
    if(custom && c.trade === "cabinets") return;
    total += c.cost * 0.80;
  });
  total += getInteriorUpgradesTotal(S) * 0.80;
  total -= getEffectiveCredits(S);
  return Math.max(0, total);
}

function computeInteriorContractPrice(S){
  S = S || STATE;
  if(!S.model) return 0;
  var upgrades = getInteriorUpgradesTotal(S);
  var effectiveCredits = getEffectiveCredits(S);
  if(isCustomFloorPlan()){
    // Custom: reverse-margin non-cabinet true cost, then add cabinet CAD flat customer charge.
    var trueCostNoCredit = 0;
    var flatCabCharge = 0;
    INT_TRADE_GROUPS.forEach(function(tg){
      if(tg.key === "cabinets") return;
      trueCostNoCredit += calcIntTradeBase(tg, S);
    });
    computeCadCharges(S).forEach(function(c){
      if(c.trade === "cabinets") flatCabCharge += c.cost;
      else trueCostNoCredit += c.cost * 0.80;
    });
    trueCostNoCredit += upgrades * 0.80;
    return Math.round(trueCostNoCredit / 0.70 + flatCabCharge - effectiveCredits);
  }
  // Preset: base + CAD + upgrades - credits (capped so never below base).
  var base = getIntContractForBranch(S.model);
  var cadTotal = 0;
  computeCadCharges(S).forEach(function(c){ cadTotal += c.cost; });
  return base + cadTotal + upgrades - effectiveCredits;
}

function renderStep6(){
  if(!STATE.int) initInteriorState();
  else applyIntMetrics();
  initCabUpgradesState();   // idempotent — heals missing nested fields from autosaves/imports
  var cu = STATE.cabUpgrades;
  var cabT = computeCabSections();
  var ctT = computeCtSections();
  var subTab = STATE.cabSubTab || "cabinets";
  var m = STATE.model;
  var cr = CRAFTSMAN[m] || {paint:{}, stain:{}};
  var h = '';

  h += '<div class="card">';
  h +=   '<div class="sub-pills">';
  h +=     '<button class="sub-pill'+(subTab==="cabinets"?" active":"")+'" onclick="switchCabSubTab(\'cabinets\')">Cabinets <span class="sub-pill-badge">'+fmt(cabT.cabSummaryTotal)+'</span></button>';
  h +=     '<button class="sub-pill'+(subTab==="countertops"?" active":"")+'" onclick="switchCabSubTab(\'countertops\')">Countertops <span class="sub-pill-badge">'+fmt(ctT.ctSummaryTotal)+'</span></button>';
  h +=   '</div>';
  h += '</div>';

  h += '<div id="cabSub-cabinets" style="display:'+(subTab==="cabinets"?"block":"none")+'">';
  h += renderCabSubTab(cu, cr, cabT);
  h += '</div>';

  h += '<div id="cabSub-countertops" style="display:'+(subTab==="countertops"?"block":"none")+'">';
  h += renderCtSubTab(ctT);
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function switchCabSubTab(tab){ STATE.cabSubTab = tab; renderCurrentStep(); }

function renderCabSubTab(cu, cr, cabT){
  var h = '';
  var isCustom = isCustomFloorPlan();

  // Section 1 — Plan Selections Summary
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 1 · Plan Selections Summary</span><span class="badge">'+fmt(cabT.planCharges)+'</span></div>';
  h +=   '<div class="card-pad">';
  var charges = computeCadCharges();
  if(charges.length === 0){
    h += '<div class="banner banner-empty">No CAD-based charges. Enter modifications on Step 5 Zone D to see plan charges here.</div>';
  } else {
    h += renderCadChargesInline();
  }
  h +=   '</div>';
  h += '</div>';

  // Section 2 — Craftsman Door Style
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 2 · Craftsman Door Style</span><span class="badge">'+fmt(cabT.doorStyleTotal + cabT.customCraftTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  var areasShown = 0;
  ["kitchen","island","laundry","baths","other"].forEach(function(area){
    var paintCost = pn(cr.paint && cr.paint[area]);
    var stainCost = pn(cr.stain && cr.stain[area]);
    if(paintCost === 0 && stainCost === 0 && !isCustom) return;
    areasShown++;
    var label = area.charAt(0).toUpperCase() + area.slice(1);
    var cur = cu.doorStyle[area] || "";
    var liveCost = cur === "paint" ? paintCost : (cur === "stain" ? stainCost : 0);
    h += '<div class="upg-row">';
    h +=   '<span class="upg-label"><strong>'+esc(label)+'</strong>'+(paintCost||stainCost?' <span style="font-size:11px;color:var(--g500);margin-left:6px">Paint '+fmt(paintCost)+' · Stain '+fmt(stainCost)+'</span>':'')+'</span>';
    h +=   '<select class="sel" onchange="updCraftArea(\''+area+'\', this.value)" style="max-width:240px">';
    h +=     '<option value=""'+(cur===""?" selected":"")+'>— Select Finish —</option>';
    if(paintCost>0 || isCustom) h += '<option value="paint"'+(cur==="paint"?" selected":"")+'>Craftsman Paint</option>';
    if(stainCost>0 || isCustom) h += '<option value="stain"'+(cur==="stain"?" selected":"")+'>Craftsman Stain</option>';
    h +=   '</select>';
    h +=   '<span class="upg-cost'+(liveCost===0?" zero":"")+'">'+(liveCost===0?"—":fmt(liveCost))+'</span>';
    h += '</div>';
  });
  if(areasShown === 0 && !isCustom){
    h += '<div class="banner banner-empty">No preset craftsman areas for this model. Use "+ Add Custom Craftsman Area" below.</div>';
  }

  h += '<div style="margin-top:16px;padding-top:12px;border-top:1px solid var(--g200)">';
  h +=   '<div class="sec-title"><span>Custom Craftsman Areas</span><span class="sec-badge">$35/LF paint · $45/LF stain</span></div>';
  if((cu.customCraftRows||[]).length > 0){
    h += '<div class="row-table">';
    h +=   '<div class="row-hdr" style="grid-template-columns:1.4fr 140px 110px 110px 36px"><div>Area</div><div>Finish</div><div style="text-align:right">LF</div><div style="text-align:right">Cost</div><div></div></div>';
    cu.customCraftRows.forEach(function(r, i){
      var rate = r.finish === "stain" ? 45 : (r.finish === "paint" ? 35 : 0);
      var cost = rate * pn(r.lf);
      h += '<div class="row-line" style="grid-template-columns:1.4fr 140px 110px 110px 36px">';
      h +=   '<input class="inp" type="text" value="'+esc(r.area)+'" placeholder="e.g. Butler\'s Pantry" oninput="updCraftCustomField('+i+', \'area\', this.value)">';
      h +=   '<select class="sel" onchange="updCraftCustomField('+i+', \'finish\', this.value)">';
      h +=     '<option value=""'+(r.finish===""?" selected":"")+'>— Finish —</option>';
      h +=     '<option value="paint"'+(r.finish==="paint"?" selected":"")+'>Paint ($35/LF)</option>';
      h +=     '<option value="stain"'+(r.finish==="stain"?" selected":"")+'>Stain ($45/LF)</option>';
      h +=   '</select>';
      h +=   '<input class="inp mono num" type="number" step="0.25" min="0" value="'+(pn(r.lf)||"")+'" placeholder="0" oninput="updCraftCustomField('+i+', \'lf\', this.value)">';
      h +=   '<div class="row-cost">'+(cost>0?fmt(cost):"—")+'</div>';
      h +=   '<button class="row-del" onclick="delCraftCustomRow('+i+')">×</button>';
      h += '</div>';
    });
    h += '</div>';
  }
  h +=   '<div style="margin-top:10px"><button class="row-add" onclick="addCraftCustomRow()">+ Add Custom Craftsman Area</button></div>';
  h += '</div>';
  h +=   '</div>';
  h += '</div>';

  // Section 3 — Kitchen Upgrades
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 3 · Kitchen Upgrades</span><span class="badge">'+fmt(cabT.kitchenTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     qtyUpgRow("kitDoorsToDrawers", "Change Cabinet Doors to Drawers", 250, "per cabinet", pi(cu.kitchen.doorsToDrawers));
  h +=     qtyUpgRow("kitFridgePanel",    "Increase Fridge Panel Depth to 30\"", 350, "each", pi(cu.kitchen.fridgePanel));
  h +=     toggleUpgRow("kitHoodVent",    "Decorative Hood Vent — No Fan Included (CH36)", 2200, cu.kitchen.hoodVent);
  h +=     toggleUpgRow("kitTallPantry",  "Add Tall Pantry Cabinet", 1200, cu.kitchen.tallPantry);
  h +=     toggleUpgRow("kitLazySusan",   "Add Lazy Susan Cabinet", 850, cu.kitchen.lazySusan);
  h +=   '</div>';
  h += '</div>';

  // Section 4 — Cabinet Inserts (with conditional notes)
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 4 · Cabinet Inserts</span><span class="badge">'+fmt(cabT.insertsTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  [
    {id:"pullOut",    lbl:"Pull Out Inserts",              rate:350, ph:"Describe insert location & type"},
    {id:"drawerRoll", lbl:"Drawer / Roll Out / Tip Out",    rate:275, ph:"Describe insert location & type"},
    {id:"custom",     lbl:"Custom Inserts",                  rate:500, ph:"Describe custom insert details"}
  ].forEach(function(ins){
    var entry = cu.inserts[ins.id];
    var qty = pi(entry.qty);
    var cost = qty * ins.rate;
    h += '<div class="upg-row">';
    h +=   '<span class="upg-label"><strong>'+esc(ins.lbl)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmt(ins.rate)+' each</span></span>';
    h +=   stepperHTML("inserts."+ins.id+".qty", qty, "stepInsertQty");
    h +=   '<span class="upg-cost'+(cost===0?" zero":"")+'">'+(cost===0?"—":fmt(cost))+'</span>';
    h += '</div>';
    if(qty > 0){
      h += '<div style="margin:-2px 0 10px 0">';
      h +=   '<input class="inp" type="text" placeholder="'+esc(ins.ph)+'" value="'+esc(entry.note||"")+'" oninput="updInsertNote(\''+ins.id+'\', this.value)" style="width:100%;font-size:12px">';
      h += '</div>';
    }
  });
  h +=   '</div>';
  h += '</div>';

  // Section 5 — Laundry
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 5 · Laundry Room Upgrades</span><span class="badge">'+fmt(cabT.laundryTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     toggleUpgRow("launUppersWD", "Add Uppers Above Washer/Dryer (5 LF)", 1250, cu.laundry.uppersWD);
  h +=     toggleUpgRow("launTallCab",  "Add Tall Cabinet to Laundry Room", 1200, cu.laundry.tallCab);
  h +=   '</div>';
  h += '</div>';

  // Section 6 — Bathroom
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 6 · Bathroom Upgrades</span><span class="badge">'+fmt(cabT.bathTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     qtyUpgRow("bathDrawerVanity", "Add Drawer Cabinet to Vanity", 350, "each", pi(cu.bath.drawerVanity));
  h +=     qtyUpgRow("bathTallLinen",    "Add Tall Linen Cabinet", 1250, "each", pi(cu.bath.tallLinen));
  h +=     qtyUpgRow("bathMakeupSeat",   "Make Up Seating Area", 350, "each", pi(cu.bath.makeupSeat));
  h +=   '</div>';
  h += '</div>';

  // Section 7 — Custom
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 7 · Custom Upgrades</span><span class="badge">'+fmt(cabT.customTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="sec-title"><span>LF-Based Cabinetry (per area)</span><span class="sec-badge">Uppers &amp; Lowers $450/LF · Lowers Only $350/LF</span></div>';
  if((cu.customRows||[]).length > 0){
    h +=   '<div class="row-table">';
    h +=     '<div class="row-hdr" style="grid-template-columns:1.4fr 180px 110px 110px 36px"><div>Area</div><div>Type</div><div style="text-align:right">LF</div><div style="text-align:right">Cost</div><div></div></div>';
    cu.customRows.forEach(function(r, i){
      var rate = r.type === "uppersLowers" ? 450 : (r.type === "lowersOnly" ? 350 : 0);
      var cost = rate * pn(r.lf);
      h +=   '<div class="row-line" style="grid-template-columns:1.4fr 180px 110px 110px 36px">';
      h +=     '<input class="inp" type="text" value="'+esc(r.area)+'" placeholder="e.g. Mudroom, Office" oninput="updCabCustomRow('+i+', \'area\', this.value)">';
      h +=     '<select class="sel" onchange="updCabCustomRow('+i+', \'type\', this.value)">';
      h +=       '<option value=""'+(r.type===""?" selected":"")+'>— Select Type —</option>';
      h +=       '<option value="uppersLowers"'+(r.type==="uppersLowers"?" selected":"")+'>Uppers &amp; Lowers ($450/LF)</option>';
      h +=       '<option value="lowersOnly"'+(r.type==="lowersOnly"?" selected":"")+'>Lowers Only ($350/LF)</option>';
      h +=     '</select>';
      h +=     '<input class="inp mono num" type="number" step="0.25" min="0" value="'+(pn(r.lf)||"")+'" placeholder="0" oninput="updCabCustomRow('+i+', \'lf\', this.value)">';
      h +=     '<div class="row-cost">'+(cost>0?fmt(cost):"—")+'</div>';
      h +=     '<button class="row-del" onclick="delCabCustomRow('+i+')">×</button>';
      h +=   '</div>';
    });
    h +=   '</div>';
  } else {
    h +=   '<div class="banner banner-empty">No custom LF-based cabinetry rows yet. Add areas like Mudroom, Office, or Butler\'s Pantry below.</div>';
  }
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="addCabCustomRow()">+ Add Another Area</button></div>';

  h +=     '<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--g200)">';
  h +=       '<div class="sec-title"><span>Custom Line Items (free-form)</span></div>';
  if((cu.customLines||[]).length > 0){
    h +=     '<div class="row-table">';
    h +=       '<div class="row-hdr" style="grid-template-columns:1.6fr 160px 130px 36px"><div>Description</div><div>Area</div><div style="text-align:right">Amount</div><div></div></div>';
    cu.customLines.forEach(function(r, i){
      h +=     '<div class="row-line" style="grid-template-columns:1.6fr 160px 130px 36px">';
      h +=       '<input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="Description" oninput="updCabCustomLine('+i+', \'desc\', this.value)">';
      h +=       '<input class="inp" type="text" value="'+esc(r.area)+'" placeholder="e.g. Master BR" oninput="updCabCustomLine('+i+', \'area\', this.value)">';
      h +=       '<input class="inp mono num" type="number" min="0" value="'+(pn(r.amount)||"")+'" placeholder="0" oninput="updCabCustomLine('+i+', \'amount\', this.value)">';
      h +=       '<button class="row-del" onclick="delCabCustomLine('+i+')">×</button>';
      h +=     '</div>';
    });
    h +=     '</div>';
  }
  h +=       '<div style="margin-top:10px"><button class="row-add" onclick="addCabCustomLine()">+ Add Another Line Item</button></div>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // Section 8 — Discount
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 8 · Discount</span>'+(cabT.discount>0?'<span class="badge" style="background:var(--amber-dark);color:#fff">−'+fmt(cabT.discount)+'</span>':'')+'</div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="field" style="max-width:240px"><label class="field-lbl">Discount Amount ($)</label>'
         +   '<input class="inp mono num" type="number" min="0" value="'+(pn(cu.discount)||"")+'" oninput="updCabDiscount(this.value)">'
         +   '<div class="field-hint">Subtracted from cabinet contract total</div>'
         + '</div>';
  h +=   '</div>';
  h += '</div>';

  // Section 9 — Summary
  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Section 9 · Cabinet Upgrade Cost Summary</span></div>';
  h +=   '<div class="card-pad">';
  h +=     summaryRow("1. Plan-Based Charges",        cabT.planCharges, "from Step 5 CAD — counted in interior contract base");
  h +=     summaryRow("2. Door Style Upgrades",       cabT.doorStyleTotal);
  if(cabT.customCraftTotal > 0) h += summaryRow("2b. Custom Craftsman LF", cabT.customCraftTotal);
  h +=     summaryRow("3. Kitchen Upgrades",          cabT.kitchenTotal);
  h +=     summaryRow("4. Cabinet Inserts",           cabT.insertsTotal);
  h +=     summaryRow("5. Laundry Room Upgrades",     cabT.laundryTotal);
  h +=     summaryRow("6. Bathroom Upgrades",         cabT.bathTotal);
  h +=     summaryRow("7. Custom Upgrades",           cabT.customTotal);
  if(cabT.discount > 0) h += summaryRow("8. Discount", -cabT.discount);
  h +=     '<div class="total-bar" style="margin-top:14px"><span class="total-lbl">CABINET UPGRADE TOTAL</span><span class="total-val">'+fmt(cabT.cabSummaryTotal)+'</span></div>';
  h +=   '</div>';
  h += '</div>';

  return h;
}

function renderCtSubTab(ctT){
  var ct = STATE.ct;
  var isCustom = isCustomFloorPlan();
  var h = '';

  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 1 · Plan-Based Countertop Charges</span><span class="badge">'+fmt(ctT.planCharge)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="sum-grid">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Standard Included</div><div class="sum-val">'+$(ctT.stdSF)+' SF</div><div class="sum-sub">std cab LF × 2 + std island</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Modified Total</div><div class="sum-val">'+$(ctT.modSF)+' SF</div><div class="sum-sub">mod cab LF × 2 + mod island</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Added SF</div><div class="sum-val" style="color:var(--red)">'+$(ctT.addedSF)+' SF</div><div class="sum-sub">modified − standard</div></div>';
  h +=     '</div>';
  if(isCustom){
    h += '<div class="banner banner-info"><strong>Custom Floor Plan.</strong> No plan-based countertop customer charge — reverse-margin ÷ 0.70 formula captures countertop cost via the $43/SF base in the trade rate card.</div>';
  } else if(ctT.addedSF > 0){
    h += '<div class="upg-row cad-row"><span class="upg-label"><strong>Added Countertop SF</strong> — '+$(ctT.addedSF)+' SF × $50/SF</span><span class="upg-cost">'+fmt(ctT.planCharge)+'</span></div>';
  } else {
    h += '<div class="banner banner-empty">No CAD modifications to countertop SF. Plan-based charge is $0.</div>';
  }
  h +=   '</div>';
  h += '</div>';

  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 2 · Upgraded Countertop Areas</span><span class="badge">'+fmt(ctT.areaUpgradesTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  if((ct.areas||[]).length > 0){
    h += '<div class="row-table">';
    h +=   '<div class="row-hdr" style="grid-template-columns:1.4fr 130px 110px 110px 36px"><div>Area</div><div style="text-align:right">$/SF</div><div style="text-align:right">SF</div><div style="text-align:right">Cost</div><div></div></div>';
    ct.areas.forEach(function(r, i){
      var cost = pn(r.rate) * pn(r.sqft);
      h += '<div class="row-line" style="grid-template-columns:1.4fr 130px 110px 110px 36px">';
      h +=   '<input class="inp" type="text" value="'+esc(r.area)+'" placeholder="e.g. Kitchen Perimeter" oninput="updCtArea('+i+', \'area\', this.value)">';
      h +=   '<input class="inp mono num" type="number" min="0" value="'+(pn(r.rate)||"")+'" placeholder="0" oninput="updCtArea('+i+', \'rate\', this.value)">';
      h +=   '<input class="inp mono num" type="number" min="0" value="'+(pn(r.sqft)||"")+'" placeholder="0" oninput="updCtArea('+i+', \'sqft\', this.value)">';
      h +=   '<div class="row-cost">'+(cost>0?fmt(cost):"—")+'</div>';
      h +=   '<button class="row-del" onclick="delCtArea('+i+')">×</button>';
      h += '</div>';
    });
    h += '</div>';
  } else {
    h += '<div class="banner banner-empty">No upgraded countertop areas. Use "+ Add Another Area" to enter specific areas at custom $/SF rates.</div>';
  }
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="addCtArea()">+ Add Another Area</button></div>';
  h +=   '</div>';
  h += '</div>';

  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Section 3 · Notes</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<textarea class="inp" rows="4" style="width:100%;resize:vertical" placeholder="Countertop material selections, edge profiles, seams, etc." oninput="updCtNotes(this.value)">'+esc(ct.notes||"")+'</textarea>';
  h +=   '</div>';
  h += '</div>';

  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Section 4 · Countertop Upgrade Total</span></div>';
  h +=   '<div class="card-pad">';
  h +=     summaryRow("Plan-Based Charge (added SF × $50)", ctT.planCharge, isCustom?"not applied for Custom Floor Plan":null);
  h +=     summaryRow("Area Upgrades",                       ctT.areaUpgradesTotal);
  h +=     '<div class="total-bar" style="margin-top:14px"><span class="total-lbl">COUNTERTOP UPGRADE TOTAL</span><span class="total-val">'+fmt(ctT.ctSummaryTotal)+'</span></div>';
  h +=   '</div>';
  h += '</div>';

  return h;
}

/* Shared row builders */
function qtyUpgRow(id, lbl, rate, unit, qty){
  var section = id.indexOf("kit")===0 ? "kitchen" : (id.indexOf("bath")===0 ? "bath" : "");
  var key = "";
  if(section === "kitchen") key = id === "kitDoorsToDrawers" ? "doorsToDrawers" : "fridgePanel";
  else if(section === "bath") key = id === "bathDrawerVanity" ? "drawerVanity" : (id === "bathTallLinen" ? "tallLinen" : "makeupSeat");
  var path = section + "." + key;
  var cost = qty * rate;
  return '<div class="upg-row">'
       +   '<span class="upg-label"><strong>'+esc(lbl)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmt(rate)+' '+esc(unit)+'</span></span>'
       +   stepperHTML(path, qty, "stepCabMetric")
       +   '<span class="upg-cost'+(cost===0?" zero":"")+'">'+(cost===0?"—":fmt(cost))+'</span>'
       + '</div>';
}

function toggleUpgRow(id, lbl, price, checked){
  var path = "";
  if(id === "kitHoodVent") path = "kitchen.hoodVent";
  else if(id === "kitTallPantry") path = "kitchen.tallPantry";
  else if(id === "kitLazySusan") path = "kitchen.lazySusan";
  else if(id === "launUppersWD") path = "laundry.uppersWD";
  else if(id === "launTallCab") path = "laundry.tallCab";
  var cost = checked ? price : 0;
  return '<div class="upg-row">'
       +   '<label class="upg-label" style="display:flex;align-items:center;gap:10px;cursor:pointer"><input type="checkbox" '+(checked?"checked":"")+' onchange="toggleCabFlag(\''+path+'\', this.checked)"><strong>'+esc(lbl)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmt(price)+'</span></label>'
       +   '<span class="upg-cost'+(cost===0?" zero":"")+'">'+(cost===0?"—":fmt(cost))+'</span>'
       + '</div>';
}

function summaryRow(lbl, amount, note, muted){
  return '<div class="upg-row" style="background:var(--g50);border-color:var(--g200)'+(muted?";opacity:.55":"")+'">'
       +   '<span class="upg-label">'+esc(lbl)+(note?' <span style="font-size:11px;color:var(--g500);margin-left:6px">'+esc(note)+'</span>':'')+'</span>'
       +   '<span class="upg-cost'+(amount===0?" zero":"")+'">'+(amount===0?"—":(amount<0?"−"+fmt(Math.abs(amount)):fmt(amount)))+'</span>'
       + '</div>';
}

/* Step 6 handlers */
function updCraftArea(area, val){ STATE.cabUpgrades.doorStyle[area] = val; renderCurrentStep(); }
function addCraftCustomRow(){ STATE.cabUpgrades.customCraftRows.push({area:"", finish:"", lf:0}); renderCurrentStep(); }
function delCraftCustomRow(i){ STATE.cabUpgrades.customCraftRows.splice(i,1); renderCurrentStep(); }
function updCraftCustomField(i, field, val){
  var r = STATE.cabUpgrades.customCraftRows[i];
  if(field === "area") r.area = val;
  else if(field === "finish"){ r.finish = val; renderCurrentStep(); return; }
  else r[field] = pn(val);
  refreshLiveTotals();
}
function stepCabMetric(path, delta){
  var parts = path.split(".");
  var obj = STATE.cabUpgrades[parts[0]];
  obj[parts[1]] = Math.max(0, pi(obj[parts[1]]) + delta);
  renderCurrentStep();
}
function toggleCabFlag(path, checked){
  var parts = path.split(".");
  STATE.cabUpgrades[parts[0]][parts[1]] = checked ? 1 : 0;
  renderCurrentStep();
}
function stepInsertQty(path, delta){
  var parts = path.split(".");
  var entry = STATE.cabUpgrades.inserts[parts[1]];
  entry.qty = Math.max(0, pi(entry.qty) + delta);
  renderCurrentStep();
}
function updInsertNote(insertId, val){
  STATE.cabUpgrades.inserts[insertId].note = val;
  scheduleSave();
}
function updCustomLF(key, val){ /* legacy — kept as no-op for old saved state */ refreshLiveTotals(); }
function addCabCustomRow(){ STATE.cabUpgrades.customRows.push({area:"", type:"", lf:0}); renderCurrentStep(); }
function delCabCustomRow(i){ STATE.cabUpgrades.customRows.splice(i,1); renderCurrentStep(); }
function updCabCustomRow(i, field, val){
  var r = STATE.cabUpgrades.customRows[i];
  if(field === "area") { r.area = val; refreshLiveTotals(); }
  else if(field === "type"){ r.type = val; renderCurrentStep(); }
  else { r.lf = pn(val); refreshLiveTotals(); }
}
function addCabCustomLine(){ STATE.cabUpgrades.customLines.push({desc:"", amount:0, area:""}); renderCurrentStep(); }
function delCabCustomLine(i){ STATE.cabUpgrades.customLines.splice(i,1); renderCurrentStep(); }
function updCabCustomLine(i, field, val){
  var r = STATE.cabUpgrades.customLines[i];
  if(field === "amount") r.amount = pn(val);
  else r[field] = val;
  refreshLiveTotals();
}
function updCabDiscount(val){ STATE.cabUpgrades.discount = pn(val); refreshLiveTotals(); }
function addCtArea(){ STATE.ct.areas.push({area:"", rate:0, sqft:0}); renderCurrentStep(); }
function delCtArea(i){ STATE.ct.areas.splice(i,1); renderCurrentStep(); }
function updCtArea(i, field, val){
  var r = STATE.ct.areas[i];
  if(field === "area") r.area = val;
  else r[field] = pn(val);
  refreshLiveTotals();
}
function updCtNotes(val){ STATE.ct.notes = val; scheduleSave(); }

/* ═══════════════════════════════════════════════════════════════
   STEP 7 — SELECTIONS (5 pills)
   Config-driven: SEL_DEFS holds every upgrade item. One generic renderer
   per pill reads config + STATE.sel[pill] to produce toggles/steppers/SF/LF.
   ═══════════════════════════════════════════════════════════════ */

var SEL_DEFS = __wizRequired("SEL_DEFS");

var CUSTOM_TRADE_CATS = __wizRequired("CUSTOM_TRADE_CATS");

/* ── INIT: idempotent normalizer for STATE.sel ── */
function initSelState(){
  if(!STATE.sel) STATE.sel = {};
  ["docusign","electrical","plumbing","trim"].forEach(function(k){
    if(!STATE.sel[k]) STATE.sel[k] = {};
    var s = STATE.sel[k];
    if(!s.toggles) s.toggles = {};
    if(!s.qtys) s.qtys = {};
    if(!s.sfs) s.sfs = {};
    if(!s.lfs) s.lfs = {};
    if(!Array.isArray(s.customLines)) s.customLines = [];
  });
  if(!STATE.sel.docusign.gasType) STATE.sel.docusign.gasType = "";
  if(!Array.isArray(STATE.sel.trim.concreteFinishLines)) STATE.sel.trim.concreteFinishLines = [];
  if(!STATE.sel.custom) STATE.sel.custom = {upgrades:[], credits:[]};
  if(!Array.isArray(STATE.sel.custom.upgrades)) STATE.sel.custom.upgrades = [];
  if(!Array.isArray(STATE.sel.custom.credits)) STATE.sel.custom.credits = [];
  // Migrate legacy _mat/_fix trade values → base trade + subType
  var legacyMap = {
    "flooring_mat":"flooring", "drywall_mat":"drywall", "paint_mat":"paint",
    "trim_mat":"trim", "doors_mat":"trim", "insulation_mat":"insulation",
    "hvac_mat":"hvac", "plumbing_fix":"plumbing"
  };
  function migrateTrade(r){
    if(!r.subType) r.subType = "both";
    if(legacyMap[r.trade]){ r.subType = "material"; r.trade = legacyMap[r.trade]; }
  }
  STATE.sel.custom.upgrades.forEach(migrateTrade);
  STATE.sel.custom.credits.forEach(migrateTrade);
  if(!STATE.selSubTab) STATE.selSubTab = "docusign";
}

/* ── Compute: one item's cost ── */
function computeSelItemCost(item, sel){
  if(!sel) return 0;
  if(item.type === "toggle"){
    return (sel.toggles && sel.toggles[item.id]) ? item.price : 0;
  }
  if(item.type === "qty"){
    var qty = pn(sel.qtys && sel.qtys[item.id]);
    var cost = qty * item.price;
    if(item.baseAddOn && qty > 0) cost += item.baseAddOn;
    return cost;
  }
  if(item.type === "sf"){
    return pn(sel.sfs && sel.sfs[item.id]) * item.price;
  }
  if(item.type === "lf"){
    return pn(sel.lfs && sel.lfs[item.id]) * item.price;
  }
  return 0;
}

/* ── Compute: one pill's total (for pills with SEL_DEFS) ── */
function computeSelPillTotal(pillKey, S){
  S = S || STATE;
  var defs = SEL_DEFS[pillKey];
  if(!defs || !defs.sections) return 0;
  if(!S.sel || !S.sel[pillKey]) return 0;
  var sel = S.sel[pillKey];
  var total = 0;
  defs.sections.forEach(function(sec){
    (sec.items || []).forEach(function(it){ total += computeSelItemCost(it, sel); });
    (sec.subsections || []).forEach(function(sub){
      (sub.items || []).forEach(function(it){ total += computeSelItemCost(it, sel); });
    });
    if(sec.type === "customLines"){
      (sel.customLines || []).forEach(function(r){ total += pn(r.amount); });
    }
    if(sec.type === "concreteFinishLines"){
      (sel.concreteFinishLines || []).forEach(function(r){ total += pn(r.rate) * pn(r.sqft); });
    }
  });
  return total;
}

/* ── Compute: Pill 5 Custom upgrades / credits ── */
function computeCustomUpgradesTotal(S){
  S = S || STATE;
  if(!S.sel || !S.sel.custom) return 0;
  var total = 0;
  (S.sel.custom.upgrades || []).forEach(function(r){
    if(r.pricing === "flat") total += pn(r.amount);
    else total += pn(r.rate) * pn(r.qty);
  });
  return total;
}

function getSelectionsUpgradesTotal(S){
  S = S || STATE;
  var total = 0;
  ["docusign","electrical","plumbing","trim"].forEach(function(k){
    total += computeSelPillTotal(k, S);
  });
  total += computeCustomUpgradesTotal(S);
  return total;
}

/* ═══════════════════════════════════════════════════════════════
   STEP 7 RENDERER
   ═══════════════════════════════════════════════════════════════ */
function renderStep7(){
  if(!STATE.int) initInteriorState();
  else applyIntMetrics();
  initCabUpgradesState();
  initSelState();

  var subTab = STATE.selSubTab || "docusign";
  var h = '';
  var totals = {
    docusign:   computeSelPillTotal("docusign"),
    electrical: computeSelPillTotal("electrical"),
    plumbing:   computeSelPillTotal("plumbing"),
    trim:       computeSelPillTotal("trim"),
    custom:     computeCustomUpgradesTotal() - getInteriorCreditsTotal()
  };

  // Pill header
  h += '<div class="card">';
  h +=   '<div class="sub-pills">';
  ["docusign","electrical","plumbing","trim","custom"].forEach(function(k){
    var lbl = k === "custom" ? "Custom" : (((SEL_DEFS[k] || {}).label) || k);
    var tot = totals[k];
    var sign = (tot < 0) ? "−" : "";
    var absT = Math.abs(tot);
    h += '<button class="sub-pill'+(subTab===k?" active":"")+'" onclick="switchSelSubTab(\''+k+'\')">'+esc(lbl)+' <span class="sub-pill-badge" id="selpill-badge-'+k+'">'+sign+fmt(absT)+'</span></button>';
  });
  h +=   '</div>';
  h += '</div>';

  // Active pill content
  if(subTab === "custom") h += renderPill5Custom();
  else h += renderSelPill(subTab);

  // Cross-reference note (all pills except Custom)
  if(subTab !== "custom"){
    h += '<div class="card"><div class="card-pad"><div class="banner banner-info"><strong>Need to add a custom upgrade or credit?</strong> Go to the <strong>Custom</strong> pill above to add upgrades not listed here, or to credit items the customer is providing themselves.</div></div></div>';
  }

  document.getElementById("stepContainer").innerHTML = h;
}

function switchSelSubTab(tab){ STATE.selSubTab = tab; renderCurrentStep(); }

/* ── Render one of the config-driven pills (docusign, electrical, plumbing, trim) ── */
function renderSelPill(pillKey){
  var defs = SEL_DEFS[pillKey];
  var sel = STATE.sel[pillKey];
  var pillTotal = computeSelPillTotal(pillKey);
  var h = '';

  defs.sections.forEach(function(sec, secIdx){
    var secTotal = computeSelSectionTotal(sec, sel);
    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Section '+(secIdx+1)+' · '+esc(sec.title)+'</span>'
         +   '<span class="badge" id="selsec-'+pillKey+'-'+secIdx+'" style="'+(secTotal>0?'':'display:none')+'">'+fmt(secTotal)+'</span>'
         + '</div>';
    h +=   '<div class="card-pad">';
    if(sec.header) h += '<div class="sec-title" style="margin-top:0"><span>'+esc(sec.header)+'</span></div>';

    if(sec.type === "radio"){
      h += renderRadioSection(pillKey, sec);
    } else if(sec.type === "customLines"){
      h += renderCustomLinesSection(pillKey);
    } else if(sec.type === "concreteFinishLines"){
      h += renderConcreteFinishSection(sec);
    } else {
      // Standard section with items or subsections
      (sec.items || []).forEach(function(it){ h += renderSelItem(it, pillKey); });
      (sec.subsections || []).forEach(function(sub){
        h += '<div style="margin-top:12px;padding-top:10px;border-top:1px solid var(--g200)">';
        h +=   '<div class="sec-title" style="margin-top:0"><span>'+esc(sub.heading)+'</span></div>';
        sub.items.forEach(function(it){ h += renderSelItem(it, pillKey); });
        h += '</div>';
      });
    }

    if(sec.note) h += '<div class="field-hint" style="margin-top:10px">'+esc(sec.note)+'</div>';
    h +=   '</div>';
    h += '</div>';
  });

  // Pill total bar
  h += '<div class="card">';
  h +=   '<div class="card-pad">';
  h +=     '<div class="total-bar"><span class="total-lbl">'+esc(defs.label.toUpperCase())+' TOTAL</span><span class="total-val" id="selpill-total-'+pillKey+'">'+fmt(pillTotal)+'</span></div>';
  h +=   '</div>';
  h += '</div>';

  return h;
}

function computeSelSectionTotal(sec, sel){
  var total = 0;
  (sec.items || []).forEach(function(it){ total += computeSelItemCost(it, sel); });
  (sec.subsections || []).forEach(function(sub){
    sub.items.forEach(function(it){ total += computeSelItemCost(it, sel); });
  });
  if(sec.type === "customLines") (sel.customLines || []).forEach(function(r){ total += pn(r.amount); });
  if(sec.type === "concreteFinishLines") (sel.concreteFinishLines || []).forEach(function(r){ total += pn(r.rate) * pn(r.sqft); });
  return total;
}

function renderSelItem(item, pillKey){
  var sel = STATE.sel[pillKey];
  var cost = computeSelItemCost(item, sel);
  var costDisplay = cost === 0 ? "—" : fmt(cost);
  var costClass = cost === 0 ? " zero" : "";
  var costId = ' id="selcost-'+pillKey+'-'+item.id+'"';
  var h = '';

  if(item.type === "toggle"){
    var on = !!(sel.toggles && sel.toggles[item.id]);
    h += '<div class="upg-row">';
    h +=   '<label class="upg-label" style="display:flex;align-items:center;gap:10px;cursor:pointer">'
         +   '<input type="checkbox" '+(on?"checked":"")+' onchange="updSelToggle(\''+pillKey+'\', \''+item.id+'\', this.checked)">'
         +   '<strong>'+esc(item.label)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmt(item.price)+'</span>'
         + '</label>';
    h +=   '<span class="upg-cost'+costClass+'"'+costId+'>'+costDisplay+'</span>';
    h += '</div>';
  } else if(item.type === "qty"){
    var qty = pi(sel.qtys && sel.qtys[item.id]);
    var unit = item.unit || "each";
    var baseHint = item.baseAddOn ? ' + '+fmt(item.baseAddOn)+' flat when qty&gt;0' : '';
    h += '<div class="upg-row">';
    h +=   '<span class="upg-label"><strong>'+esc(item.label)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmt(item.price)+'/'+esc(unit)+baseHint+'</span></span>';
    h +=   stepperHTML("sel."+pillKey+"."+item.id, qty, "stepSelQty");
    h +=   '<span class="upg-cost'+costClass+'"'+costId+'>'+costDisplay+'</span>';
    h += '</div>';
  } else if(item.type === "sf" || item.type === "lf"){
    var bucket = item.type === "sf" ? "sfs" : "lfs";
    var val = pn(sel[bucket] && sel[bucket][item.id]);
    var unit = item.type.toUpperCase();
    h += '<div class="upg-row">';
    h +=   '<span class="upg-label"><strong>'+esc(item.label)+'</strong> <span style="font-size:11px;color:var(--g500)">'+fmtC(item.price)+'/'+unit+'</span></span>';
    h +=   '<input class="inp mono num" type="number" step="0.1" min="0" value="'+(val||"")+'" placeholder="0" oninput="updSelNum(\''+pillKey+'\', \''+item.id+'\', \''+item.type+'\', this.value)" style="max-width:140px">';
    h +=   '<span class="upg-cost'+costClass+'"'+costId+'>'+costDisplay+'</span>';
    h += '</div>';
  }
  return h;
}

function renderRadioSection(pillKey, sec){
  var cur = STATE.sel[pillKey][sec.id] || "";
  return radioPillsHTML("sel."+pillKey+"."+sec.id,
    sec.options.filter(function(o){ return o.v !== ""; }),
    cur, "updSelRadio");
}

function renderCustomLinesSection(pillKey){
  var lines = STATE.sel[pillKey].customLines || [];
  var h = '';
  if(lines.length > 0){
    h += '<div class="row-table">';
    h +=   '<div class="row-hdr" style="grid-template-columns:1.8fr 140px 36px"><div>Description</div><div style="text-align:right">Amount</div><div></div></div>';
    lines.forEach(function(r, i){
      h += '<div class="row-line" style="grid-template-columns:1.8fr 140px 36px">';
      h +=   '<input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="Description" oninput="updSelCustomLine(\''+pillKey+'\', '+i+', \'desc\', this.value)">';
      h +=   '<input class="inp mono num" type="number" min="0" value="'+(pn(r.amount)||"")+'" placeholder="0" oninput="updSelCustomLine(\''+pillKey+'\', '+i+', \'amount\', this.value)">';
      h +=   '<button class="row-del" onclick="delSelCustomLine(\''+pillKey+'\', '+i+')">×</button>';
      h += '</div>';
    });
    h += '</div>';
  }
  h += '<div style="margin-top:10px"><button class="row-add" onclick="addSelCustomLine(\''+pillKey+'\')">+ Add Another Upgrade</button></div>';
  return h;
}

function renderConcreteFinishSection(sec){
  var lines = STATE.sel.trim.concreteFinishLines || [];
  var h = '';
  if(sec.referencePricing){
    h += '<div style="background:var(--g50);border:1px solid var(--g200);border-radius:var(--radius-sm);padding:10px 14px;margin-bottom:12px;font-size:12px">';
    h +=   '<div style="font-weight:600;color:var(--g700);margin-bottom:6px">Reference Pricing</div>';
    h +=   '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:4px 16px;color:var(--g600)">';
    sec.referencePricing.forEach(function(rp){
      h += '<div><span>'+esc(rp.l)+':</span> <span class="mono" style="color:var(--g900);font-weight:500">'+esc(rp.r)+'</span></div>';
    });
    h +=   '</div>';
    h += '</div>';
  }
  if(lines.length > 0){
    h += '<div class="row-table">';
    h +=   '<div class="row-hdr" style="grid-template-columns:1.6fr 120px 110px 110px 36px"><div>Description</div><div style="text-align:right">$/SF</div><div style="text-align:right">SF</div><div style="text-align:right">Cost</div><div></div></div>';
    lines.forEach(function(r, i){
      var cost = pn(r.rate) * pn(r.sqft);
      h += '<div class="row-line" style="grid-template-columns:1.6fr 120px 110px 110px 36px">';
      h +=   '<input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="e.g. Grind & Seal — Living Area" oninput="updConcFinishLine('+i+', \'desc\', this.value)">';
      h +=   '<input class="inp mono num" type="number" step="0.01" min="0" value="'+(pn(r.rate)||"")+'" placeholder="0" oninput="updConcFinishLine('+i+', \'rate\', this.value)">';
      h +=   '<input class="inp mono num" type="number" min="0" value="'+(pn(r.sqft)||"")+'" placeholder="0" oninput="updConcFinishLine('+i+', \'sqft\', this.value)">';
      h +=   '<div class="row-cost" id="concfin-cost-'+i+'">'+(cost>0?fmt(cost):"—")+'</div>';
      h +=   '<button class="row-del" onclick="delConcFinishLine('+i+')">×</button>';
      h += '</div>';
    });
    h += '</div>';
  }
  h += '<div style="margin-top:10px"><button class="row-add" onclick="addConcFinishLine()">+ Add Another Line</button></div>';
  return h;
}

/* ── Pill 5 — Custom Upgrades & Credits ── */
function renderPill5Custom(){
  var cust = STATE.sel.custom;
  var upgrades = cust.upgrades || [];
  var credits = cust.credits || [];
  var upTotal = computeCustomUpgradesTotal();
  var crTotal = getInteriorCreditsTotal();
  var netCredits = Math.min(crTotal, upTotal);
  var intUpgrades = getInteriorUpgradesTotal();
  var overCap = crTotal > intUpgrades;
  var netVal = upTotal - netCredits;
  var h = '';

  // Instructions banner
  h += '<div class="card"><div class="card-pad">';
  h +=   '<div class="banner banner-info" style="line-height:1.7">';
  h +=     '<strong style="font-size:13px">Custom Upgrades & Credits — Quick Guide</strong><br><br>';
  h +=     'Use this section for anything not already listed on the other tabs. Pick the trade category, enter your pricing, and the budget adjusts automatically.<br><br>';
  h +=     '<strong style="color:var(--g900)">When to Add an Upgrade</strong><br>'
         + 'The customer wants something extra that STMC will provide or install.<br>'
         + '• <em>Whole-house water softener</em> → Category: <strong>Plumbing</strong>, Flat Rate, $1,800. Budget adds $1,440 (80%) to Plumbing.<br>'
         + '• <em>Upgraded baseboard — 7.25 inch throughout</em> → Category: <strong>Trim & Doors</strong>, Applies To: <strong>Material</strong>, Per LF, $4.50 × 320 LF. Budget adds $1,152 to Trim materials.<br>'
         + '• <em>Specialty tile accent wall in master bath</em> → Category: <strong>Tile</strong>, Per SF, $12 × 80 SF. Budget adds $768 to Tile.<br><br>';
  h +=     '<strong style="color:var(--g900)">When to Add a Credit</strong><br>'
         + 'The customer is providing something themselves, so we need to reduce the contract and the trade budget.<br>'
         + '• <em>Customer supplying their own LVP flooring, but STMC still installs it</em> → Category: <strong>Flooring</strong>, Applies To: <strong>Material</strong>, $3,400. This reduces ONLY the flooring material budget — install labor stays intact.<br>'
         + '• <em>Customer supplying all light fixtures</em> → Category: <strong>Lighting</strong>, $2,000. The contract drops by $2,000 and Lighting budget is reduced by the full amount.<br>'
         + '• <em>Customer hiring their own painter</em> → Category: <strong>Paint</strong>, Applies To: <strong>Labor</strong>, $4,500. Removes the paint labor budget — STMC still supplies the paint material.<br><br>';
  h +=     '<strong style="color:var(--g900)">Labor / Material / Both — When Does This Matter?</strong><br>'
         + 'For trades like Flooring, Trim, Paint, Plumbing, and Electrical, the budget has separate labor and material lines. '
         + 'After you pick one of these categories, a <strong>Labor / Material / Both</strong> toggle appears. This tells the PM exactly which budget line is affected.<br>'
         + '• Pick <strong>Material</strong> when the customer is providing the product but STMC still does the work.<br>'
         + '• Pick <strong>Labor</strong> when the customer has their own contractor but STMC is still providing the product.<br>'
         + '• Leave it on <strong>Both</strong> when the upgrade or credit applies to the whole trade (most common), or if you\'re not sure — it routes to the combined trade line.';
  h +=   '</div>';
  h += '</div></div>';

  // Part A — Custom Upgrades
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Part A · Custom Upgrades</span>'
       +   '<span class="badge" id="pill5-partA-badge">'+fmt(upTotal)+'</span>'
       + '</div>';
  h +=   '<div class="card-pad">';
  if(upgrades.length === 0){
    h += '<div class="banner banner-empty">No custom upgrades yet. Add upgrades not listed on other tabs.</div>';
  } else {
    upgrades.forEach(function(r, i){
      h += renderCustomUpgradeRow(r, i);
    });
  }
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="addCustomUpgrade()">+ Add Another Upgrade</button></div>';
  h +=   '</div>';
  h += '</div>';

  // Part B — Credits
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Part B · Credits</span>'
       +   '<span class="badge" id="pill5-partB-badge" style="background:'+(crTotal>0?"var(--amber-dark)":"")+';color:'+(crTotal>0?"#fff":"")+'">'+(crTotal>0?"−"+fmt(crTotal):"$0")+'</span>'
       + '</div>';
  h +=   '<div class="card-pad">';
  // Credit-cap warning banner — always rendered with display:none so refresh can toggle visibility
  var baseINTText = (STATE.model && !isCustomFloorPlan() && INT_CONTRACT[STATE.model]) ? fmt(INT_CONTRACT[STATE.model].t) : "the base turnkey price";
  h +=     '<div id="pill5-cap-warning" class="banner banner-amber" style="display:'+(overCap && STATE.model && !isCustomFloorPlan() ? "":"none")+'">'
         +   '⚠ Credits (<strong id="pill5-cap-creds">'+fmt(crTotal)+'</strong>) exceed total upgrades (<strong id="pill5-cap-upg">'+fmt(intUpgrades)+'</strong>). '
         +   'The adjusted INT Contract will not fall below the standard turnkey price of <strong>'+baseINTText+'</strong> for this model.'
         + '</div>';
  if(credits.length === 0){
    h += '<div class="banner banner-empty">No credits yet. Add credits for items the customer is providing themselves.</div>';
  } else {
    credits.forEach(function(r, i){
      h += renderCustomCreditRow(r, i);
    });
  }
  h +=     '<div style="margin-top:10px"><button class="row-add" onclick="addCustomCredit()">+ Add Another Credit</button></div>';
  h +=   '</div>';
  h += '</div>';

  // Net total
  h += '<div class="card"><div class="card-pad">';
  h +=   '<div class="total-bar" id="pill5-net-bar" style="'+(netVal<0?"background:var(--g800)":"")+'">'
       +   '<span class="total-lbl">CUSTOM NET TOTAL</span>'
       +   '<span class="total-val" id="pill5-net-total">'+(netVal<0?"−":"")+fmt(Math.abs(netVal))+'</span>'
       + '</div>';
  h += '<div id="pill5-split-line" style="margin-top:8px;font-size:12px;color:var(--g600);line-height:1.5;'+(crTotal===0?"display:none":"")+'">'
     +   'Upgrades: <span id="pill5-split-up">'+fmt(upTotal)+'</span> · Credits applied: <span id="pill5-split-cr">'+fmt(netCredits)+'</span>'
     +   '<span id="pill5-split-capnote" style="'+(netCredits<crTotal?"":"display:none")+'"> (capped from <span id="pill5-split-rawcr">'+fmt(crTotal)+'</span>)</span>'
     + '</div>';
  h += '</div></div>';

  return h;
}

function renderCustomUpgradeRow(r, i){
  var showSub = r.trade && tradeHasSub(r.trade);
  var h = '<div class="row-line" style="display:flex;flex-direction:column;gap:8px;background:var(--g50);margin-bottom:8px">';
  h +=   '<div style="display:flex;justify-content:space-between;align-items:center">';
  h +=     '<span style="font-size:11px;font-weight:600;color:var(--g500);text-transform:uppercase;letter-spacing:0.05em">Upgrade '+(i+1)+'</span>';
  h +=     '<button class="row-del" onclick="delCustomUpgrade('+i+')">×</button>';
  h +=   '</div>';
  // Row 1: Trade + optional subType + Pricing
  h +=   '<div class="field-row">';
  h +=     '<div class="field" style="min-width:200px"><label class="field-lbl">Category</label>'+customTradeDropdown(r.trade, "updCustomUpgrade", i, "trade")+'</div>';
  if(showSub){
    h +=   '<div class="field" style="min-width:200px"><label class="field-lbl">Applies To</label>'+subTypePills(r.subType||"both", "updCustomUpgrade", i)+'</div>';
  }
  h +=     '<div class="field"><label class="field-lbl">Pricing Type</label>';
  h +=       '<div class="radio-pills">';
  h +=         '<button class="radio-pill'+(r.pricing==="flat"?" active":"")+'" onclick="updCustomUpgrade('+i+', \'pricing\', \'flat\')">Flat Rate</button>';
  h +=         '<button class="radio-pill'+(r.pricing==="per_unit"?" active":"")+'" onclick="updCustomUpgrade('+i+', \'pricing\', \'per_unit\')">Per SF / LF</button>';
  h +=       '</div>';
  h +=     '</div>';
  h +=   '</div>';
  // Row 2: Fields based on pricing type
  if(r.pricing === "flat"){
    var cost = pn(r.amount);
    h += '<div class="field-row">';
    h +=   '<div class="field" style="flex:2"><label class="field-lbl">Description</label><input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="e.g. Custom range hood install" oninput="updCustomUpgrade('+i+', \'desc\', this.value)"></div>';
    h +=   '<div class="field"><label class="field-lbl">Amount</label><input class="inp mono num" type="number" min="0" value="'+(pn(r.amount)||"")+'" placeholder="0" oninput="updCustomUpgrade('+i+', \'amount\', this.value)"></div>';
    h +=   '<div class="field" style="max-width:120px"><label class="field-lbl">Row Total</label><div class="metric-readout" id="custup-total-'+i+'">'+(cost>0?fmt(cost):"—")+'</div></div>';
    h += '</div>';
  } else {
    var cost = pn(r.rate) * pn(r.qty);
    h += '<div class="field-row">';
    h +=   '<div class="field" style="flex:2"><label class="field-lbl">Description</label><input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="e.g. Specialty tile accent wall" oninput="updCustomUpgrade('+i+', \'desc\', this.value)"></div>';
    h +=   '<div class="field"><label class="field-lbl">Rate / Unit</label><input class="inp mono num" type="number" step="0.01" min="0" value="'+(pn(r.rate)||"")+'" placeholder="0" oninput="updCustomUpgrade('+i+', \'rate\', this.value)"></div>';
    h +=   '<div class="field" style="max-width:100px"><label class="field-lbl">Unit</label><select class="sel" onchange="updCustomUpgrade('+i+', \'unit\', this.value)"><option value="SF"'+(r.unit==="SF"?" selected":"")+'>SF</option><option value="LF"'+(r.unit==="LF"?" selected":"")+'>LF</option></select></div>';
    h +=   '<div class="field"><label class="field-lbl">Qty</label><input class="inp mono num" type="number" min="0" value="'+(pn(r.qty)||"")+'" placeholder="0" oninput="updCustomUpgrade('+i+', \'qty\', this.value)"></div>';
    h +=   '<div class="field" style="max-width:120px"><label class="field-lbl">Row Total</label><div class="metric-readout" id="custup-total-'+i+'">'+(cost>0?fmt(cost):"—")+'</div></div>';
    h += '</div>';
  }
  h += '</div>';
  return h;
}

function renderCustomCreditRow(r, i){
  var amt = pn(r.amount);
  var showSub = r.trade && tradeHasSub(r.trade);
  var h = '<div class="row-line" style="display:flex;flex-direction:column;gap:8px;background:#FEF3C7;border-color:#FDE68A;margin-bottom:8px">';
  h +=   '<div style="display:flex;justify-content:space-between;align-items:center">';
  h +=     '<span style="font-size:11px;font-weight:600;color:var(--amber-dark);text-transform:uppercase;letter-spacing:0.05em">Credit '+(i+1)+'</span>';
  h +=     '<button class="row-del" onclick="delCustomCredit('+i+')">×</button>';
  h +=   '</div>';
  h +=   '<div class="field-row">';
  h +=     '<div class="field" style="min-width:200px"><label class="field-lbl">Category</label>'+customTradeDropdown(r.trade, "updCustomCredit", i, "trade")+'</div>';
  if(showSub){
    h +=   '<div class="field" style="min-width:200px"><label class="field-lbl">Applies To</label>'+subTypePills(r.subType||"both", "updCustomCredit", i)+'</div>';
  }
  h +=     '<div class="field" style="flex:2"><label class="field-lbl">Description</label><input class="inp" type="text" value="'+esc(r.desc)+'" placeholder="e.g. Customer providing all light fixtures" oninput="updCustomCredit('+i+', \'desc\', this.value)"></div>';
  h +=     '<div class="field"><label class="field-lbl">Credit Amount</label><input class="inp mono num" type="number" min="0" value="'+(pn(r.amount)||"")+'" placeholder="0" oninput="updCustomCredit('+i+', \'amount\', this.value)"></div>';
  h +=     '<div class="field" style="max-width:120px"><label class="field-lbl">Applied</label><div class="metric-readout" id="custcr-total-'+i+'" style="color:var(--amber-dark)">'+(amt>0?"−"+fmt(amt):"—")+'</div></div>';
  h +=   '</div>';
  h += '</div>';
  return h;
}

function customTradeDropdown(cur, handler, i, field){
  var h = '<select class="sel" onchange="'+handler+'('+i+', \''+field+'\', this.value)">';
  h +=   '<option value=""'+(cur===""?" selected":"")+'>— Select Category —</option>';
  CUSTOM_TRADE_CATS.forEach(function(cat){
    h += '<option value="'+esc(cat.v)+'"'+(cur===cat.v?" selected":"")+'>'+esc(cat.l)+'</option>';
  });
  h += '</select>';
  return h;
}

function tradeHasSub(tradeVal){
  for(var i=0; i<CUSTOM_TRADE_CATS.length; i++){
    if(CUSTOM_TRADE_CATS[i].v === tradeVal) return CUSTOM_TRADE_CATS[i].hasSub;
  }
  return false;
}

function subTypePills(curSub, handler, rowIdx){
  var h = '<div class="radio-pills" style="margin-top:0">';
  ["labor","material","both"].forEach(function(v){
    var lbl = v === "labor" ? "Labor" : v === "material" ? "Material" : "Both";
    h += '<button class="radio-pill'+(curSub===v?" active":"")+'" onclick="'+handler+'('+rowIdx+', \'subType\', \''+v+'\')">'+lbl+'</button>';
  });
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
   STEP 7 HANDLERS
   ═══════════════════════════════════════════════════════════════ */
/* ═══════════════════════════════════════════════════════════════
   STEP 7 LIVE REFRESH — targeted DOM updates without rebuilding inputs
   Called by oninput handlers so per-row costs update on every keystroke
   without losing cursor focus.
   ═══════════════════════════════════════════════════════════════ */
function refreshStep7Live(){
  // 1. Update per-item cost spans on pills 1-4 (ID: selcost-{pillKey}-{itemId})
  ["docusign","electrical","plumbing","trim"].forEach(function(pillKey){
    var sel = STATE.sel[pillKey];
    if(!sel) return;
    var defs = SEL_DEFS[pillKey];
    defs.sections.forEach(function(sec){
      function updateItem(it){
        var cost = computeSelItemCost(it, sel);
        var span = document.getElementById("selcost-"+pillKey+"-"+it.id);
        if(span){
          span.textContent = cost === 0 ? "—" : fmt(cost);
          if(cost === 0) span.classList.add("zero");
          else span.classList.remove("zero");
        }
      }
      (sec.items || []).forEach(updateItem);
      (sec.subsections || []).forEach(function(sub){ sub.items.forEach(updateItem); });
    });
  });

  // 2. Update concrete finish row costs (ID: concfin-cost-{i})
  (STATE.sel.trim.concreteFinishLines || []).forEach(function(r, i){
    var cost = pn(r.rate) * pn(r.sqft);
    var el = document.getElementById("concfin-cost-"+i);
    if(el) el.textContent = cost > 0 ? fmt(cost) : "—";
  });

  // 3. Update section badges on the active pill (ID: selsec-{pillKey}-{secIdx})
  var activePill = STATE.selSubTab;
  if(activePill && activePill !== "custom"){
    var defs = SEL_DEFS[activePill];
    var sel = STATE.sel[activePill];
    defs.sections.forEach(function(sec, i){
      var total = computeSelSectionTotal(sec, sel);
      var badge = document.getElementById("selsec-"+activePill+"-"+i);
      if(badge){
        badge.textContent = fmt(total);
        badge.style.display = total > 0 ? "" : "none";
      }
    });
    // Update pill total bar
    var totalBar = document.getElementById("selpill-total-"+activePill);
    if(totalBar) totalBar.textContent = fmt(computeSelPillTotal(activePill));
  }

  // 4. Update Pill 5 row totals + structural elements (if on custom tab)
  if(activePill === "custom"){
    (STATE.sel.custom.upgrades || []).forEach(function(r, i){
      var cost = r.pricing === "flat" ? pn(r.amount) : pn(r.rate) * pn(r.qty);
      var el = document.getElementById("custup-total-"+i);
      if(el) el.textContent = cost > 0 ? fmt(cost) : "—";
    });
    (STATE.sel.custom.credits || []).forEach(function(r, i){
      var amt = pn(r.amount);
      var el = document.getElementById("custcr-total-"+i);
      if(el) el.textContent = amt > 0 ? "−"+fmt(amt) : "—";
    });
    // Pill 5 structural elements
    var upT = computeCustomUpgradesTotal();
    var crT = getInteriorCreditsTotal();
    var intUp = getInteriorUpgradesTotal();
    var netCr = Math.min(crT, upT);
    var overCap = crT > intUp;
    var netV = upT - netCr;
    var partA = document.getElementById("pill5-partA-badge");
    if(partA) partA.textContent = fmt(upT);
    var partB = document.getElementById("pill5-partB-badge");
    if(partB){
      partB.textContent = crT > 0 ? "−"+fmt(crT) : "$0";
      partB.style.background = crT > 0 ? "var(--amber-dark)" : "";
      partB.style.color = crT > 0 ? "#fff" : "";
    }
    var netBar = document.getElementById("pill5-net-bar");
    if(netBar) netBar.style.background = netV < 0 ? "var(--g800)" : "";
    var netTot = document.getElementById("pill5-net-total");
    if(netTot) netTot.textContent = (netV < 0 ? "−" : "") + fmt(Math.abs(netV));
    var splitLine = document.getElementById("pill5-split-line");
    if(splitLine) splitLine.style.display = crT === 0 ? "none" : "";
    var splitUp = document.getElementById("pill5-split-up");
    if(splitUp) splitUp.textContent = fmt(upT);
    var splitCr = document.getElementById("pill5-split-cr");
    if(splitCr) splitCr.textContent = fmt(netCr);
    var splitCapNote = document.getElementById("pill5-split-capnote");
    if(splitCapNote) splitCapNote.style.display = netCr < crT ? "" : "none";
    var splitRawCr = document.getElementById("pill5-split-rawcr");
    if(splitRawCr) splitRawCr.textContent = fmt(crT);
    var capWarn = document.getElementById("pill5-cap-warning");
    if(capWarn) capWarn.style.display = (overCap && STATE.model && !isCustomFloorPlan()) ? "" : "none";
    var capCreds = document.getElementById("pill5-cap-creds");
    if(capCreds) capCreds.textContent = fmt(crT);
    var capUpg = document.getElementById("pill5-cap-upg");
    if(capUpg) capUpg.textContent = fmt(intUp);
  }

  // 5. Update all 5 pill header badges (totals ripple across pills via custom's net)
  var totals = {
    docusign:   computeSelPillTotal("docusign"),
    electrical: computeSelPillTotal("electrical"),
    plumbing:   computeSelPillTotal("plumbing"),
    trim:       computeSelPillTotal("trim"),
    custom:     computeCustomUpgradesTotal() - getInteriorCreditsTotal()
  };
  Object.keys(totals).forEach(function(k){
    var badge = document.getElementById("selpill-badge-"+k);
    if(badge){
      var t = totals[k];
      badge.textContent = (t < 0 ? "−" : "") + fmt(Math.abs(t));
    }
  });

  // 6. Fall through to the standard running-total refresh (header + data-livesum spans + autosave)
  refreshLiveTotals();
}

function updSelToggle(pillKey, id, checked){
  STATE.sel[pillKey].toggles[id] = !!checked;
  renderCurrentStep();
}
function stepSelQty(path, delta){
  // path = "sel.pillKey.itemId"
  var parts = path.split(".");
  var pill = parts[1], id = parts[2];
  STATE.sel[pill].qtys[id] = Math.max(0, pi(STATE.sel[pill].qtys[id]) + delta);
  renderCurrentStep();
}
function updSelNum(pillKey, id, type, val){
  var bucket = type === "sf" ? "sfs" : "lfs";
  STATE.sel[pillKey][bucket][id] = pn(val);
  refreshStep7Live();
}
function updSelRadio(path, val){
  var parts = path.split(".");
  STATE.sel[parts[1]][parts[2]] = val;
  renderCurrentStep();
}
function addSelCustomLine(pillKey){
  STATE.sel[pillKey].customLines.push({desc:"", amount:0});
  renderCurrentStep();
}
function delSelCustomLine(pillKey, i){
  STATE.sel[pillKey].customLines.splice(i, 1);
  renderCurrentStep();
}
function updSelCustomLine(pillKey, i, field, val){
  var r = STATE.sel[pillKey].customLines[i];
  if(field === "desc") { r.desc = val; refreshStep7Live(); return; }
  r.amount = pn(val);
  refreshStep7Live();
}
function addConcFinishLine(){
  STATE.sel.trim.concreteFinishLines.push({desc:"", rate:0, sqft:0});
  renderCurrentStep();
}
function delConcFinishLine(i){
  STATE.sel.trim.concreteFinishLines.splice(i, 1);
  renderCurrentStep();
}
function updConcFinishLine(i, field, val){
  var r = STATE.sel.trim.concreteFinishLines[i];
  if(field === "desc") { r.desc = val; refreshStep7Live(); return; }
  r[field] = pn(val);
  refreshStep7Live();
}
function addCustomUpgrade(){
  STATE.sel.custom.upgrades.push({trade:"", subType:"both", pricing:"flat", desc:"", amount:0, rate:0, unit:"SF", qty:0});
  renderCurrentStep();
}
function delCustomUpgrade(i){ STATE.sel.custom.upgrades.splice(i,1); renderCurrentStep(); }
function updCustomUpgrade(i, field, val){
  var r = STATE.sel.custom.upgrades[i];
  if(field === "amount" || field === "rate" || field === "qty") r[field] = pn(val);
  else r[field] = val;
  // Re-render for layout-changing fields (trade shows/hides subType toggle, pricing swaps fields, unit/subType)
  if(field === "pricing" || field === "trade" || field === "unit" || field === "subType") renderCurrentStep();
  else refreshStep7Live();
}
function addCustomCredit(){
  STATE.sel.custom.credits.push({trade:"", subType:"both", desc:"", amount:0});
  renderCurrentStep();
}
function delCustomCredit(i){ STATE.sel.custom.credits.splice(i,1); renderCurrentStep(); }
function updCustomCredit(i, field, val){
  var r = STATE.sel.custom.credits[i];
  if(field === "amount") r.amount = pn(val);
  else r[field] = val;
  if(field === "trade" || field === "subType") renderCurrentStep();
  else refreshStep7Live();
}

/* ═══════════════════════════════════════════════════════════════
   UPGRADE TEXT & BULLET GENERATION — reads STATE, produces arrays
   for Contract wording (Part E) and PDF pricing tables.
   ═══════════════════════════════════════════════════════════════ */

function gatherUpgradeTextLines(){
  // Returns array of human-readable strings for contract wording (no dollar amounts)
  var lines = [];
  if(!STATE.int) return lines;
  var S = STATE;
  var cu = S.cabUpgrades;
  var isCust = isCustomFloorPlan();

  // Step 5 — CAD modifications
  var cadList = computeCadCharges(S);
  cadList.forEach(function(c){
    if(c.cost > 0 || c.cost < 0) lines.push(c.label);
  });

  // Step 6 Sub-Tab A — Cabinets
  if(cu){
    // Craftsman door style
    var ds = cu.doorStyle || {};
    ["kitchen","island","laundry","baths","other"].forEach(function(area){
      if(ds[area]) lines.push("Door Style — "+area.charAt(0).toUpperCase()+area.slice(1)+": "+ds[area]);
    });
    (cu.customCraftRows||[]).forEach(function(r){
      if(r.area && r.finish) lines.push("Custom Craftsman: "+r.area+" — "+r.finish+(pn(r.lf)>0?" ("+pn(r.lf)+" LF)":""));
    });
    // Kitchen upgrades
    var kNames = {doorsToDrawers:"Doors to Drawers", fridgePanel:"Fridge Panel", hoodVent:"Hood Vent", tallPantry:"Tall Pantry", lazySusan:"Lazy Susan"};
    if(cu.kitchen) Object.keys(kNames).forEach(function(k){
      var qty = pi(cu.kitchen[k]);
      if(qty > 0) lines.push("Kitchen: "+kNames[k]+(qty>1?" ("+qty+")":""));
    });
    // Inserts
    if(cu.inserts){
      ["pullOut","drawerRoll","custom"].forEach(function(k){
        var ins = cu.inserts[k];
        if(ins && pi(ins.qty) > 0){
          var iLabel = {pullOut:"Pull-Out Shelf", drawerRoll:"Drawer Roll-Out", custom:"Custom Insert"}[k];
          lines.push("Cabinet Insert: "+iLabel+" ("+pi(ins.qty)+")"+(ins.note ? " — "+ins.note : ""));
        }
      });
    }
    // Laundry
    if(cu.laundry){
      if(pi(cu.laundry.uppersWD)>0) lines.push("Laundry: Uppers Above W/D ("+pi(cu.laundry.uppersWD)+")");
      if(pi(cu.laundry.tallCab)>0) lines.push("Laundry: Tall Cabinet ("+pi(cu.laundry.tallCab)+")");
    }
    // Bath
    if(cu.bath){
      if(pi(cu.bath.drawerVanity)>0) lines.push("Bath: Drawer Stack Vanity ("+pi(cu.bath.drawerVanity)+")");
      if(pi(cu.bath.tallLinen)>0) lines.push("Bath: Tall Linen ("+pi(cu.bath.tallLinen)+")");
      if(pi(cu.bath.makeupSeat)>0) lines.push("Bath: Makeup Seat ("+pi(cu.bath.makeupSeat)+")");
    }
    // Custom cabinetry rows
    (cu.customRows||[]).forEach(function(r){
      if(r.area && pn(r.lf)>0){
        var type = r.type==="uppersLowers"?"Uppers & Lowers":"Lowers Only";
        lines.push("Custom Cabinetry: "+r.area+" — "+type+" ("+pn(r.lf)+" LF)");
      }
    });
    // Custom line items
    (cu.customLines||[]).forEach(function(r){
      if(r.desc) lines.push("Cabinet Custom: "+r.desc+(r.area?" — "+r.area:""));
    });
    // Discount
    if(pn(cu.discount)>0) lines.push("Cabinet Discount Applied");
  }

  // Step 6 Sub-Tab B — Countertops
  if(S.ct){
    (S.ct.areas||[]).forEach(function(a){
      if(a.area && pn(a.sqft)>0) lines.push("Countertop Upgrade: "+a.area+" ("+pn(a.sqft)+" SF × "+fmtC(pn(a.rate))+"/SF)");
    });
    if(S.ct.notes) lines.push("Countertop Notes: "+S.ct.notes);
  }

  // Step 7 — Selections (Pills 1-4)
  ["docusign","electrical","plumbing","trim"].forEach(function(pillKey){
    var defs = SEL_DEFS[pillKey];
    if(!defs || !S.sel || !S.sel[pillKey]) return;
    var sel = S.sel[pillKey];
    function processItem(it){
      if(it.type === "toggle" && sel.toggles[it.id]) lines.push(it.label);
      if(it.type === "qty" && pi(sel.qtys[it.id]) > 0){
        var qty = pi(sel.qtys[it.id]);
        lines.push(it.label+(qty>1?" ("+qty+")":""));
      }
      if(it.type === "sf" && pn(sel.sfs[it.id]) > 0) lines.push(it.label+": "+pn(sel.sfs[it.id])+" SF");
      if(it.type === "lf" && pn(sel.lfs[it.id]) > 0) lines.push(it.label+": "+pn(sel.lfs[it.id])+" LF");
    }
    defs.sections.forEach(function(sec){
      if(sec.type === "radio" && sel[sec.id]) lines.push(sec.title+": "+sel[sec.id]);
      (sec.items||[]).forEach(processItem);
      (sec.subsections||[]).forEach(function(sub){ sub.items.forEach(processItem); });
    });
  });

  // Step 7 — Concrete finish lines
  (S.sel.trim.concreteFinishLines||[]).forEach(function(r){
    if(r.desc && (pn(r.rate)*pn(r.sqft))>0) lines.push("Concrete Finish: "+r.desc+" ("+pn(r.sqft)+" SF × "+fmtC(pn(r.rate))+"/SF)");
  });

  // Step 7 Pill 5 — Custom upgrades
  (S.sel.custom.upgrades||[]).forEach(function(r){
    if(r.pricing === "flat" && pn(r.amount) > 0) lines.push("Custom: "+(r.desc||"Upgrade"));
    else if(pn(r.rate)*pn(r.qty) > 0) lines.push("Custom: "+(r.desc||"Upgrade")+" ("+pn(r.qty)+" "+(r.unit||"SF")+")");
  });

  // Step 7 Pill 5 — Credits
  (S.sel.custom.credits||[]).forEach(function(r){
    if(pn(r.amount)>0) lines.push("Credit: "+(r.desc||"Customer-provided item")+" (−"+fmt(pn(r.amount))+")");
  });

  return lines;
}

function gatherUpgradeBulletItems(){
  // Returns array of {label, cost} for PDF pricing tables
  var items = [];
  if(!STATE.int) return items;
  var S = STATE;
  var cu = S.cabUpgrades;

  // CAD charges
  computeCadCharges(S).forEach(function(c){
    if(c.cost !== 0) items.push({label:c.label, cost:c.cost});
  });

  // Cab upgrades (non-plan): use computeCabSections line items
  if(cu){
    var ds = cu.doorStyle || {};
    ["kitchen","island","laundry","baths","other"].forEach(function(area){
      if(ds[area]){
        var rate = ds[area].toLowerCase().indexOf("stain") >= 0 ? 45 : 35;
        // Approximate — actual cost computed in sections
      }
    });
    // Kitchen upgrades
    var kRates = {doorsToDrawers:200, fridgePanel:500, hoodVent:650, tallPantry:1200, lazySusan:250};
    if(cu.kitchen) Object.keys(kRates).forEach(function(k){
      var qty = pi(cu.kitchen[k]);
      if(qty > 0){
        var lbl = {doorsToDrawers:"Doors to Drawers", fridgePanel:"Fridge Panel", hoodVent:"Hood Vent", tallPantry:"Tall Pantry", lazySusan:"Lazy Susan"}[k];
        items.push({label:"Kitchen: "+lbl+(qty>1?" ×"+qty:""), cost:qty*kRates[k]});
      }
    });
    // Inserts
    var iRates = {pullOut:175, drawerRoll:175, custom:250};
    if(cu.inserts) ["pullOut","drawerRoll","custom"].forEach(function(k){
      var ins = cu.inserts[k];
      if(ins && pi(ins.qty)>0){
        var lbl = {pullOut:"Pull-Out Shelf", drawerRoll:"Drawer Roll-Out", custom:"Custom Insert"}[k];
        items.push({label:"Insert: "+lbl+" ×"+pi(ins.qty), cost:pi(ins.qty)*iRates[k]});
      }
    });
    // Laundry
    if(cu.laundry){
      if(pi(cu.laundry.uppersWD)>0) items.push({label:"Laundry: Uppers Above W/D", cost:pi(cu.laundry.uppersWD)*500});
      if(pi(cu.laundry.tallCab)>0) items.push({label:"Laundry: Tall Cabinet", cost:pi(cu.laundry.tallCab)*900});
    }
    // Bath
    if(cu.bath){
      if(pi(cu.bath.drawerVanity)>0) items.push({label:"Bath: Drawer Stack Vanity", cost:pi(cu.bath.drawerVanity)*400});
      if(pi(cu.bath.tallLinen)>0) items.push({label:"Bath: Tall Linen", cost:pi(cu.bath.tallLinen)*800});
      if(pi(cu.bath.makeupSeat)>0) items.push({label:"Bath: Makeup Seat", cost:pi(cu.bath.makeupSeat)*350});
    }
    // Custom rows
    (cu.customRows||[]).forEach(function(r){
      var rate = r.type==="uppersLowers"?450:(r.type==="lowersOnly"?350:0);
      if(pn(r.lf)>0 && rate>0) items.push({label:"Custom: "+r.area+" ("+r.type.replace("uppersLowers","U&L").replace("lowersOnly","Lowers")+")", cost:rate*pn(r.lf)});
    });
    (cu.customLines||[]).forEach(function(r){
      if(pn(r.amount)>0) items.push({label:"Custom: "+(r.desc||"Line item"), cost:pn(r.amount)});
    });
  }

  // Countertop upgrades
  if(S.ct)(S.ct.areas||[]).forEach(function(a){
    if(pn(a.sqft)>0) items.push({label:"Countertop: "+a.area, cost:pn(a.rate)*pn(a.sqft)});
  });

  // Selections pills 1-4
  ["docusign","electrical","plumbing","trim"].forEach(function(pk){
    var defs = SEL_DEFS[pk]; if(!defs || !S.sel[pk]) return;
    var sel = S.sel[pk];
    function proc(it){
      var cost = computeSelItemCost(it, sel);
      if(cost > 0) items.push({label:it.label+(it.type==="qty"&&pi(sel.qtys[it.id])>1?" ×"+pi(sel.qtys[it.id]):""), cost:cost});
    }
    defs.sections.forEach(function(sec){
      (sec.items||[]).forEach(proc);
      (sec.subsections||[]).forEach(function(sub){ sub.items.forEach(proc); });
    });
  });

  // Concrete finish
  (S.sel.trim.concreteFinishLines||[]).forEach(function(r){
    var cost = pn(r.rate)*pn(r.sqft);
    if(cost>0) items.push({label:"Concrete: "+(r.desc||"Finish"), cost:cost});
  });

  // Custom upgrades
  (S.sel.custom.upgrades||[]).forEach(function(r){
    var cost = r.pricing==="flat"?pn(r.amount):pn(r.rate)*pn(r.qty);
    if(cost>0) items.push({label:"Custom: "+(r.desc||"Upgrade"), cost:cost});
  });

  // Credits (negative)
  (S.sel.custom.credits||[]).forEach(function(r){
    if(pn(r.amount)>0) items.push({label:"Credit: "+(r.desc||"Customer-provided"), cost:-pn(r.amount)});
  });

  return items;
}

/* ═══════════════════════════════════════════════════════════════
   STEP 8 — CONTRACT PAGE
   ═══════════════════════════════════════════════════════════════ */
function renderStep8(){
  var items = buildSalesItems();
  var concItems = buildConcItems();
  var concTotal = sumItems(concItems);
  var custLabor = sumItems(items) - concTotal;   // labor = total sales - concrete pass-through
  var punchAmt = Math.max(P.punch, pn(STATE.ext.punchAmt)||0);
  var p10 = pn(STATE.customer.p10);
  var shellTotal = p10 + custLabor + concTotal;
  var livingSF = livSF();
  var shellPerSF = livingSF > 0 ? shellTotal / livingSF : 0;
  var branchLbl = BRANCHES[STATE.branch] ? BRANCHES[STATE.branch].label : STATE.branch;

  var h = '';
  var isShell = STATE.jobMode === "shell";

  // Info banner
  h += '<div class="banner banner-info"><strong>Contract Breakdown</strong> — '
     +   esc(STATE.model || "(no model selected)")
     +   ' <span class="info-chip">'+esc(branchLbl)+'</span>'
     + '</div>';

  // ── PART A: EXTERIOR SHELL CONTRACT BREAKDOWN ──
  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Part A · Exterior Shell</span></div>';
  h +=   '<div class="kpi-grid">';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">P10 Material Total</div><div class="kpi-val">'+fmt(p10)+'</div></div>';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">Customer Labor Cost</div><div class="kpi-val red">'+fmt(custLabor)+'</div></div>';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">Punch Total</div><div class="kpi-val">'+fmt(punchAmt)+'</div></div>';
  h +=   '</div>';
  h +=   '<div class="kpi-grid">';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">Concrete Total</div><div class="kpi-val">'+fmt(concTotal)+'</div></div>';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">Shell Price per SQFT</div><div class="kpi-val" style="font-size:18px">'+(livingSF>0?fmtC(shellPerSF)+'/SF':'—')+'</div></div>';
  h +=     '<div class="kpi-box"><div class="kpi-lbl">Branch</div><div class="kpi-val" style="font-size:14px">'+esc(branchLbl)+'</div></div>';
  h +=   '</div>';
  h +=   '<div style="padding:8px 16px 16px"><div class="total-bar"><span class="total-lbl">Total Exterior Shell Package</span><span class="total-val">'+fmt(shellTotal)+'</span></div></div>';
  h += '</div>';

  // ── CUSTOMER PRICING SUMMARY (itemized) ──
  if(items.length > 0){
    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Customer Pricing Summary</span></div>';
    h +=   '<table class="ps-table">';
    h +=     '<thead><tr><th>Description</th><th style="text-align:right">Details</th><th style="text-align:right">Amount</th></tr></thead>';
    h +=     '<tbody>';
    items.forEach(function(it){
      h +=   '<tr><td>'+esc(it.label)+'</td><td class="num">'+$(it.qty)+' '+it.unit+' × '+fmtC(it.rate)+'</td><td class="cost">'+fmt(it.cost)+'</td></tr>';
    });
    h +=     '<tr class="ps-total"><td colspan="2">LABOR AND CONCRETE TOTAL</td><td class="cost">'+fmt(sumItems(items))+'</td></tr>';
    h +=     '</tbody>';
    h +=   '</table>';
    h += '</div>';
  }

  // ── TURNKEY PARTS B-E (Turnkey mode only) ──
  if(!isShell){
    if(!STATE.int) initInteriorState();
    else applyIntMetrics();
    initCabUpgradesState();
    initSelState();

    var cabS = computeCabSections();
    var ctS  = computeCtSections();
    var cadCharges = [];
    computeCadCharges().forEach(function(c){ cadCharges.push(c); });
    var cadTotal = 0;
    cadCharges.forEach(function(c){ cadTotal += c.cost; });
    var ctPlanCharge = isCustomFloorPlan() ? 0 : ctS.planCharge;
    var cadBasedKPI = cadTotal + ctPlanCharge;

    var selUpTotal = getSelectionsUpgradesTotal();
    var effCredits = getEffectiveCredits();
    var upgradesKPI = cabS.upgradesSubtotal + ctS.upgradesSubtotal + selUpTotal - effCredits;
    var intContract = computeInteriorContractPrice();
    var turnkeyTotal = shellTotal + intContract;
    var intPerSF = livingSF > 0 ? intContract / livingSF : 0;
    var totalPerSF = shellPerSF + intPerSF;

    var baseINT = 0;
    var isCustomFP = isCustomFloorPlan();
    if(!isCustomFP && INT_CONTRACT[STATE.model]) baseINT = INT_CONTRACT[STATE.model].t;

    // ── PART B: Interior Turnkey Contract ──
    h += '<div class="card">';
    h +=   '<div class="section-hdr section-hdr-red"><span>Part B · Interior Turnkey Contract</span></div>';
    h +=   '<div class="kpi-grid">';
    h +=     '<div class="kpi-box"><div class="kpi-lbl">Base Turnkey Adder</div><div class="kpi-val">'+(isCustomFP ? '<span style="font-size:13px">Custom Floor Plan</span>' : fmt(baseINT))+'</div></div>';
    h +=     '<div class="kpi-box"><div class="kpi-lbl">CAD-Based Charges</div><div class="kpi-val">'+fmt(cadBasedKPI)+'</div></div>';
    h +=     '<div class="kpi-box"><div class="kpi-lbl">Upgrades Selected</div><div class="kpi-val">'+fmt(upgradesKPI)+'</div></div>';
    h +=   '</div>';
    h +=   '<div class="card-pad">';
    if(livingSF > 0){
      h += '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">';
      h +=   '<div class="kpi-box"><div class="kpi-lbl">Shell $/SF</div><div class="kpi-val" style="font-size:15px">'+fmtC(shellPerSF)+'/SF</div></div>';
      h +=   '<div class="kpi-box"><div class="kpi-lbl">Interior $/SF</div><div class="kpi-val" style="font-size:15px">'+fmtC(intPerSF)+'/SF</div></div>';
      h +=   '<div class="kpi-box"><div class="kpi-lbl">Total $/SF</div><div class="kpi-val" style="font-size:18px;font-weight:700">'+fmtC(totalPerSF)+'/SF</div></div>';
      h += '</div>';
    }
    h +=     '<div style="margin-top:12px"><div class="total-bar" style="font-size:16px"><span class="total-lbl">Total Contracted Amount</span><span class="total-val">'+fmt(turnkeyTotal)+'</span></div>';
    h +=       '<div style="margin-top:6px;font-size:12px;color:var(--g600)">Shell: '+fmt(shellTotal)+' · Interior: '+fmt(intContract)+'</div>';
    h +=     '</div>';
    h +=   '</div>';
    h += '</div>';

    // ── PART C: Cabinet Contract Summary ──
    var baseCabLF = isCustomFP ? pn(STATE.int.cabLF) : (MODELS[STATE.model] ? pn(MODELS[STATE.model].cabinetryLFNum) : 0);
    var baseCabContract = baseCabLF * 330;
    var cabUpgTotal = isCustomFP ? cabS.upgradesSubtotal : cabS.cabSummaryTotal;
    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Part C · Cabinet Contract Summary</span></div>';
    h +=   '<div class="card-pad">';
    h +=     '<div class="field-row" style="gap:8px">';
    h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Base Cabinet Contract</div><div class="kpi-val">'+fmt(baseCabContract)+'</div><div style="font-size:10px;color:var(--g500);margin-top:2px">'+baseCabLF+' LF × $330</div></div>';
    h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Total Cabinet Upgrades</div><div class="kpi-val">'+fmt(cabUpgTotal)+'</div></div>';
    h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl" style="font-weight:700">Total Cabinet Contract</div><div class="kpi-val" style="font-weight:700;font-size:18px">'+fmt(baseCabContract + cabUpgTotal)+'</div></div>';
    h +=     '</div>';
    h +=   '</div>';
    h += '</div>';

    // ── PART D: Upgrade Categories Breakdown ──
    var docT = computeSelPillTotal("docusign");
    var elecT = computeSelPillTotal("electrical");
    var plmT  = computeSelPillTotal("plumbing");
    var trmT  = computeSelPillTotal("trim");
    var custUpT = computeCustomUpgradesTotal();
    var crTotal = getInteriorCreditsTotal();
    var catLines = [
      {lbl:"Cabinet Upgrades", val: cabUpgTotal},
      {lbl:"Countertop Upgrades", val: ctPlanCharge + ctS.upgradesSubtotal},
      {lbl:"Docusign INT Upgrades", val: docT},
      {lbl:"Electrical Upgrades", val: elecT},
      {lbl:"Plumbing Upgrades", val: plmT},
      {lbl:"Interior Trim & Flooring", val: trmT},
      {lbl:"Custom Upgrades", val: custUpT}
    ];
    if(crTotal > 0) catLines.push({lbl:"Credits", val: -effCredits, credit:true});
    var grandUpg = 0;
    catLines.forEach(function(c){ grandUpg += c.val; });

    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Part D · Upgrade Categories Breakdown</span></div>';
    h +=   '<table class="ps-table">';
    h +=     '<thead><tr><th>Category</th><th style="text-align:right">Amount</th></tr></thead>';
    h +=     '<tbody>';
    catLines.forEach(function(c){
      var style = c.credit ? ' style="color:var(--green-dark)"' : (c.val === 0 ? ' class="muted"' : '');
      h += '<tr'+style+'><td>'+esc(c.lbl)+'</td><td class="cost">'+(c.credit ? '−'+fmt(Math.abs(c.val)) : fmt(c.val))+'</td></tr>';
    });
    h +=     '<tr class="ps-total"><td>GRAND TOTAL IN UPGRADES</td><td class="cost">'+fmt(grandUpg)+'</td></tr>';
    h +=     '</tbody>';
    h +=   '</table>';
    h += '</div>';

    // ── PART E: Contract Upgrade Wording ──
    var textLines = gatherUpgradeTextLines();
    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Part E · Contract Upgrade Selections</span></div>';
    h +=   '<div class="card-pad">';
    if(textLines.length === 0){
      h += '<div class="banner banner-empty">No upgrades selected</div>';
    } else {
      h += '<div style="background:var(--g50);border:1px solid var(--g200);border-radius:var(--radius-sm);padding:12px 16px;font-size:13px;line-height:1.7;max-height:340px;overflow-y:auto">';
      textLines.forEach(function(line){ h += '<div>• '+esc(line)+'</div>'; });
      h += '</div>';
    }
    h +=   '</div>';
    h += '</div>';
  }

  // ── DRAW SCHEDULE ──
  var tkTotal = isShell ? shellTotal : (shellTotal + (typeof intContract !== "undefined" ? intContract : 0));
  h += renderDrawScheduleHTML(isShell, p10, concTotal, custLabor, shellTotal, tkTotal);

  // ── Save & PDF action buttons ──
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Save Contract</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<button id="saveContractBtn" class="nav-btn nav-next" style="width:100%;font-size:15px;padding:12px 20px" onclick="saveContract()"> Save Contract to Dashboard</button>';
  h +=     '<div style="margin-top:8px;font-size:11px;color:var(--g500)">Saves this contract to the server — it will immediately appear on the Manager and Owner dashboards.</div>';
  h +=   '</div>';
  h += '</div>';

  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Generate PDFs</span></div>';
  h +=   '<div class="card-pad" style="display:flex;gap:10px;flex-wrap:wrap">';
  if(isShell){
    h += '<button class="nav-btn nav-next" style="flex:1;min-width:220px" onclick="printFullContract()">📋 Generate Full Contract PDF</button>';
    h += '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printCustomerPDF()">📄 Customer Contract PDF</button>';
    h += '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printContractorPDF()">🔧 Contractor Labor PDF</button>';
  } else {
    h += '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printCustomerPDF()">📋 Exterior Shell Contract</button>';
    h += '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printUpgradesPDF()">📄 Customer Upgrades PDF</button>';
    h += '<button class="nav-btn nav-next" style="flex:1;min-width:220px" onclick="printContractsPDF()">📋 Generate Contracts PDF</button>';
    h += '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printDrawSchedulePDF()">📄 Save Draw Schedule PDF</button>';
  }
  h +=   '</div>';
  h +=   '<div style="padding:0 16px 14px;font-size:11px;color:var(--g500);line-height:1.5">Opens your browser\'s native print dialog. You can save to PDF, send to printer, or cancel — you\'ll be right back where you left off.</div>';
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

function renderDrawScheduleHTML(isShell, p10, concTotal, custLabor, shellTotal, turnkeyTotal){
  var deposit = 2500;
  var draw1 = Math.max(0, p10 - deposit);
  var draw2 = concTotal;
  var draw3 = custLabor;
  var h = '';
  var total = isShell ? shellTotal : turnkeyTotal;
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Draw Schedule</span><span class="badge">'+fmt(total)+'</span></div>';
  h +=   '<table class="draw-table">';
  h +=     '<thead><tr><th>Draw</th><th>Description</th><th style="text-align:right">Amount</th></tr></thead>';
  h +=     '<tbody>';
  h +=     '<tr class="draw-deposit"><td>Good Faith Deposit (Prepayment)</td><td>Non-refundable, paid at signing</td><td class="num">'+fmt(deposit)+'</td></tr>';
  h +=     '<tr><td>1st Home Draw at Loan Closing (Minimum of 20% of total home contract)</td><td>Total Shell Material Amount minus Prepayment</td><td class="num">'+fmt(draw1)+'</td></tr>';
  h +=     '<tr><td>1st Draw Shop/Detached Garage Portion (if applicable)</td><td>Total Shop/Detached Garage Deposit (Full Material Amount of shop/detached garage)</td><td class="num muted">'+fmt(0)+'</td></tr>';
  h +=     '<tr><td>2nd Home Draw Upon Concrete Completion (Minimum 20%)</td><td>Includes remaining material, site prep, and concrete</td><td class="num">'+fmt(draw2)+'</td></tr>';
  h +=     '<tr><td>2nd Draw Shop/Detached Garage Portion (if applicable)</td><td>Total Concrete and Labor Cost at Completion of Shop/Detached Garage</td><td class="num muted">'+fmt(0)+'</td></tr>';
  h +=     '<tr><td>3rd Home Draw Upon Framing Completion (Minimum 15%)</td><td>Includes exterior labor</td><td class="num">'+fmt(draw3)+'</td></tr>';
  if(isShell){
    h +=   '<tr><td>4th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of mechanical rough-in/electric/plumbing/HVAC</td><td class="num muted">—</td></tr>';
    h +=   '<tr><td>5th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of drywall/cabinets/countertops</td><td class="num muted">—</td></tr>';
    h +=   '<tr><td>6th Home Draw (Minimum 5%)</td><td>Final Punch/Notice of Completion or Certificate of Occupancy if necessary</td><td class="num muted">—</td></tr>';
  } else {
    var draw4 = Math.round(turnkeyTotal * 0.20);
    var draw5 = Math.round(turnkeyTotal * 0.20);
    var draw6 = Math.max(0, turnkeyTotal - deposit - draw1 - draw2 - draw3 - draw4 - draw5);
    h +=   '<tr><td>4th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of mechanical rough-in/electric/plumbing/HVAC</td><td class="num">'+fmt(draw4)+'</td></tr>';
    h +=   '<tr><td>5th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of drywall/cabinets/countertops</td><td class="num">'+fmt(draw5)+'</td></tr>';
    h +=   '<tr><td>6th Home Draw (Minimum 5%)</td><td>Final Punch/Notice of Completion or Certificate of Occupancy if necessary</td><td class="num">'+fmt(draw6)+'</td></tr>';
  }
  h +=     '</tbody>';
  h +=   '</table>';
  h +=   '<div class="card-pad" style="padding:10px 16px;font-size:11px;color:var(--g500);line-height:1.5">Note that progress in construction shall not proceed to the next step until the draw is received on the completed work up to that point.<br>Contractor accepts cash, checks, and wires. Past due accounts are subject to a monthly fee which will be calculated at the rate of 1.5% monthly interest rate.<br>Summertown Metals Contracting • '+psDateStamp()+'</div>';
  h += '</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
   PDF GENERATION — same-window print pattern from V7.
   All PDFs built from STATE (not DOM-scraped). Structure:
     1. Fill #printSheet with <div class="ps-page">…</div> sections.
     2. window.print() — browser's native print dialog opens in-place.
     3. User saves to PDF, prints, or cancels — no new tabs.
   ═══════════════════════════════════════════════════════════════ */

function psDateStamp(){
  return new Date().toLocaleDateString('en-US', {year:'numeric', month:'long', day:'numeric'});
}

function buildPsHeader(titleText, opts){
  opts = opts || {};
  var c = STATE.customer;
  var branch = BRANCHES[STATE.branch] ? BRANCHES[STATE.branch].label : STATE.branch;
  var h = '';
  h += '<div class="ps-hdr">';
  h +=   '<div>';
  h +=     '<div class="ps-hdr-brand">Summertown Metals Contracting</div>';
  h +=     '<div class="ps-hdr-brand-sub">STMC Turnkey Estimator</div>';
  if(opts.warning) h += '<div class="ps-hdr-warn">'+esc(opts.warning)+'</div>';
  h +=   '</div>';
  h +=   '<div class="ps-hdr-info">';
  h +=     '<div><strong>Date</strong>'+psDateStamp()+'</div>';
  if(c.order) h += '<div><strong>Order #</strong>'+esc(c.order)+'</div>';
  h +=   '</div>';
  h += '</div>';
  h += '<div class="ps-title">'+esc(titleText)+'</div>';
  h += '<div class="ps-info-grid">';
  h +=   '<div><span class="lbl">Customer</span>'+esc(c.name || "—")+'</div>';
  h +=   '<div><span class="lbl">Model</span>'+esc(STATE.model || "—")+'</div>';
  h +=   '<div><span class="lbl">Sales Rep</span>'+esc(c.rep || "—")+'</div>';
  h +=   '<div><span class="lbl">Address</span>'+esc(c.addr || "—")+'</div>';
  h +=   '<div><span class="lbl">Branch</span>'+esc(branch)+'</div>';
  h += '</div>';
  return h;
}

function buildPsCustomerPricing(){
  var items = buildSalesItems();
  var linesTotal = sumItems(items);
  var p10 = pn(STATE.customer.p10);
  var shellTotal = p10 + linesTotal;

  var h = buildPsHeader('Customer Pricing Summary');
  h += '<table class="ps-table">';
  h +=   '<thead><tr><th style="width:44%">Description</th><th class="num" style="width:18%">Qty</th><th class="num" style="width:18%">Rate</th><th class="num" style="width:20%">Amount</th></tr></thead>';
  h +=   '<tbody>';
  h +=     '<tr><td><strong>P10 Material Package</strong></td><td class="num">—</td><td class="num">—</td><td class="num">'+fmt(p10)+'</td></tr>';
  items.forEach(function(it){
    var qty = (it.unit === "ea") ? $(it.qty) : $(it.qty)+" "+it.unit;
    h +=   '<tr><td>'+esc(it.label)+'</td><td class="num">'+qty+'</td><td class="num">'+fmtC(it.rate)+'</td><td class="num">'+fmt(it.cost)+'</td></tr>';
  });
  h +=     '<tr class="total"><td colspan="3">TOTAL EXTERIOR SHELL PACKAGE</td><td class="num">'+fmt(shellTotal)+'</td></tr>';
  h +=   '</tbody>';
  h += '</table>';
  h += '<div class="ps-footer">Summertown Metals Contracting · This estimate is valid for 30 days · Generated '+psDateStamp()+'</div>';
  return h;
}

function buildPsContractorLabor(){
  var all = buildCtrItems();
  var items = all.filter(function(i){ return i.qty > 0 && i.cost > 0; });
  var sections = getSections(items);
  var grand = sumItems(items);

  var h = buildPsHeader('Contractor Labor Breakdown', {warning:'Internal document — not for customer distribution'});
  h += '<table class="ps-table">';
  h +=   '<thead><tr><th style="width:50%">Item</th><th class="num" style="width:16%">Qty</th><th class="num" style="width:14%">Rate</th><th class="num" style="width:20%">Amount</th></tr></thead>';
  h +=   '<tbody>';
  sections.forEach(function(sec){
    var secItems = items.filter(function(i){ return i.section === sec; });
    if(secItems.length === 0) return;
    var secTotal = sumSection(items, sec);
    h += '<tr class="section"><td colspan="3">'+esc(sec)+'</td><td class="num">'+fmt(secTotal)+'</td></tr>';
    secItems.forEach(function(it){
      var qty = (it.unit === "ea") ? $(it.qty) : $(it.qty)+" "+it.unit;
      h += '<tr><td>'+esc(it.label)+'</td><td class="num">'+qty+'</td><td class="num">'+fmtC(it.rate)+'</td><td class="num">'+fmt(it.cost)+'</td></tr>';
    });
  });
  if(items.length === 0){
    h += '<tr><td colspan="4" style="text-align:center;color:#999;padding:14px">No contractor line items. Configure the exterior shell in Steps 2–3 first.</td></tr>';
  }
  h += '<tr class="total"><td colspan="3">CONTRACTOR TOTAL</td><td class="num">'+fmt(grand)+'</td></tr>';
  h +=   '</tbody>';
  h += '</table>';
  h += '<div class="ps-footer">Summertown Metals Contracting · Contractor scope of work · Generated '+psDateStamp()+'</div>';
  return h;
}

function buildPsDrawSchedule(){
  var isShell = STATE.jobMode === "shell";
  var items = buildSalesItems();
  var concTotal = sumItems(buildConcItems());
  var custLabor = sumItems(items) - concTotal;
  var p10 = pn(STATE.customer.p10);
  var shellTotal = p10 + custLabor + concTotal;
  var turnkeyTotal = shellTotal + computeInteriorContractPrice();
  var deposit = 2500;
  var draw1 = Math.max(0, p10 - deposit);
  var draw2 = concTotal;
  var draw3 = custLabor;

  var h = buildPsHeader('Draw Schedule');
  h += '<table class="ps-table">';
  h +=   '<thead><tr><th style="width:38%">Draw</th><th style="width:42%">Description</th><th class="num" style="width:20%">Amount</th></tr></thead>';
  h +=   '<tbody>';
  h +=     '<tr><td><strong>Good Faith Deposit (Prepayment)</strong></td><td>Non-refundable, paid at signing</td><td class="num">'+fmt(deposit)+'</td></tr>';
  h +=     '<tr><td>1st Home Draw at Loan Closing (Minimum of 20% of total home contract)</td><td>Total Shell Material Amount minus Prepayment</td><td class="num">'+fmt(draw1)+'</td></tr>';
  h +=     '<tr><td>1st Draw Shop/Detached Garage Portion (if applicable)</td><td>Total Shop/Detached Garage Deposit (Full Material Amount of shop/detached garage)</td><td class="num">'+fmt(0)+'</td></tr>';
  h +=     '<tr><td>2nd Home Draw Upon Concrete Completion (Minimum 20%)</td><td>Includes remaining material, site prep, and concrete</td><td class="num">'+fmt(draw2)+'</td></tr>';
  h +=     '<tr><td>2nd Draw Shop/Detached Garage Portion (if applicable)</td><td>Total Concrete and Labor Cost at Completion of Shop/Detached Garage</td><td class="num">'+fmt(0)+'</td></tr>';
  h +=     '<tr><td>3rd Home Draw Upon Framing Completion (Minimum 15%)</td><td>Includes exterior labor</td><td class="num">'+fmt(draw3)+'</td></tr>';
  if(isShell){
    h +=   '<tr><td>4th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of mechanical rough-in/electric/plumbing/HVAC</td><td class="num">—</td></tr>';
    h +=   '<tr><td>5th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of drywall/cabinets/countertops</td><td class="num">—</td></tr>';
    h +=   '<tr><td>6th Home Draw (Minimum 5%)</td><td>Final Punch/Notice of Completion or Certificate of Occupancy if necessary</td><td class="num">—</td></tr>';
    h +=   '<tr class="total"><td colspan="2">TOTAL EXTERIOR SHELL PACKAGE</td><td class="num">'+fmt(shellTotal)+'</td></tr>';
  } else {
    var draw4 = Math.round(turnkeyTotal * 0.20);
    var draw5 = Math.round(turnkeyTotal * 0.20);
    var draw6 = Math.max(0, turnkeyTotal - deposit - draw1 - draw2 - draw3 - draw4 - draw5);
    h +=   '<tr><td>4th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of mechanical rough-in/electric/plumbing/HVAC</td><td class="num">'+fmt(draw4)+'</td></tr>';
    h +=   '<tr><td>5th Home Draw (Minimum 20%)</td><td>20% of total contract upon completion of drywall/cabinets/countertops</td><td class="num">'+fmt(draw5)+'</td></tr>';
    h +=   '<tr><td>6th Home Draw (Minimum 5%)</td><td>Final Punch/Notice of Completion or Certificate of Occupancy if necessary</td><td class="num">'+fmt(draw6)+'</td></tr>';
    h +=   '<tr class="total"><td colspan="2">TOTAL CONTRACTED AMOUNT</td><td class="num">'+fmt(turnkeyTotal)+'</td></tr>';
  }
  h +=   '</tbody>';
  h += '</table>';
  h += '<div class="ps-footer">Note that progress in construction shall not proceed to the next step until the draw is received on the completed work up to that point.<br>Contractor accepts cash, checks, and wires. Past due accounts are subject to a monthly fee which will be calculated at the rate of 1.5% monthly interest rate.<br>Summertown Metals Contracting • '+psDateStamp()+'</div>';
  return h;
}

function printToSheet(html){
  var ps = document.getElementById("printSheet");
  if(!ps){ showToast("Print sheet not ready."); return; }
  ps.innerHTML = html;
  ps.style.display = "block";
  setTimeout(function(){
    try { window.print(); } catch(e){ showToast("Print failed: "+e.message); }
    // Clean up after the dialog closes (cancel or save)
    setTimeout(function(){
      ps.innerHTML = "";
      ps.style.display = "none";
    }, 300);
  }, 150);
}

function requireModel(){
  if(!STATE.model){ showToast("Select a model on Step 1 first."); return false; }
  return true;
}

function printCustomerPDF(){
  if(!requireModel()) return;
  var html = '<div class="ps-page">' + buildPsCustomerPricing() + '</div>';
  printToSheet(html);
}
function printContractorPDF(){
  if(!requireModel()) return;
  var html = '<div class="ps-page">' + buildPsContractorLabor() + '</div>';
  printToSheet(html);
}
function printFullContract(){
  if(!requireModel()) return;
  var html = '';
  html += '<div class="ps-page">' + buildPsCustomerPricing() + '</div>';
  html += '<div class="ps-page ps-page-break">' + buildPsContractorLabor() + '</div>';
  html += '<div class="ps-page ps-page-break">' + buildPsDrawSchedule() + '</div>';
  printToSheet(html);
}
function printUpgradesPDF(){
  if(!requireModel()) return;
  var html = '<div class="ps-page">' + buildPsUpgradesPricing() + '</div>';
  printToSheet(html);
}
function printContractsPDF(){
  if(!requireModel()) return;
  var html = '';
  html += '<div class="ps-page">' + buildPsContractSummary() + '</div>';
  html += '<div class="ps-page ps-page-break">' + buildPsDrawSchedule() + '</div>';
  printToSheet(html);
}
function printDrawSchedulePDF(){
  if(!requireModel()) return;
  var html = '';
  html += '<div class="ps-page">' + buildPsDrawSchedule() + '</div>';
  html += '<div class="ps-page ps-page-break">' + buildPsUpgradesPricing() + '</div>';
  html += '<div class="ps-page ps-page-break">' + buildPsUpgradeWording() + '</div>';
  printToSheet(html);
}

/* ── Turnkey PDF builders ── */
function buildPsUpgradesPricing(){
  var h = buildPsHeader("Interior Upgrades Pricing Summary");
  var bullets = gatherUpgradeBulletItems();
  h += '<table class="ps-detail-table" style="width:100%;border-collapse:collapse;font-size:12px;margin-top:10px">';
  h +=   '<thead><tr style="border-bottom:2px solid #333"><th style="text-align:left;padding:6px">Item</th><th style="text-align:right;padding:6px">Amount</th></tr></thead>';
  h +=   '<tbody>';
  var total = 0;
  bullets.forEach(function(b){
    total += b.cost;
    var neg = b.cost < 0;
    h += '<tr style="border-bottom:1px solid #ddd"><td style="padding:5px 6px">'+esc(b.label)+'</td><td style="text-align:right;padding:5px 6px;font-family:monospace;'+(neg?"color:green":"")+'">'+( neg ? "−"+fmt(Math.abs(b.cost)) : fmt(b.cost) )+'</td></tr>';
  });
  h +=   '<tr style="border-top:2px solid #333;font-weight:bold"><td style="padding:6px">GRAND TOTAL IN UPGRADES</td><td style="text-align:right;padding:6px;font-family:monospace">'+fmt(total)+'</td></tr>';
  h +=   '</tbody>';
  h += '</table>';
  h += '<div style="margin-top:16px;font-size:10px;color:#777">Summertown Metals Contracting &bull; '+psDateStamp()+' &bull; This estimate is valid for 30 days.</div>';
  return h;
}

function buildPsContractSummary(){
  var items = buildSalesItems();
  var concTotal = sumItems(buildConcItems());
  var custLabor = sumItems(items) - concTotal;
  var p10 = pn(STATE.customer.p10);
  var shellTotal = p10 + custLabor + concTotal;
  var livSFVal = livSF();
  var intContract = computeInteriorContractPrice();
  var turnkey = shellTotal + intContract;

  var h = buildPsHeader("Contract Summary");
  h += '<div style="display:flex;gap:12px;margin:10px 0"><div style="flex:1;text-align:center;padding:8px;border:1px solid #ddd;border-radius:4px"><div style="font-size:10px;color:#777">Shell Package</div><div style="font-size:16px;font-weight:700">'+fmt(shellTotal)+'</div></div>';
  h +=   '<div style="flex:1;text-align:center;padding:8px;border:1px solid #ddd;border-radius:4px"><div style="font-size:10px;color:#777">Interior Contract</div><div style="font-size:16px;font-weight:700">'+fmt(intContract)+'</div></div>';
  h +=   '<div style="flex:1;text-align:center;padding:8px;background:#A31A1A;color:#fff;border-radius:4px"><div style="font-size:10px;opacity:0.8">Total Contracted Amount</div><div style="font-size:18px;font-weight:700">'+fmt(turnkey)+'</div></div></div>';
  if(livSFVal > 0){
    h += '<div style="text-align:center;font-size:12px;color:#555;margin-bottom:10px">Shell '+fmtC(shellTotal/livSFVal)+'/SF &bull; Interior '+fmtC(intContract/livSFVal)+'/SF &bull; <strong>Total '+fmtC(turnkey/livSFVal)+'/SF</strong></div>';
  }
  h += '<div style="margin-top:16px;font-size:10px;color:#777">Summertown Metals Contracting &bull; '+psDateStamp()+'</div>';
  return h;
}

function buildPsUpgradeWording(){
  var h = buildPsHeader("Contract Upgrade Selections");
  var textLines = gatherUpgradeTextLines();
  if(textLines.length === 0){
    h += '<p style="font-size:13px;color:#777">No upgrades selected.</p>';
  } else {
    h += '<div style="font-size:12px;line-height:1.8;margin-top:10px">';
    textLines.forEach(function(line){ h += '<div>&bull; '+esc(line)+'</div>'; });
    h += '</div>';
  }
  h += '<div style="margin-top:16px;font-size:10px;color:#777">Summertown Metals Contracting &bull; '+psDateStamp()+'</div>';
  return h;
}

/* ═══════════════════════════════════════════════════════════════
  STEP 9 — BUDGET
  Shows PM the true cost breakdown. No customer pricing or margins.
  ═══════════════════════════════════════════════════════════════ */

function computeUpgradesByTrade(S){
  // Returns {tradeKey: trueCostAdder} for every trade that received upgrades.
  // Upgrades at ×0.80. Credits at FULL value (subtracted).
  S = S || STATE;
  var out = {};
  function addTo(k, amt){ out[k] = (out[k]||0) + amt; }

  // Step 6 cabinet upgrades → cabinets at 0.80
  var cabS = computeCabSections(S);
  if(cabS.cabSummaryTotal > 0) addTo("cabinets", cabS.cabSummaryTotal * 0.80);

  // Step 6 countertop upgrades → countertops at 0.80
  var ctS = computeCtSections(S);
  var ctUpg = isCustomFloorPlan() ? ctS.upgradesSubtotal : (ctS.planCharge + ctS.upgradesSubtotal);
  if(ctUpg > 0) addTo("countertops", ctUpg * 0.80);

  // Pills 1-4: walk SEL_DEFS, compute each item cost, route to item.trade at 0.80
  ["docusign","electrical","plumbing","trim"].forEach(function(pk){
    var defs = SEL_DEFS[pk]; if(!defs || !S.sel || !S.sel[pk]) return;
    var sel = S.sel[pk];
    function proc(it){
      var cost = computeSelItemCost(it, sel);
      if(cost > 0) addTo(it.trade, cost * 0.80);
    }
    defs.sections.forEach(function(sec){
      (sec.items||[]).forEach(proc);
      (sec.subsections||[]).forEach(function(sub){ sub.items.forEach(proc); });
    });
  });

  // Concrete finish lines → concreteFinish at 0.80
  (S.sel.trim.concreteFinishLines||[]).forEach(function(r){
    var cost = pn(r.rate) * pn(r.sqft);
    if(cost > 0) addTo("concreteFinish", cost * 0.80);
  });

  // Pill 5 custom upgrades → trade at 0.80
  (S.sel.custom.upgrades||[]).forEach(function(r){
    var cost = r.pricing === "flat" ? pn(r.amount) : pn(r.rate) * pn(r.qty);
    if(cost > 0 && r.trade) addTo(r.trade, cost * 0.80);
  });

  // Pill 5 credits → trade at FULL value (subtracted)
  (S.sel.custom.credits||[]).forEach(function(r){
    var amt = pn(r.amount);
    if(amt > 0 && r.trade) addTo(r.trade, -amt);
  });

  return out;
}

function renderStep9(){
  var isShell = STATE.jobMode === "shell";

  // Turnkey needs interior state initialized; shell doesn't but it's harmless
  if(!STATE.int) initInteriorState();
  else applyIntMetrics();
  if(!isShell){ initCabUpgradesState(); initSelState(); }

  var h = '';
  var I = STATE.int || {};
  var deckAudit = !!STATE.ext.deckShown;
  var deckKeys = {deckRoof:1, deckNR:1, trex:1};
  var milesKey = STATE.miles >= 1 ? "o" : "u";
  var milesLabel = milesKey === "o" ? "Over 100 Miles" : "Under 100 Miles";
  var stdRoofSF = rfMetalStd();
  var stdRoofRate = STATE.ext.g26 ? 1.5 : (P.ctr.r612[milesKey] || 0);
  var overrideCount = Object.keys(STATE.ext.ctrOverrides || {}).length;

  // Deck audit banner (if flagged)
  if(deckAudit){
    h += '<div class="banner banner-amber" style="margin-bottom:10px"><strong>Deck Framing audit needed</strong> - deck-related line items are highlighted below in amber. Verify quantities before finalizing the contractor payout.</div>';
  }

  // PART A: Exterior Contractor Calculator (editable) - both modes
  var ctrItems = buildCtrItems();
  var ctrSections = getSections(ctrItems);
  var ctrTotal = sumItems(ctrItems);

  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>'+(isShell?'Contractor Labor Budget':'Part A · Contractor Labor Budget')+'</span><span class="badge">'+fmt(ctrTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="banner banner-info">Auto-populated from Steps 2–3. <strong>All possible labor line items are shown</strong> — the PM can enter or adjust any quantity to match the actual contractor payout. Zero-qty rows are muted but remain editable.</div>';
  h +=     '<div class="banner banner-amber" style="margin-top:8px">Calc fingerprint: <strong>'+esc(milesLabel)+'</strong> bucket · 26g roof <strong>'+(STATE.ext.g26?"Yes":"No")+'</strong> · Std metal roof <strong>'+$(stdRoofSF)+'</strong> SF @ <strong>'+fmtC(stdRoofRate)+'/SF</strong> · Manual overrides <strong>'+$(overrideCount)+'</strong></div>';
  ctrSections.forEach(function(sec){
    var secItems = ctrItems.filter(function(i){ return i.section === sec; });
    if(secItems.length === 0) return;
    h += '<div style="margin-top:14px">';
    h +=   '<div class="sec-title"><span>'+esc(sec)+'</span><span class="sec-badge">'+fmt(sumSection(ctrItems, sec))+'</span></div>';
    h +=   '<div class="row-table">';
    h +=     '<div class="row-hdr" style="grid-template-columns:2.2fr 100px 100px 120px"><div>Item</div><div style="text-align:right">Qty</div><div style="text-align:right">Rate</div><div style="text-align:right">Cost</div></div>';
    secItems.forEach(function(it){
      var zeroStyle = it.qty === 0 ? 'opacity:0.55' : '';
      var deckHL = deckAudit && deckKeys[it.key] ? 'background:#FFFBEB;border-left:3px solid #F59E0B;' : '';
      h +=   '<div class="row-line" style="grid-template-columns:2.2fr 100px 100px 120px;'+zeroStyle+deckHL+'">';
      h +=     '<div style="font-size:12px">'+esc(it.label)+(deckAudit && deckKeys[it.key] ? ' <span style="color:#B45309;font-size:10px">AUDIT</span>' : '')+'</div>';
      h +=     '<input class="inp mono num" type="number" step="0.25" min="0" value="'+(it.qty||"")+'" placeholder="0" style="max-width:90px" oninput="updCtrOverride(\''+it.key+'\', this.value)">';
      h +=     '<div class="num" style="font-size:12px;color:var(--g600)">'+fmtC(it.rate)+'/'+esc(it.unit)+'</div>';
      h +=     '<div class="row-cost" id="ctr-cost-'+it.key+'">'+(it.qty>0?fmt(it.cost):"—")+'</div>';
      h +=   '</div>';
    });
    h +=   '</div>';
    h += '</div>';
  });
  h +=     '<div style="margin-top:14px"><div class="total-bar"><span class="total-lbl">CONTRACTOR TOTAL</span><span class="total-val" id="ctr-grand-total">'+fmt(ctrTotal)+'</span></div></div>';
  h +=   '</div>';
  h += '</div>';

  // PART B: Contractor Summary - both modes
  var salesItems = buildSalesItems();
  var concTotal = sumItems(buildConcItems());
  var custLabor = sumItems(salesItems) - concTotal;
  var laborProfit = custLabor - ctrTotal;
  var laborProfitPct = custLabor > 0 ? (laborProfit / custLabor * 100) : 0;
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>'+(isShell?'Contractor Summary':'Part B · Contractor Summary')+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="field-row" style="gap:8px">';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Customer Exterior Labor</div><div class="kpi-val red">'+fmt(custLabor)+'</div></div>';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Contractor Labor Estimate</div><div class="kpi-val">'+fmt(ctrTotal)+'</div></div>';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Estimated Labor Profit</div><div class="kpi-val" style="color:'+(laborProfit>=0?"var(--green-dark)":"var(--stc-red)")+'">'+fmt(laborProfit)+' ('+laborProfitPct.toFixed(1)+'%)</div></div>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';

  // SHELL MODE: just the contractor PDF button
  if(isShell){
    h += '<div class="card">';
    h +=   '<div class="section-hdr"><span>Generate Budget PDF</span></div>';
    h +=   '<div class="card-pad" style="display:flex;gap:10px;flex-wrap:wrap">';
    h +=     '<button class="nav-btn nav-next" style="flex:1;min-width:220px" onclick="printContractorPDF()">Contractor Labor PDF</button>';
    h +=   '</div>';
    h +=   '<div style="padding:0 16px 14px;font-size:11px;color:var(--g500);line-height:1.5">Internal document — not customer-facing. Opens your browser\'s native print dialog.</div>';
    h += '</div>';

    document.getElementById("stepContainer").innerHTML = h;
    return;
  }

  // TURNKEY ONLY: Parts D, F, G below

  // PART D: Interior Base Budget Table (16 trades)
  var livingSF = livSF();
  var drivers = {
    livingSF: livingSF, cabLF: pn(I.cabLF), counterSF: pn(I.counterSF),
    drywallSF: pn(I.drywallSF), trimLF: pn(I.trimLF), doors: pn(I.doors),
    bathCount: pi(I.fullBaths)+pi(I.halfBaths), fixtures: pn(I.fixtures),
    hvacTons: pn(I.hvacTons), flat: 1
  };

  var upgradesByTrade = computeUpgradesByTrade();
  var intBaseTotal = 0;
  var intUpgTotal = 0;
  var tradeRows = [];
  INT_TRADE_GROUPS.forEach(function(tg){
    var baseCost = calcIntTradeBase(tg);
    var upgAdder = upgradesByTrade[tg.key] || 0;
    intBaseTotal += baseCost;
    intUpgTotal += upgAdder;
    tradeRows.push({key:tg.key, name:tg.name, baseCost:baseCost, upgAdder:upgAdder, total:baseCost+upgAdder, rates:tg.rates});
  });

  h += '<div class="card">';
  h +=   '<div class="section-hdr section-hdr-red"><span>Part D · Interior Budget</span><span class="badge">'+fmt(intBaseTotal+intUpgTotal)+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="sum-grid" style="margin-bottom:14px">';
  h +=       '<div class="sum-box"><div class="sum-lbl">Living SF</div><div class="sum-val">'+$(livingSF)+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Cabinet LF</div><div class="sum-val">'+$(pn(I.cabLF))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Counter SF</div><div class="sum-val">'+$(pn(I.counterSF))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Drywall SF</div><div class="sum-val">'+$(pn(I.drywallSF))+'</div>'+(pn(I.drywallSF)>0?'<div class="sum-sub">~'+Math.ceil(pn(I.drywallSF)/32)+' sheets (4\'×8\')</div>':'')+'</div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Trim LF</div><div class="sum-val">'+$(pn(I.trimLF))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Doors</div><div class="sum-val">'+$(pn(I.doors))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Baths</div><div class="sum-val">'+$(pi(I.fullBaths)+pi(I.halfBaths))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Fixtures</div><div class="sum-val">'+$(pn(I.fixtures) + getSelectionFixturePoints())+'</div>'+(getSelectionFixturePoints()>0?'<div class="sum-sub">base '+$(pn(I.fixtures))+' + sel +'+$(getSelectionFixturePoints())+'</div>':'')+'</div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">HVAC Tons</div><div class="sum-val">'+pn(I.hvacTons).toFixed(1)+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Paint SF</div><div class="sum-val">'+$(pn(I.paintSF))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Insulation SF</div><div class="sum-val">'+$(pn(I.insulationSF))+'</div></div>';
  h +=       '<div class="sum-box"><div class="sum-lbl">Flooring SF</div><div class="sum-val">'+$(pn(I.flooringSF))+'</div></div>';
  h +=     '</div>';
  h +=     '<table class="ps-table">';
  h +=       '<thead><tr><th>Trade</th><th style="text-align:right">Base Cost</th><th style="text-align:right">Upgrades</th><th style="text-align:right">Total</th></tr></thead>';
  h +=       '<tbody>';
  tradeRows.forEach(function(row){
    var upgStyle = row.upgAdder > 0 ? 'color:#B45309;font-weight:500' : (row.upgAdder < 0 ? 'color:var(--green-dark)' : 'color:var(--g400)');
    var upgText = row.upgAdder === 0 ? '–' : (row.upgAdder > 0 ? '+'+fmt(row.upgAdder) : '−'+fmt(Math.abs(row.upgAdder)));
    h +=     '<tr><td>'+esc(row.name)+'</td>';
    h +=       '<td class="cost">'+fmt(row.baseCost)+'</td>';
    h +=       '<td class="cost" style="'+upgStyle+'">'+upgText+'</td>';
    h +=       '<td class="cost" style="font-weight:600">'+fmt(row.total)+'</td>';
    h +=     '</tr>';
    (row.rates || []).forEach(function(rk){
      var rc = INT_RC[rk];
      if(!rc) return;
      var q = drivers[rc.driver] || 0;
      var lc = rc.rate * q;
      if(lc === 0 && row.baseCost === 0) return;
      h += '<tr style="font-size:11px;color:var(--g500)"><td style="padding-left:24px">'+esc(rc.label)+' <span class="mono">'+$(q)+' '+rc.unit+' × '+fmtC(rc.rate)+'</span></td><td class="cost" style="color:var(--g500)">'+fmt(lc)+'</td><td></td><td></td></tr>';
    });
  });
  h +=       '<tr class="ps-total"><td>INT BUDGET TOTAL</td><td class="cost">'+fmt(intBaseTotal)+'</td><td class="cost" style="color:#B45309">+'+ fmt(intUpgTotal)+'</td><td class="cost">'+fmt(intBaseTotal+intUpgTotal)+'</td></tr>';
  h +=       '</tbody>';
  h +=     '</table>';
  h +=   '</div>';
  h += '</div>';

  // PART F: Full Combined Budget
  var combinedTotal = ctrTotal + intBaseTotal + intUpgTotal;
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Part F · Combined Budget</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="field-row" style="gap:8px">';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Exterior Contractor</div><div class="kpi-val">'+fmt(ctrTotal)+'</div></div>';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Interior Base</div><div class="kpi-val">'+fmt(intBaseTotal)+'</div></div>';
  h +=       '<div class="kpi-box" style="flex:1"><div class="kpi-lbl">Interior Upgrades</div><div class="kpi-val" style="color:#B45309">+'+fmt(intUpgTotal)+'</div></div>';
  h +=     '</div>';
  h +=     '<div style="margin-top:12px"><div class="total-bar" style="font-size:16px"><span class="total-lbl">COMBINED TOTAL TRUE COST</span><span class="total-val">'+fmt(combinedTotal)+'</span></div></div>';
  h +=   '</div>';
  h += '</div>';

  // PART G: Budget PDF Buttons
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>Generate Budget PDFs</span></div>';
  h +=   '<div class="card-pad" style="display:flex;gap:10px;flex-wrap:wrap">';
  h +=     '<button class="nav-btn" style="flex:1;min-width:220px" onclick="printContractorPDF()">🔧 Contractor Labor PDF</button>';
  h +=     '<button class="nav-btn nav-next" style="flex:1;min-width:220px" onclick="printPMBudgetPDF()">📊 PM Budget PDF (3-page)</button>';
  h +=   '</div>';
  h +=   '<div style="padding:0 16px 14px;font-size:11px;color:var(--g500);line-height:1.5">Internal documents — not customer-facing. Opens your browser\'s native print dialog.</div>';
  h += '</div>';

  document.getElementById("stepContainer").innerHTML = h;
}

/* ── Contractor Override Handler ── */
function updCtrOverride(key, val){
  var numVal = pn(val);
  if(!STATE.ext.ctrOverrides) STATE.ext.ctrOverrides = {};
  // Find default qty for this key
  var defaults = buildCtrItems({ext:Object.assign({}, STATE.ext, {ctrOverrides:{}})});
  var dflt = 0;
  defaults.forEach(function(it){ if(it.key === key) dflt = it.qty; });
  if(numVal === dflt) delete STATE.ext.ctrOverrides[key];
  else STATE.ext.ctrOverrides[key] = numVal;
  // Live-update the row cost and grand total
  var items = buildCtrItems();
  items.forEach(function(it){
    if(it.key === key){
      var el = document.getElementById("ctr-cost-"+key);
      if(el) el.textContent = fmt(it.cost);
    }
  });
  var gt = document.getElementById("ctr-grand-total");
  if(gt) gt.textContent = fmt(sumItems(items));
  refreshLiveTotals();
}

/* ── PM Budget PDF (stub — builds 3-page) ── */
function printPMBudgetPDF(){
  if(!requireModel()) return;
  if(!STATE.int) initInteriorState();
  else applyIntMetrics();
  initCabUpgradesState(); initSelState();

  var I = STATE.int || {};
  var drivers = {
    livingSF:livSF(), cabLF:pn(I.cabLF), counterSF:pn(I.counterSF),
    drywallSF:pn(I.drywallSF), trimLF:pn(I.trimLF), doors:pn(I.doors),
    bathCount:pi(I.fullBaths)+pi(I.halfBaths), fixtures:pn(I.fixtures),
    hvacTons:pn(I.hvacTons), flat:1
  };
  var upgradesByTrade = computeUpgradesByTrade();
  var ctrItems = buildCtrItems();

  // Page 1: Trade Budget Summary
  var h = '<div class="ps-page">';
  h += buildPsHeader("PM Trade Budget Summary", {warning:"INTERNAL DOCUMENT — HIDDEN FROM CUSTOMER"});
  h += '<div style="background:#FEF3C7;border:1px solid #FDE68A;padding:8px 12px;margin:8px 0;font-size:11px;border-radius:4px">This page shows the budgeted cost (true cost) for each trade. PMs use this to track spend against budget per trade on this job.</div>';
  h += '<table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:8px">';
  h +=   '<thead><tr style="border-bottom:2px solid #333"><th style="text-align:left;padding:4px 6px">TRADE</th><th style="text-align:right;padding:4px 6px">BASE BUDGET</th><th style="text-align:right;padding:4px 6px">UPGRADES</th><th style="text-align:right;padding:4px 6px">TOTAL BUDGET</th></tr></thead>';
  h +=   '<tbody>';
  // Exterior trades
  var extSecs = ["Framing","Roof","Walls","Doors & Windows"];
  var extSheath = sumSection(ctrItems,"Sheathing");
  var extRoof = sumSection(ctrItems,"Roof") + extSheath;
  var extWalls = sumSection(ctrItems,"Walls");
  var extDW = sumSection(ctrItems,"Doors & Windows");
  var extOther = sumSection(ctrItems,"Other") + sumSection(ctrItems,"Stone") + sumSection(ctrItems,"Custom");
  var extFraming = sumSection(ctrItems,"Framing");
  function budgetRow(lbl, base, upg){
    var total = base + upg;
    var us = upg===0?'color:#aaa':'color:#B45309';
    var ut = upg===0?'–':(upg>0?'+'+fmt(upg):'−'+fmt(Math.abs(upg)));
    h += '<tr style="border-bottom:1px solid #eee"><td style="padding:4px 6px">'+esc(lbl)+'</td><td style="text-align:right;padding:4px 6px;font-family:monospace">'+fmt(base)+'</td><td style="text-align:right;padding:4px 6px;font-family:monospace;'+us+'">'+ut+'</td><td style="text-align:right;padding:4px 6px;font-family:monospace;font-weight:600">'+fmt(total)+'</td></tr>';
  }
  budgetRow("Framing", extFraming, 0);
  budgetRow("Roof (Sheathing + Metal)", extRoof, 0);
  budgetRow("Walls (Metal + Soffit)", extWalls, 0);
  budgetRow("Doors & Windows Install", extDW, 0);
  // Interior trades
  INT_TRADE_GROUPS.forEach(function(tg){
    var base = calcIntTradeBase(tg);
    var upg = upgradesByTrade[tg.key] || 0;
    budgetRow(tg.name, base, upg);
  });
  // Totals
  var extTotal = sumItems(ctrItems);
  var intTotal = 0; INT_TRADE_GROUPS.forEach(function(tg){ intTotal += calcIntTradeBase(tg) + (upgradesByTrade[tg.key]||0); });
  h += '<tr style="border-top:2px solid #333;background:#222;color:#fff;font-weight:700"><td style="padding:6px">TOTAL</td><td style="text-align:right;padding:6px;font-family:monospace">'+fmt(extTotal+intTotal-(upgradesByTrade?Object.values(upgradesByTrade).reduce(function(a,b){return a+b},0):0))+'</td><td></td><td style="text-align:right;padding:6px;font-family:monospace">'+fmt(extTotal+intTotal)+'</td></tr>';
  h +=   '</tbody></table>';
  h += '<div style="margin-top:12px;font-size:9px;color:#999">Generated from STC Interior Construction Tool — '+psDateStamp()+'</div>';
  h += '</div>';

  // Page 2: Line Item Detail
  h += '<div class="ps-page ps-page-break">';
  h += buildPsHeader("Trade Budget — Line Item Detail", {warning:"INTERNAL DOCUMENT"});
  INT_TRADE_GROUPS.forEach(function(tg){
    var base = calcIntTradeBase(tg);
    var upg = upgradesByTrade[tg.key] || 0;
    if(base === 0 && upg === 0) return;
    h += '<div style="margin-top:10px"><div style="color:#A31A1A;font-weight:700;font-size:11px;text-transform:uppercase;border-bottom:1px solid #A31A1A;padding-bottom:2px">'+esc(tg.name)+'</div>';
    // Drywall trade: add material estimate note (sheet count at 4×8 = 32 SF per sheet)
    if(tg.key === "drywall" && pn(I.drywallSF) > 0){
      var sheets = Math.ceil(pn(I.drywallSF) / 32);
      var sheetsWithWaste = Math.ceil(pn(I.drywallSF) * 1.10 / 32);
      h += '<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0 2px 12px;color:#0369A1;font-style:italic"><span>📋 Material estimate: '+sheets+' sheets (4\'×8\' @ 32 SF/sheet) · '+sheetsWithWaste+' sheets with 10% waste</span><span></span></div>';
    }
    (tg.rates||[]).forEach(function(rk){
      var rc = INT_RC[rk]; if(!rc) return;
      var q = drivers[rc.driver]||0;
      var lc = rc.rate*q;
      if(lc===0) return;
      h += '<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0 2px 12px;color:#555"><span>'+esc(rc.label)+' ('+$(q)+' '+rc.unit+' × '+fmtC(rc.rate)+')</span><span style="font-family:monospace">'+fmt(lc)+'</span></div>';
    });
    if(upg !== 0){
      h += '<div style="display:flex;justify-content:space-between;font-size:10px;padding:2px 0 2px 12px;color:#B45309"><span>Upgrades (true cost from selections)</span><span style="font-family:monospace">'+(upg>0?'+':'')+fmt(upg)+'</span></div>';
    }
    h += '</div>';
  });
  h += '<div style="margin-top:12px;font-size:9px;color:#999">Generated from STC Interior Construction Tool — '+psDateStamp()+'</div>';
  h += '</div>';

  // Page 3: Spend Tracking Grid
  h += '<div class="ps-page ps-page-break">';
  h += buildPsHeader("Spend Tracking (PM Use)", {warning:"INTERNAL DOCUMENT"});
  h += '<table style="width:100%;border-collapse:collapse;font-size:11px;margin-top:8px">';
  h +=   '<thead><tr style="border-bottom:2px solid #333"><th style="text-align:left;padding:4px 6px">TRADE</th><th style="text-align:right;padding:4px 6px">BUDGET</th><th style="text-align:right;padding:4px 6px;width:120px">ACTUAL SPENT</th><th style="text-align:right;padding:4px 6px;width:120px">REMAINING</th></tr></thead>';
  h +=   '<tbody>';
  INT_TRADE_GROUPS.forEach(function(tg){
    var total = calcIntTradeBase(tg) + (upgradesByTrade[tg.key]||0);
    if(total === 0) return;
    h += '<tr style="border-bottom:1px solid #eee"><td style="padding:4px 6px">'+esc(tg.name)+'</td><td style="text-align:right;padding:4px 6px;font-family:monospace">'+fmt(total)+'</td><td style="border-bottom:1px dotted #ccc"></td><td style="border-bottom:1px dotted #ccc"></td></tr>';
  });
  h +=   '</tbody></table>';
  h += '<div style="margin-top:12px;font-size:9px;color:#999">Generated from STC Interior Construction Tool — '+psDateStamp()+'</div>';
  h += '</div>';

  printToSheet(h);
}

/* ═══════════════════════════════════════════════════════════════
   STUB RENDERER — placeholder for Steps 2–9 (built in Steps 2 & 3 of the build plan)
   ═══════════════════════════════════════════════════════════════ */
function renderStepStub(){
  var sid = currentStepId();
  var lbl = STEP_DEFS[sid] ? STEP_DEFS[sid].label : "Step";
  var h = '';
  h += '<div class="card">';
  h +=   '<div class="section-hdr"><span>'+esc(lbl)+'</span><span class="badge">Step '+sid+'</span></div>';
  h +=   '<div class="card-pad">';
  h +=     '<div class="banner banner-info"><strong>Coming next.</strong> This step will be built in the next pass of the build plan. '
       +     'Step 1 is the scaffold + Customer & Model — Steps 2–4 (Exterior shell + concrete) and the Contract page come in build pass 2; '
       +     'interior steps come in pass 3+.</div>';
  h +=     '<div style="font-size:12px;color:var(--g600);margin-top:14px;line-height:1.6">';
  h +=       'Current STATE snapshot for this step:<br>';
  h +=       '<code style="font-family:var(--font-mono);font-size:11px;background:var(--g100);padding:10px;display:block;margin-top:6px;border-radius:6px;white-space:pre-wrap;word-break:break-word;max-height:280px;overflow:auto">'
       +     esc(JSON.stringify(stateSnapshotForStep(sid), null, 2))
       +     '</code>';
  h +=     '</div>';
  h +=   '</div>';
  h += '</div>';
  document.getElementById("stepContainer").innerHTML = h;
}

function stateSnapshotForStep(sid){
  if(sid === 2 || sid === 3) return {ext: STATE.ext};
  if(sid === 4) return {conc: STATE.conc};
  if(sid === 5) return {int: STATE.int, model: STATE.model};
  if(sid === 6) return {cabUpgrades: STATE.cabUpgrades, ct: STATE.ct};
  if(sid === 7) return {sel: STATE.sel};
  if(sid === 8) return {customer: STATE.customer, model: STATE.model, jobMode: STATE.jobMode, shellTotal: computeShellTotal()};
  if(sid === 9) return {budget: STATE.budget};
  return {};
}

/* ═══════════════════════════════════════════════════════════════
   LOCALSTORAGE AUTOSAVE (§ user directive — 500ms debounce)
   ═══════════════════════════════════════════════════════════════ */
var LS_AUTOSAVE_KEY = "stmc_wizard_autosave";
var saveTimer = null;
var lastAutosaveAt = 0;

function scheduleSave(){
  if(saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(doAutosave, 500);
  setSaveStatus("Unsaved…", false);
}

function doAutosave(){
  try{
    localStorage.setItem(LS_AUTOSAVE_KEY, JSON.stringify({state:STATE, ts:Date.now()}));
    lastAutosaveAt = Date.now();
    setSaveStatus("Autosaved "+relTime(lastAutosaveAt), true);
  } catch(e){
    setSaveStatus("Autosave failed", false);
  }
}

function setSaveStatus(txt, saved){
  var el = document.getElementById("footerSaveStatus");
  if(!el) return;
  el.textContent = txt;
  el.className = "footer-right"+(saved?" saved":"");
}

/* ── Reset all inputs for a new contract ── */
function resetAll(){
  if(!confirm("Clear all inputs and start a new contract? This cannot be undone.")) return;
  // Cancel any pending autosave timer so it can't overwrite the cleared state
  if(saveTimer){ clearTimeout(saveTimer); saveTimer = null; }
  localStorage.removeItem(LS_AUTOSAVE_KEY);
  STATE = defaultState();
  renderCurrentStep();
  setSaveStatus("Ready", true);
  showToast("Contract cleared — ready for new entry.");
}

/* ── Server-side contract save ── */
function saveContract(){
  var btn = document.getElementById("saveContractBtn");
  if(btn){ btn.disabled = true; btn.textContent = "Saving…"; }

  // Build draw rows from the same numbers renderStep8 uses
  var items      = buildSalesItems();
  var concItems  = buildConcItems();
  var concTotal  = sumItems(concItems);
  var custLabor  = sumItems(items) - concTotal;
  var p10        = pn(STATE.customer.p10);
  var shellTotal = p10 + custLabor + concTotal;
  var isShell    = STATE.jobMode === "shell";
  var deposit    = 2500;
  var draw1      = Math.max(0, p10 - deposit);
  var turnkeyTotal = 0;
  if(!isShell){
    var intContract = computeInteriorContractPrice ? computeInteriorContractPrice() : 0;
    turnkeyTotal = shellTotal + intContract;
  }
  var total = isShell ? shellTotal : turnkeyTotal;
  var draw4 = isShell ? 0 : Math.round(total * 0.20);
  var draw5 = isShell ? 0 : Math.round(total * 0.20);
  var draw6 = isShell ? 0 : Math.max(0, total - deposit - draw1 - concTotal - custLabor - draw4 - draw5);

  var tradeBudgets = [];
  var contractorBudget = Math.round(sumItems(buildCtrItems()));
  if(contractorBudget > 0){
    tradeBudgets.push({ trade: "Contractor Labor", budgeted: contractorBudget, actual: 0 });
  }

  if(!isShell){
    var upgradesByTrade = computeUpgradesByTrade();
    INT_TRADE_GROUPS.forEach(function(tg){
      var tradeBudget = Math.round(calcIntTradeBase(tg) + (upgradesByTrade[tg.key] || 0));
      if(tradeBudget > 0){
        tradeBudgets.push({ trade: tg.name, budgeted: tradeBudget, actual: 0 });
      }
    });
  }

  var budgetTotal = tradeBudgets.reduce(function(sum, row){ return sum + pn(row.budgeted); }, 0);

  var allDraws = [
    {n:0, l:"Good Faith Deposit",                   a: deposit},
    {n:1, l:"1st Home Draw (Loan Closing)",          a: draw1},
    {n:3, l:"2nd Home Draw (Concrete Completion)",   a: concTotal},
    {n:5, l:"3rd Home Draw (Framing Completion)",    a: custLabor},
    {n:6, l:"4th Home Draw (Rough-In)",             a: draw4},
    {n:7, l:"5th Home Draw (Drywall/Cabinets)",     a: draw5},
    {n:8, l:"6th Home Draw (Final/CO)",             a: draw6}
  ];
  var draws = allDraws.filter(function(d){ return d.a > 0; });

  var payload = {
    customer:     STATE.customer,
    model:        STATE.model,
    branch:       STATE.branch,
    jobMode:      STATE.jobMode,
    p10:          p10,
    shellTotal:   shellTotal,
    turnkeyTotal: turnkeyTotal,
    budgetTotal:  budgetTotal,
    tradeBudgets: tradeBudgets,
    draws:        draws,
    // When editing an existing row (lead conversion or Edit Contract), pass
    // the row's pk so the server updates-in-place instead of matching on
    // (customer_name, order_number). Server treats leadId/jobId the same.
    jobId:        window.STMC_EDIT_JOB_ID || null,
    // Full wizard STATE snapshot — server stores on Job.wizard_state
    // so Edit Contract can rehydrate the wizard with every field intact.
    rawState:     STATE
  };

  fetch("/stmc_ops/app/save-contract/", {
    method:  "POST",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": window.CSRF_TOKEN || ""
    },
    body:    JSON.stringify(payload)
  })
  .then(function(r){
    if (!r.ok) {
      return r.text().then(function(t){
        throw new Error("HTTP " + r.status + " — " + (t.slice(0, 120) || "request failed"));
      });
    }
    return r.json();
  })
  .then(function(data){
    if(data.ok){
      if(btn){ btn.textContent = "✅ Contract Saved!"; btn.style.background = "#1a6e3c"; }
      setSaveStatus("Contract saved to server", true);
    } else {
      if(btn){ btn.disabled = false; btn.textContent = "💾 Save Contract"; }
      alert("Save failed: " + (data.error || "unknown error"));
    }
  })
  .catch(function(err){
    if(btn){ btn.disabled = false; btn.textContent = "💾 Save Contract"; }
    alert("Network error saving contract: " + err);
  });
}

function relTime(ts){
  var d = new Date(ts);
  return d.toLocaleTimeString([], {hour:"2-digit", minute:"2-digit"});
}

function loadAutosave(){
  try{
    var raw = localStorage.getItem(LS_AUTOSAVE_KEY);
    if(!raw) return false;
    var data = JSON.parse(raw);
    if(!data || !data.state) return false;
    // Merge over default state to tolerate schema gaps between versions
    STATE = mergeDeep(defaultState(), data.state);
    return true;
  } catch(e){
    return false;
  }
}

function mergeDeep(a, b){
  if(b === null || b === undefined) return a;
  if(typeof b !== "object" || Array.isArray(b)) return b;
  var out = Array.isArray(a) ? a.slice() : Object.assign({}, a);
  Object.keys(b).forEach(function(k){
    if(b[k] !== null && typeof b[k] === "object" && !Array.isArray(b[k])){
      out[k] = mergeDeep(a && a[k] ? a[k] : {}, b[k]);
    } else {
      out[k] = b[k];
    }
  });
  return out;
}

/* ═══════════════════════════════════════════════════════════════
   STATE EXPORT / IMPORT (JSON) — share drafts between reps or with Matt
   ═══════════════════════════════════════════════════════════════ */
function exportStateJSON(){
  var json;
  try{ json = JSON.stringify(STATE, null, 2); }
  catch(e){ showToast("Export failed: "+e.message); return; }

  function success(){
    var label = (STATE.customer.name || STATE.model || "draft").trim();
    showToast("Copied to clipboard ("+json.length.toLocaleString()+" chars) — "+label);
  }

  // Modern API first
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(json).then(success, fallback);
  } else {
    fallback();
  }
  function fallback(){
    try{
      var ta = document.createElement("textarea");
      ta.value = json;
      ta.style.position = "fixed"; ta.style.top = "-2000px"; ta.setAttribute("readonly","");
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      if(ok) success();
      else showToast("Clipboard blocked — copy from the prompt manually.");
    } catch(e){
      showToast("Clipboard unavailable: "+e.message);
    }
  }
}

function importStateJSON(){
  var raw = prompt("Paste exported state JSON:");
  if(!raw) return;
  try{
    var parsed = JSON.parse(raw);
    if(!parsed || typeof parsed !== "object" || Array.isArray(parsed)){
      throw new Error("Not a JSON object");
    }
    // Merge over default state so missing keys (old exports) still work
    STATE = mergeDeep(defaultState(), parsed);
    // Snap to Step 1 if imported state points past the active flow
    var ids = activeStepIds();
    if(STATE._stepIdx >= ids.length) STATE._stepIdx = 0;
    renderCurrentStep();
    showToast("State imported — "+(STATE.customer.name||STATE.model||"untitled"));
  } catch(e){
    showToast("Import failed: "+e.message);
  }
}

/* ═══════════════════════════════════════════════════════════════
   PAGE INIT
   ═══════════════════════════════════════════════════════════════ */
(function init(){
  if(__WIZ_MISSING_KEYS.length){
    renderWizardConfigError();
    return;
  }
  // Edit-from-server hydration: if the page embedded an existing STATE
  // payload (sales_shell_edit / sales_turnkey_edit), deep-merge it over
  // defaults BEFORE any autosave restore so the stored contract wins.
  var editSeeded = false;
  try {
    if (window.STMC_EDIT_STATE && typeof window.STMC_EDIT_STATE === "object" && Object.keys(window.STMC_EDIT_STATE).length) {
      STATE = mergeDeep(defaultState(), window.STMC_EDIT_STATE);
      var ids = activeStepIds();
      if (STATE._stepIdx >= ids.length) STATE._stepIdx = 0;
      editSeeded = true;
    }
  } catch (e) { /* fall through to autosave */ }

  // Fall back to autosave only when not editing an existing contract.
  var restored = false;
  if (!editSeeded) {
    restored = loadAutosave();
  }

  if(__WIZ_DEFAULT_MODE === "shell" || __WIZ_DEFAULT_MODE === "turnkey"){
    if (!editSeeded) STATE.jobMode = __WIZ_DEFAULT_MODE;
    if(STATE._stepIdx >= activeStepIds().length) STATE._stepIdx = 0;
  }
  renderCurrentStep();
  if (editSeeded) {
    showToast("Editing contract — "+(STATE.customer.name || STATE.model || "saved draft"));
  } else if (restored) {
    showToast("Session restored from autosave.");
  }
})();
