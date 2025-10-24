import streamlit as st
import pandas as pd
import datetime as dt
import os
import base64
from typing import List, Dict, Tuple

# Optional: Supabase for cloud persistence (auto if secrets exist)
try:
    from supabase import create_client, Client  # pip install supabase
except Exception:
    create_client = None
    Client = None

# Optional: Supabase for cloud persistence (auto if secrets exist)
try:
    from supabase import create_client, Client  # pip install supabase
except Exception:
    create_client = None
    Client = None

# ──────────────────────────────────────────────────────────────
# CONFIG & THEME (+ optional Supabase cloud storage) (+ optional Supabase cloud storage)
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="🏋️ Training Adventure", page_icon="💪", layout="wide")
LOG_FILE = "workout_log.csv"            # per-set/per-task log
XP_LOG_FILE = "xp_log.csv"              # XP gamification log
TEMPLATE_FILE = "split_template.csv"    # exportable plan

# Optional local avatar folder (drop your own images here)
AVATAR_FOLDER = "avatars"
AVATARS = {
    0: ("rookie", "Rookie"),
    1: ("cadet", "Cadet"),
    2: ("contender", "Contender"),
    3: ("warrior", "Warrior"),
    4: ("champion", "Champion"),
    5: ("legend", "Legend"),
}
LEVEL_THRESHOLDS = [
    (0, 0), (1, 150), (2, 350), (3, 650), (4, 1050), (5, 1600)
]

# XP awards (rough heuristic)
XP = {
    "compound": 12,
    "unilateral": 10,
    "isolation": 8,
    "core": 10,
    "erectors": 10,
    "balance": 8,
    "grip": 8,
    "core/grip": 10,
}

# ──────────────────────────────────────────────────────────────
# PROGRAM (PPL A/B with core, balance, grip, erectors)
# rep tuples are (min_reps, max_reps). None => time/steps target in `duration`.
# `tip` shows a concise cue; `icon` decorates the UI.
SPLIT: Dict[str, List[Dict]] = {
    "Push A — Chest + Triceps + Core": [
        {"exercise": "Barbell Bench Press", "sets": 4, "reps": (6, 8), "category": "compound", "icon": "🏋️", "tip": "Elbows ~45°, 2–3s eccentric"},
        {"exercise": "Incline Dumbbell Press", "sets": 3, "reps": (8, 10), "category": "compound", "icon": "📈", "tip": "Slight arch, deep stretch"},
        {"exercise": "Machine/Cable Fly", "sets": 3, "reps": (12, 15), "category": "isolation", "icon": "🦋", "tip": "Hug a tree, squeeze"},
        {"exercise": "Overhead DB Triceps Extension", "sets": 3, "reps": (10, 12), "category": "isolation", "icon": "🎯", "tip": "Long head stretch"},
        {"exercise": "Seated DB Lateral Raise", "sets": 3, "reps": (15, 20), "category": "isolation", "icon": "🏹", "tip": "Lead with elbows"},
        {"exercise": "Rope Pushdown", "sets": 3, "reps": (12, 15), "category": "isolation", "icon": "🪢", "tip": "Flare rope at bottom"},
        {"exercise": "Weighted Decline Sit-Up", "sets": 3, "reps": (10, 12), "category": "core", "icon": "🧱", "tip": "Ribs to pelvis"},
        {"exercise": "Pallof Press", "sets": 3, "reps": (12, 15), "category": "core", "icon": "🧭", "tip": "Resist rotation"},
    ],
    "Pull A — Back Thickness + Biceps + Grip": [
        {"exercise": "Barbell Row / Pendlay", "sets": 4, "reps": (6, 8), "category": "compound", "icon": "🛠️", "tip": "Torso ~15°, brace"},
        {"exercise": "Weighted Pull-Up / Lat Pulldown", "sets": 4, "reps": (8, 10), "category": "compound", "icon": "🧗", "tip": "Drive elbows to hips"},
        {"exercise": "Chest-Supported Row", "sets": 3, "reps": (10, 12), "category": "compound", "icon": "🧱", "tip": "No momentum"},
        {"exercise": "Seated Cable Row", "sets": 3, "reps": (10, 12), "category": "compound", "icon": "🎣", "tip": "Pause at chest"},
        {"exercise": "Barbell Curl", "sets": 3, "reps": (8, 10), "category": "isolation", "icon": "🌀", "tip": "Pin elbows"},
        {"exercise": "Hammer Curl", "sets": 3, "reps": (10, 12), "category": "isolation", "icon": "🔨", "tip": "Neutral grip"},
        {"exercise": "Farmer's Carry (steps)", "sets": 3, "reps": None, "duration": 40, "category": "grip", "icon": "🧺", "tip": "Tall, tight ribs"},
    ],
    "Legs A — Quads + Balance + Core": [
        {"exercise": "Front / Safety Bar Squat", "sets": 4, "reps": (6, 8), "category": "compound", "icon": "🧊", "tip": "Upright torso, brace"},
        {"exercise": "Bulgarian Split Squat (supported)", "sets": 3, "reps": (10, 12), "category": "unilateral", "icon": "🦵", "tip": "Use post for balance"},
        {"exercise": "Walking Lunge / Step-Up", "sets": 3, "reps": (10, 10), "category": "unilateral", "icon": "🚶", "tip": "Knee tracks toes"},
        {"exercise": "Leg Extension", "sets": 3, "reps": (12, 15), "category": "isolation", "icon": "🦿", "tip": "Squeeze at top"},
        {"exercise": "Hanging Leg Raise / Ab Rollout", "sets": 3, "reps": (12, 15), "category": "core", "icon": "🏗️", "tip": "Posterior tilt"},
        {"exercise": "Pallof Press", "sets": 3, "reps": (12, 15), "category": "core", "icon": "🧭", "tip": "Neutral pelvis"},
        {"exercise": "Single-Leg Balance Reach (opt)", "sets": 2, "reps": (10, 10), "category": "balance", "icon": "🦶", "tip": "Soft knee, hinge"},
    ],
    "Push B — Shoulders + Triceps + Core": [
        {"exercise": "Standing Overhead Press", "sets": 4, "reps": (6, 8), "category": "compound", "icon": "📏", "tip": "Glutes tight, chin back"},
        {"exercise": "Arnold Press", "sets": 3, "reps": (8, 10), "category": "compound", "icon": "🎛️", "tip": "Full ROM"},
        {"exercise": "DB Lateral Raise (slow ecc)", "sets": 3, "reps": (15, 20), "category": "isolation", "icon": "🌙", "tip": "2–3s down"},
        {"exercise": "Machine Chest Press", "sets": 3, "reps": (10, 12), "category": "compound", "icon": "🛡️", "tip": "Neutral grip"},
        {"exercise": "Cable Lateral Raise (1-arm)", "sets": 3, "reps": (12, 15), "category": "isolation", "icon": "🎯", "tip": "Constant tension"},
        {"exercise": "Skullcrusher / Rope Ext.", "sets": 3, "reps": (10, 12), "category": "isolation", "icon": "💥", "tip": "Elbows still"},
        {"exercise": "Cable Woodchop (per side)", "sets": 3, "reps": (12, 12), "category": "core", "icon": "🪓", "tip": "Hips quiet"},
        {"exercise": "Side Plank Hip Raise (sec)", "sets": 3, "reps": None, "duration": 30, "category": "core", "icon": "🧱", "tip": "Ribs down"},
    ],
    "Pull B — Width + Posterior + Grip + Lower Back": [
        {"exercise": "Wide-Grip Pull-Up / Pulldown", "sets": 4, "reps": (6, 10), "category": "compound", "icon": "🦅", "tip": "Drive scapular depression"},
        {"exercise": "T-Bar / Machine Row", "sets": 4, "reps": (8, 10), "category": "compound", "icon": "⚓", "tip": "Chest up"},
        {"exercise": "Single-Arm DB Row", "sets": 3, "reps": (10, 12), "category": "unilateral", "icon": "🧲", "tip": "Shoulder square"},
        {"exercise": "Reverse Fly / Face Pull", "sets": 3, "reps": (15, 20), "category": "isolation", "icon": "🎣", "tip": "ER + scap set"},
        {"exercise": "Preacher Curl", "sets": 3, "reps": (10, 12), "category": "isolation", "icon": "🧪", "tip": "No shoulder swing"},
        {"exercise": "Zottman / Reverse Curl", "sets": 3, "reps": (12, 15), "category": "forearms", "icon": "🔁", "tip": "Slow negative"},
        {"exercise": "Back Extension (weighted)", "sets": 3, "reps": (15, 20), "category": "erectors", "icon": "🧱", "tip": "Neutral spine"},
        {"exercise": "Plate Pinch Hold (sec)", "sets": 3, "reps": None, "duration": 45, "category": "grip", "icon": "📀", "tip": "Thumbs crush"},
    ],
    "Legs B — Glutes + Hamstrings + Lower Back + Core": [
        {"exercise": "Romanian Deadlift", "sets": 4, "reps": (6, 8), "category": "compound", "icon": "🪵", "tip": "Hinge; shins vertical"},
        {"exercise": "Seated Good Morning", "sets": 3, "reps": (10, 12), "category": "erectors", "icon": "🪑", "tip": "Brace, move hips"},
        {"exercise": "Hip Thrust / Glute Bridge", "sets": 3, "reps": (10, 12), "category": "compound", "icon": "🍑", "tip": "Posterior tilt"},
        {"exercise": "Hamstring Curl", "sets": 3, "reps": (10, 15), "category": "isolation", "icon": "🧵", "tip": "Toes neutral"},
        {"exercise": "Weighted Side Plank (sec)", "sets": 3, "reps": None, "duration": 30, "category": "core", "icon": "🧱", "tip": "Hips stacked"},
        {"exercise": "Back Extension / Reverse Hyper", "sets": 3, "reps": (15, 20), "category": "erectors", "icon": "🔁", "tip": "Control end-range"},
        {"exercise": "Ab Wheel Rollout", "sets": 3, "reps": (10, 15), "category": "core", "icon": "🛞", "tip": "Ribs down"},
        {"exercise": "Suitcase Carry (steps)", "sets": 3, "reps": None, "duration": 40, "category": "core/grip", "icon": "🧳", "tip": "Anti-lean"},
    ],
}

# ──────────────────────────────────────────────────────────────
# STYLING (vibes like your piano tracker)
# ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      html, body, .stApp, .block-container {background: #f5f2e8 url('https://www.transparenttextures.com/patterns/beige-paper.png') repeat;}
      .big-title{font-size:56px;font-family:'Merriweather',serif;color:#2f3b2f;text-align:center;font-weight:800;margin:32px 0 8px}
      .menu-bar{display:flex;justify-content:center;gap:28px;margin:6px auto 24px;padding:12px 0;background:#4b5f49;border-bottom:4px solid #8b5e3c;border-radius:10px;width:92%;box-shadow:0 4px 12px rgba(0,0,0,0.2);position:sticky;top:0;z-index:1000}
      .menu-bar a{color:#fff!important;font-weight:700;text-decoration:none!important;padding:0 10px}
      .menu-bar a:hover{color:#f0d07a!important}
      .card{border:1px solid #8b5e3c;border-radius:14px;padding:14px;margin:10px 0;background:#faf7f0;box-shadow:0 6px 16px rgba(0,0,0,0.18)}
      .xp-bar{height:26px;width:100%;background:#ddd;border-radius:14px;overflow:hidden;margin:10px 0}
      .xp-fill{height:100%;background:linear-gradient(90deg,#f9d423,#ff4e50);text-align:center;color:#000;font-weight:700;line-height:26px}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("""
<div class='menu-bar'>
  <a href='#plan'>📋 Plan</a>
  <a href='#log'>📝 Log</a>
  <a href='#progress'>📊 Progress</a>
  <a href='#avatar'>🧟 Avatar</a>
</div>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>💪 Training Adventure</div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# DATA IO  (Supabase if configured; else CSV)  (Supabase if configured; else CSV)
# ──────────────────────────────────────────────────────────────
DEFAULT_LOG_COLUMNS = [
    "date","week","day_name","exercise","set_number","reps","weight","rir","tempo","notes","est_1rm","volume","xp"
]

def load_csv(path: str, cols: List[str]) -> pd.DataFrame:
    if os.path.exists(path):
        df = pd.read_csv(path)
        for c in cols:
            if c not in df.columns:
                df[c] = None
        return df
    return pd.DataFrame(columns=cols)


def save_csv(df: pd.DataFrame, path: str):
    df.to_csv(path, index=False)

# --- Supabase helpers ---
@st.cache_resource(show_spinner=False)
def supabase_client():
    url = st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None
    key = st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None
    if 'create_client' in globals() and create_client and url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None

SUPA = supabase_client()
USE_SUPABASE = SUPA is not None
WORKOUT_TABLE = "workout_log"
XP_TABLE = "xp_log"

# --- Supabase helpers ---
@st.cache_resource(show_spinner=False)
def supabase_client():
    url = st.secrets.get("SUPABASE_URL") if hasattr(st, "secrets") else None
    key = st.secrets.get("SUPABASE_KEY") if hasattr(st, "secrets") else None
    if 'create_client' in globals() and create_client and url and key:
        try:
            return create_client(url, key)
        except Exception:
            return None
    return None

SUPA = supabase_client()
USE_SUPABASE = SUPA is not None
WORKOUT_TABLE = "workout_log"
XP_TABLE = "xp_log"


def epley_1rm(reps: float, weight: float) -> float:
    try:
        reps = float(reps); weight = float(weight)
        return weight if reps <= 1 else weight * (1 + reps/30)
    except: return 0.0


def todays_week_number() -> int:
    today = dt.date.today(); monday = today - dt.timedelta(days=today.weekday())
    return 1 + (today - monday).days // 7  # simple anchor

# ──────────────────────────────────────────────────────────────
# XP / LEVELS
# ──────────────────────────────────────────────────────────────

def total_xp() -> int:
    if USE_SUPABASE:
        try:
            res = SUPA.table(XP_TABLE).select("xp").execute()
            return int(sum([r.get("xp", 0) for r in (res.data or [])]))
        except Exception:
            pass
    df = load_csv(XP_LOG_FILE, ["date","task","xp"])
    return int(df["xp"].sum()) if not df.empty else 0


def award_xp(task: str, xp_amount: int):
    df = load_csv(XP_LOG_FILE, ["date","task","xp"])
    row = {"date": str(dt.date.today()), "task": task, "xp": int(xp_amount)}
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    save_csv(df, XP_LOG_FILE)


def current_level_and_progress() -> Tuple[int,int,int]:
    xp = total_xp()
    level = 0
    for lv, need in LEVEL_THRESHOLDS:
        if xp >= need: level = lv
    cur_need = next((need for lv,need in LEVEL_THRESHOLDS if lv==level), 0)
    next_need = next((need for lv,need in LEVEL_THRESHOLDS if lv==level+1), cur_need)
    progress = 0 if next_need==cur_need else int( (xp-cur_need) / (next_need-cur_need) * 100 )
    return level, xp, progress


def avatar_display(level:int):
    key,title = AVATARS.get(level, ("rookie","Rookie"))
    local_path = os.path.join(AVATAR_FOLDER, f"{key}.png")
    st.markdown("<a name='avatar'></a>", unsafe_allow_html=True)
    st.header("🧟 Your Training Avatar")
    if os.path.exists(local_path):
        with open(local_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
            st.markdown(f"<div style='text-align:center'><img src='data:image/png;base64,{encoded}' width='260' style='border-radius:16px;border:5px solid #8b5e3c;box-shadow:0 10px 25px rgba(0,0,0,0.25)'/><p style='font-size:22px;font-weight:700;color:#2f3b2f'>{title}</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='card' style='text-align:center'>🥇 <b>{title}</b> — drop an image in ./avatars/{key}.png to customize.</div>", unsafe_allow_html=True)

# XP header
level, totalxp, pct = current_level_and_progress()
st.markdown(f"### ⭐ Level {level} | Total XP: {totalxp}")
st.markdown(f"""
<div class='xp-bar'><div class='xp-fill' style='width:{pct}%'>{pct}%</div></div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# PLAN VIEW (select day -> see what to do; checkbox to award XP)
# ──────────────────────────────────────────────────────────────
st.markdown("<a name='plan'></a>", unsafe_allow_html=True)
st.header("📋 Plan — Pick a Training Day")

all_days = list(SPLIT.keys())
sel_day = st.selectbox("Choose workout", all_days)

plan_cols = st.columns(2)
with plan_cols[0]:
    st.subheader(sel_day)
    for block in SPLIT[sel_day]:
        rep = block.get("reps")
        rep_str = f"{rep[0]}–{rep[1]} reps" if rep else f"{block.get('duration','—')} sec/steps"
        icon = block.get("icon", "•")
        tip = block.get("tip", "")
        st.markdown(f"<div class='card'> {icon} <b>{block['exercise']}</b> — {block['sets']} × {rep_str}<br><span style='opacity:.8'>{tip}</span></div>", unsafe_allow_html=True)

with plan_cols[1]:
    st.subheader("Quick XP check-off ✅")
    st.caption("Tick what you completed today to add XP (you can still log detailed sets on the Log page).")
    for block in SPLIT[sel_day]:
        done = st.checkbox(f"{block.get('icon','•')} {block['exercise']}", key=f"xp_{sel_day}_{block['exercise']}")
        if done:
            gained = XP.get(block["category"], 6)
            award_xp(block['exercise'], gained)
            st.success(f"+{gained} XP — {block['exercise']}")

# ──────────────────────────────────────────────────────────────
# LOG PAGE (detailed logging w/ est 1RM & volume)
# ──────────────────────────────────────────────────────────────
st.markdown("<a name='log'></a>", unsafe_allow_html=True)
st.header("📝 Log Workout (sets/reps/weight/RIR)")
log_df = (pd.DataFrame(SUPA.table(WORKOUT_TABLE).select("*").order("id").execute().data) if USE_SUPABASE else load_csv(LOG_FILE, DEFAULT_LOG_COLUMNS))

log_day = st.selectbox("Training day", all_days, index=all_days.index(sel_day))
exercises = [x["exercise"] for x in SPLIT[log_day]]
log_ex = st.selectbox("Exercise", exercises)
# show target
rng = next((x.get("reps") for x in SPLIT[log_day] if x["exercise"]==log_ex), None)
if rng: st.info(f"Target: {rng[0]}–{rng[1]} reps (double progression)")
else: st.info("Time/steps based — log duration in notes.")

col1,col2,col3 = st.columns(3)
with col1: date = st.date_input("Date", value=dt.date.today())
with col2: week = st.number_input("Week #", min_value=1, value=todays_week_number(), step=1)
with col3: num_sets = st.number_input("How many sets?", 1, 10, 3)

new_rows = []
for s in range(1, num_sets+1):
    with st.expander(f"Set {s}"):
        reps = st.number_input("Reps", 0, 100, 0, key=f"reps_{s}")
        weight = st.number_input("Weight", 0.0, 2000.0, 0.0, step=2.5, key=f"wt_{s}")
        rir = st.number_input("RIR", 0.0, 10.0, 2.0, step=0.5, key=f"rir_{s}")
        tempo = st.text_input("Tempo (e.g., 3-0-1)", key=f"tempo_{s}")
        notes = st.text_input("Notes", key=f"notes_{s}")
        est = round(epley_1rm(reps, weight),2)
        vol = (weight or 0)*(reps or 0)
        cat = next((x['category'] for x in SPLIT[log_day] if x['exercise']==log_ex), 'compound')
        set_xp = XP.get(cat, 6)
        st.caption(f"Est 1RM: {est} • Volume: {vol} • XP on save: +{set_xp}")
        new_rows.append({"date":str(date),"week":week,"day_name":log_day,"exercise":log_ex,
                         "set_number":s,"reps":reps,"weight":weight,"rir":rir,"tempo":tempo,
                         "notes":notes,"est_1rm":est,"volume":vol,"xp":set_xp})

if st.button("✅ Save Sets"):
    if new_rows:
        if USE_SUPABASE:
            try:
                SUPA.table(WORKOUT_TABLE).insert(new_rows).execute()
                log_df = pd.DataFrame(SUPA.table(WORKOUT_TABLE).select("*").order("id").execute().data)
            except Exception as e:
                st.error(f"Supabase insert failed: {e}")
        else:
            log_df = pd.concat([log_df, pd.DataFrame(new_rows)], ignore_index=True)
            save_csv(log_df, LOG_FILE)
        # award XP total for these sets
        total_award = sum(r["xp"] for r in new_rows)
        award_xp(f"{log_ex} sets", total_award)
        st.success(f"Saved {len(new_rows)} set(s). Awarded +{total_award} XP.")

st.subheader("Recent Entries")
st.dataframe(log_df.tail(20), use_container_width=True)
cols_dl = st.columns(2)
with cols_dl[0]:
    if st.button("↩️ Undo Last Entry"):
        if not log_df.empty:
            if USE_SUPABASE and "id" in log_df.columns:
                try:
                    last_id = int(log_df.iloc[-1]["id"])  # assumes serial id in Supabase
                    SUPA.table(WORKOUT_TABLE).delete().eq("id", last_id).execute()
                    log_df = pd.DataFrame(SUPA.table(WORKOUT_TABLE).select("*").order("id").execute().data)
                    st.warning("Removed last entry from Supabase.")
                except Exception as e:
                    st.error(f"Failed to delete from Supabase: {e}")
            else:
                save_csv(log_df.iloc[:-1], LOG_FILE)
                st.warning("Removed last entry from CSV (XP not auto-removed).")
        else:
            st.info("Log is empty.")
with cols_dl[1]:
    if not log_df.empty:
        st.download_button("⬇️ Download full CSV", data=log_df.to_csv(index=False), file_name="workout_log_export.csv", mime="text/csv")

# ──────────────────────────────────────────────────────────────
# PROGRESS (charts + PRs + targets)
# ──────────────────────────────────────────────────────────────
st.markdown("<a name='progress'></a>", unsafe_allow_html=True)
st.header("📊 Progress & PRs")
prog = (pd.DataFrame(SUPA.table(WORKOUT_TABLE).select("*").order("id").execute().data) if USE_SUPABASE else load_csv(LOG_FILE, DEFAULT_LOG_COLUMNS))
if prog.empty:
    st.info("No data yet — log a session above.")
else:
    c1,c2 = st.columns(2)
    with c1:
        exs = sorted(prog["exercise"].dropna().unique())
        ex = st.selectbox("Exercise", exs)
    with c2:
        metric = st.selectbox("Metric", ["weight","reps","volume","est_1rm"]) 

    ex_df = prog[prog["exercise"]==ex].copy()
    ex_df["session"] = pd.to_datetime(ex_df["date"]).dt.date
    if metric == "volume":
        series = ex_df.groupby("session")["volume"].sum()
    elif metric == "est_1rm":
        series = ex_df.groupby("session")["est_1rm"].max()
    else:
        series = ex_df.groupby("session")[metric].mean()
    st.line_chart(series)

    st.markdown("### Best Sets (last 90 days)")
    recent = ex_df[pd.to_datetime(ex_df["date"]) >= (pd.Timestamp.today() - pd.Timedelta(days=90))]
    best = recent.sort_values(["est_1rm","volume"], ascending=False).head(10)
    st.dataframe(best[["date","exercise","reps","weight","est_1rm","volume","notes"]])

# ──────────────────────────────────────────────────────────────
# AVATAR SECTION
# ──────────────────────────────────────────────────────────────
avatar_display(level)

# ──────────────────────────────────────────────────────────────
# TEMPLATE EXPORT
# ──────────────────────────────────────────────────────────────
if st.button("⬇️ Export Weekly Template CSV"):
    rows = []
    for day, items in SPLIT.items():
        for it in items:
            r = it.get("reps"); rep_str = "time" if r is None else f"{r[0]}-{r[1]}"
            rows.append({"day":day,"exercise":it["exercise"],"sets":it["sets"],"reps":rep_str,"category":it["category"]})
    pd.DataFrame(rows).to_csv(TEMPLATE_FILE, index=False)
    st.success(f"Saved {TEMPLATE_FILE} in this folder.")

# ──────────────────────────────────────────────────────────────
# CLOUD STORAGE INFO / FOOTER — bulletproof no-quote version
# ──────────────────────────────────────────────────────────────

if USE_SUPABASE:
    st.markdown("🔗 **Cloud storage is ON (Supabase).** Logs persist & sync across devices.")
    st.markdown(
        """
**Add to Streamlit Secrets:**
- `SUPABASE_URL = https://YOUR-project.supabase.co`
- `SUPABASE_KEY = YOUR-ANON-KEY`

**SQL schema (run once in Supabase):**
        """
    )

    st.code(
        """create table if not exists workout_log (
  id bigserial primary key,
  date text,
  week int,
  day_name text,
  exercise text,
  set_number int,
  reps int,
  weight float8,
  rir float8,
  tempo text,
  notes text,
  est_1rm float8,
  volume float8,
  xp int
);

create table if not exists xp_log (
  id bigserial primary key,
  date text,
  task text,
  xp int
);
""",
        language="sql",
    )

else:
    st.warning(
        "💾 Using local CSV files (no cloud). On Streamlit Cloud these may reset — "
        "use Download, or configure Supabase in Secrets to enable cloud sync."
    )

st.caption(
    "Built for Dylan • PPL A/B • Core 3–4×/wk • Erectors 2×/wk • Grip integrated • XP system inspired by your Piano Tracker."
)
