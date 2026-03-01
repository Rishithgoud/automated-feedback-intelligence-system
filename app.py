from flask import Flask, render_template, request, redirect, session, jsonify
import sqlite3, os, datetime
from textblob import TextBlob
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from flask import send_file
import io

ISSUE_ACTION_MAP = {
    "Payment Delay": [
        "Expedite fund disbursement through treasury coordination",
        "Introduce district-level payment monitoring dashboards"
    ],
    "Partial Payment": [
        "Audit beneficiary payment records",
        "Ensure correct amount mapping in DBT systems"
    ],
    "Application Delay": [
        "Reduce approval backlog at mandal offices",
        "Introduce time-bound verification deadlines"
    ],
    "Verification Delay": [
        "Increase verification staff temporarily",
        "Digitize verification workflow"
    ],
    "Eligibility Confusion": [
        "Publish simplified eligibility guidelines",
        "Conduct village-level awareness camps"
    ],
    "Lack of Awareness": [
        "Strengthen IEC campaigns",
        "Use local language outreach materials"
    ]
}

app = Flask(__name__)
app.secret_key = "dev_secret_key"

# ================= DATABASE =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "feedback.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_email TEXT,
        state TEXT,
        district TEXT,
        mandal TEXT,
        village TEXT,
        scheme TEXT,
        feedback TEXT,
        sentiment TEXT,
        issue TEXT,
        created_at DATE,
        notify INTEGER DEFAULT 0,
        viewed INTEGER DEFAULT 0,
        viewed_at DATE
    )
    """)

    conn.commit()
    conn.close()
init_db()
# ================= SCHEME DATA =================
SCHEME_DATA = {
    "Telangana": {
       "Hyderabad": {
            "Gachibowli Mandal": {
                "Gachibowli": ["PM Awas Yojana", "Ayushman Bharat", "Rythu Bandhu"]
                                 }
                    },
        "Warangal": {},
        "Karimnagar": {},
        "Nizamabad": {},
        "Khammam": {},
        "Rangareddy": {},
        "Medchal Malkajgiri": {},
        "Sangareddy": {},
        "Siddipet": {},
        "Nalgonda": {},
       "Suryapet": {},
       "Mahabubnagar": {},
        "Adilabad": {},
       "Mancherial": {},
        "Nirmal": {},
        "Jagitial": {},
        "Peddapalli": {},
        "Rajanna Sircilla": {},
        "Jayashankar Bhupalpally": {},
        "Mulugu": {},
        "Bhadradri Kothagudem": {},
        "Kumuram Bheem Asifabad": {},
        "Nagarkurnool": {},
        "Narayanpet": {},
        "Jogulamba Gadwal": {},
        "Wanaparthy": {},
        "Vikarabad": {},
        "Medak": {},
        "Mahabubabad": {},
        "Jangaon": {},
        "Yadadri Bhuvanagiri": {},
        "Hanumakonda": {}
    }
}

# ================= NLP =================
def analyze_sentiment(text):
    p = TextBlob(text).sentiment.polarity
    if p > 0.1:
        return "positive"
    if p < -0.1:
        return "negative"
    return "neutral"

def classify_issue_policy(text):
    t = text.lower()

    ISSUE_RULES = {
        "Payment & Money Problems": [
            "money", "payment", "amount", "credited", "salary", "fund",
            "subsidy", "not received", "less amount", "transaction", "bank"
        ],

        "Corruption & Bribe Problems": [
            "bribe", "commission", "corrupt", "middleman", "favor",
            "fake", "misuse", "illegal"
        ],

        "Awareness & Information Problems": [
            "not aware", "don’t know", "dont know", "no information",
            "no guidance", "no details", "awareness", "help desk"
        ],

        "Registration & Document Problems": [
            "apply", "application", "documents", "aadhaar",
            "biometric", "verification", "rejected"
        ],

        "Technology & Online System Problems": [
            "website", "portal", "server", "otp",
            "login", "app", "online", "digital"
        ],

        "Infrastructure & Facility Problems": [
            "building", "facility", "hospital",
            "road", "equipment", "maintenance"
        ],

        "Service Quality & Staff Behavior Problems": [
            "staff", "rude", "not helpful",
            "absent", "behavior", "discrimination"
        ],

        "Delay & Process Problems": [
            "delay", "late", "pending",
            "slow", "takes time", "long time"
        ],

        "Coverage & Eligibility Problems": [
            "eligible", "not eligible", "rejected",
            "wrong people", "not included", "coverage"
        ],

        "Quality of Benefit Problems": [
            "poor quality", "bad quality",
            "food quality", "house quality", "medicine"
        ],

        "Accessibility Problems": [
            "far", "distance", "transport",
            "timing", "disabled", "elderly", "language"
        ],

        "Monitoring, Transparency & Accountability Problems": [
            "status not visible", "no transparency",
            "monitoring", "no response", "no update"
        ],

        "Grievance (Complaint) Problems": [
            "complaint", "no response",
            "not solved", "closed without solution"
        ],

        "Scheme Design & Policy Problems": [
            "rules", "policy", "benefit low",
            "criteria strict", "work days"
        ],

        "Equality & Social Inclusion Problems": [
            "women", "poor", "caste",
            "community", "discrimination"
        ],

        "Operational & Implementation Problems": [
            "implementation", "mismanage",
            "staff shortage", "department", "coordination"
        ],

        "Data & Record Problems": [
            "wrong data", "duplicate",
            "missing record", "not updated"
        ],

        "Trust & Satisfaction Problems": [
            "not satisfied", "no trust",
            "bad experience", "lost faith"
        ]
    }

    for issue, keywords in ISSUE_RULES.items():
        if any(k in t for k in keywords):
            return issue

    return "Other / Unclassified Issues"


def severity_from_count(count):
    if count >= 15:
        return "High"
    if count >= 7:
        return "Medium"
    return "Low"

def generate_overall_ai_summary(state, district, mandal, village, scheme, feedback_rows):
    """
    feedback_rows: list of dicts with keys -> sentiment, issue
    """

    total = len(feedback_rows)

    if total == 0:
        return f"""
Scheme: {scheme}
Region: {state} → {district} → {mandal} → {village}

Current Status:
No public feedback has been recorded yet for this scheme in the selected region.

AI Executive Insight:
It is recommended to improve awareness and encourage citizens to submit feedback
to enable performance monitoring and corrective action.
""".strip()
def overall_executive_summary(state, district, mandal, village, scheme, issues):

    if not issues:
        return f"""
SCHEME: {scheme}
REGION: {village}, {mandal}, {district}, {state}

No significant issues reported so far.
Current implementation appears stable.
""".strip()

    top_issue = max(issues, key=issues.get)
    total = sum(issues.values())
    impact = round((issues[top_issue] / total) * 100, 1)

    severity = (
        "High" if impact >= 40 else
        "Moderate" if impact >= 20 else
        "Low"
    )

    return f"""
SCHEME: {scheme}
REGION: {village}, {mandal}, {district}, {state}

EXECUTIVE INSIGHT:
Public feedback indicates that "{top_issue}" is the dominant issue in this region,
accounting for {impact}% of reported complaints.

CURRENT STATUS:
The issue severity is assessed as {severity.lower()}, suggesting
{"immediate intervention is required" if severity == "High" else "targeted corrective action is recommended"}.

RECOMMENDED ACTION:
Focused administrative review and local-level monitoring are advised
to prevent further public dissatisfaction and implementation risks.
""".strip()

    # ---- ISSUE COUNT ----
    issue_count = {}
    for f in feedback_rows:
        issue = f.get("issue", "Other Issues")
        issue_count[issue] = issue_count.get(issue, 0) + 1

    # Top issue
    main_issue = max(issue_count, key=issue_count.get)
    main_issue_count = issue_count[main_issue]

    issue_percentage = (main_issue_count / total) * 100

    # ---- STATUS & RISK ----
    if issue_percentage >= 40:
        status = "The scheme is operational but facing significant public concerns."
        risk = "High risk of public dissatisfaction and grievance escalation."
        action = "Immediate administrative intervention is required."
    elif issue_percentage >= 20:
        status = "The scheme is functioning with moderate operational challenges."
        risk = "Potential risk to beneficiary trust if issues persist."
        action = "Targeted corrective action is recommended."
    else:
        status = "The scheme is functioning satisfactorily with minor issues."
        risk = "Low operational risk at present."
        action = "Continue monitoring and routine improvements."

    # ---- FINAL SUMMARY ----
    summary = f"""
Scheme: {scheme}
Region: {state} → {district} → {mandal} → {village}

Current Status:
{status}

Key Issue Highlight:
The dominant concern reported by citizens relates to **{main_issue}**, accounting for a
significant portion of the feedback received in this region.

Risk Assessment:
{risk}

AI Executive Insight:
{action} Priority focus should be placed on addressing **{main_issue}**
to enhance service delivery and restore public confidence.
""".strip()

    return summary

@app.route("/api/report/performance")
def api_scheme_performance():

    state = request.args.get("state")
    district = request.args.get("district")
    mandal = request.args.get("mandal")
    village = request.args.get("village")
    scheme = request.args.get("scheme")

    # ✅ SAFETY CHECK (prevents Loading forever)
    if not all([state, district, mandal, village, scheme]):
        return jsonify({"empty": True})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT issue, sentiment, created_at
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
    """, (state, district, mandal, village, scheme))

    rows = cur.fetchall()
    conn.close()

    total = len(rows)

    if total == 0:
        return jsonify({"empty": True})

    complaints = sum(1 for r in rows if r["sentiment"] == "negative")

    high_severity = sum(
        1 for r in rows
        if r["sentiment"] == "negative"
        and ("delay" in r["issue"].lower() or "payment" in r["issue"].lower())
    )

    pending = round(complaints * 0.4)
    avg_delay = 17  # demo-safe static value

    complaint_pct = round((complaints / total) * 100, 1)

    if complaint_pct > 50:
        status = "🔴 CRITICAL IMPLEMENTATION FAILURE"
    elif complaint_pct > 30:
        status = "⚠️ NEEDS ADMINISTRATIVE ATTENTION"
    else:
        status = "✅ FUNCTIONING SATISFACTORILY"

    # ---- Issue Grouping ----
    issue_map = {}
    for r in rows:
        issue_map[r["issue"]] = issue_map.get(r["issue"], 0) + 1

    issue_summary = [
        {
            "issue": issue,
            "percent": round((count / total) * 100, 1)
        }
        for issue, count in sorted(issue_map.items(), key=lambda x: x[1], reverse=True)
    ]

    return jsonify({
        "header": {
            "scheme": scheme,
            "region": f"{state} > {district} > {mandal} > {village}",
            "date": str(datetime.date.today())
        },
        "status": status,
        "metrics": {
            "total": total,
            "complaints": complaints,
            "high_severity": high_severity,
            "pending": pending,
            "avg_delay": avg_delay
        },
        "issues": issue_summary,
        "actions": [
            "Ensure timely release of scheme funds",
            "Reduce verification backlog at district offices",
            "Conduct local awareness programs",
            "Monitor unresolved complaints weekly"
        ]
    })


@app.route("/api/executive/insight")
def executive_insight():

    if "email" not in session:
        return jsonify({
            "insight": "Executive insight is available only to authorized officials."
        })

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT issue, sentiment
        FROM feedback
    """)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify({
            "insight": "Insufficient feedback data available for executive analysis."
        })

    total = len(rows)

    # ---- Count issue frequencies (NEGATIVE only) ----
    issue_count = {}
    for r in rows:
        if r["sentiment"] == "negative":
            issue_count[r["issue"]] = issue_count.get(r["issue"], 0) + 1

    if not issue_count:
        return jsonify({
            "insight": (
                "Public feedback indicates smooth implementation with no dominant "
                "operational issues reported at this stage."
            )
        })

    # ---- Rank issues ----
    ranked = sorted(issue_count.items(), key=lambda x: x[1], reverse=True)

    # ---- Build insight dynamically ----
    insight_lines = []
    insight_lines.append(
        "AI analysis of public feedback highlights specific operational weaknesses "
        "impacting scheme performance."
    )

    for issue, count in ranked:
        percent = round((count / total) * 100, 1)

        if percent >= 30:
            priority = "HIGH PRIORITY"
        elif percent >= 15:
            priority = "MEDIUM PRIORITY"
        else:
            priority = "LOW PRIORITY"

        insight_lines.append(
            f"- {issue} ({percent}% of feedback): {priority}"
        )

        actions = ISSUE_ACTION_MAP.get(issue, [])
        for act in actions:
            insight_lines.append(f"  • Recommended Action: {act}")

    insight_lines.append(
        "Addressing high-priority issues first is expected to significantly reduce "
        "citizen grievances and improve scheme delivery efficiency."
    )

    return jsonify({
        "insight": "\n".join(insight_lines)
    })
@app.route("/govt/analytics")
def govt_analytics():
    return render_template("analytics.html")
@app.route("/govt/feedback/<int:fid>")
def govt_view_feedback(fid):
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM feedback WHERE id=?
    """, (fid,))

    row = cur.fetchone()
    conn.close()

    if not row:
        return "Feedback not found", 404

    return render_template("govt_feedback_view.html", feedback=row)

    # --------- ANALYSIS ----------
    region_map = {}
    issue_map = {}

    for r in rows:
        region = f"{r['village']}, {r['mandal']}, {r['district']}, {r['state']}"
        region_map[region] = region_map.get(region, 0) + r["count"]
        issue_map[r["issue"]] = issue_map.get(r["issue"], 0) + r["count"]

    # Highest issue region
    worst_region = max(region_map, key=region_map.get)
    worst_region_count = region_map[worst_region]

    # Dominant issue
    dominant_issue = max(issue_map, key=issue_map.get)
    dominant_issue_count = issue_map[dominant_issue]

    # Severity inference
    if dominant_issue_count >= 15:
        risk_level = "High"
    elif dominant_issue_count >= 7:
        risk_level = "Moderate"
    else:
        risk_level = "Low"

    # --------- AI EXECUTIVE INSIGHT ----------
    insight = f"""
HIGH-ISSUE AREA IDENTIFICATION
The region showing the highest concentration of public grievances is {worst_region},
accounting for {worst_region_count} recorded complaints. This area requires immediate
administrative attention.

DOMINANT ISSUE ACROSS REGIONS
The most frequently reported issue across all regions is "{dominant_issue}",
indicating a systemic challenge rather than isolated incidents.

LIKELY ROOT CAUSES (AI-INFERRED)
Feedback language suggests gaps in operational execution, delayed service delivery,
and inadequate local-level monitoring as contributing factors.

RISK ASSESSMENT
If unresolved, the current trend poses a {risk_level.lower()}-to-high risk of
public dissatisfaction, reduced scheme trust, and political escalation at the local level.

EXECUTIVE RECOMMENDATION
Immediate field audits in high-impact regions, accountability reviews at the
implementation level, and time-bound corrective action plans are strongly recommended.
""".strip()

    return jsonify({
        "insight": insight
    })

# ================= AUTH =================
@app.route("/")
def home():
    return redirect("/signin")

@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        session["email"] = request.form["email"]
        session["role"] = request.form["role"]
        return redirect(
            "/govt/dashboard" if session["role"] == "govt" else "/public/dashboard"
        )
    return render_template("signin.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/signin")

# ================= API =================
@app.route("/api/schemes")
def api_schemes():
    return jsonify(SCHEME_DATA)

@app.route("/api/report")
def api_report():
    args = request.args

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT sentiment, issue
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
    """, (
        args["state"],
        args["district"],
        args["mandal"],
        args["village"],
        args["scheme"]
    ))

    rows = cur.fetchall()
    conn.close()

    # Keep counts if needed internally
    sentiments = {"positive": 0, "negative": 0, "neutral": 0}
    issues = {}

    for r in rows:
        sentiments[r["sentiment"]] += 1
        issues[r["issue"]] = issues.get(r["issue"], 0) + 1

    summary_text = generate_overall_ai_summary(
        args["state"],
        args["district"],
        args["mandal"],
        args["village"],
        args["scheme"],
        rows
    )

    return jsonify({
    "sentiments": sentiments,
    "issues": issues,
    "summary": overall_executive_summary(
        args["state"],
        args["district"],
        args["mandal"],
        args["village"],
        args["scheme"],
        issues
    )
})


@app.route("/api/recent-feedback")
def api_recent_feedback():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT 
            id, state, district, mandal, village, scheme,
            feedback, sentiment, issue, created_at
        FROM feedback
        ORDER BY created_at DESC
        LIMIT 10
    """)

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {
            "id": r["id"],
            "state": r["state"],
            "district": r["district"],
            "mandal": r["mandal"],
            "village": r["village"],
            "scheme": r["scheme"],
            "feedback": r["feedback"],
            "sentiment": r["sentiment"],
            "issue": r["issue"],
            "date": r["created_at"]
        } for r in rows
    ])
@app.route("/api/feedback/region")
def api_feedback_by_region():
    args = request.args

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT feedback, sentiment, issue, created_at
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
        ORDER BY created_at DESC
    """, (
        args.get("state"),
        args.get("district"),
        args.get("mandal"),
        args.get("village"),
        args.get("scheme")
    ))

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {
            "feedback": r["feedback"],
            "sentiment": r["sentiment"],
            "issue": r["issue"],
            "date": r["created_at"]
        }
        for r in rows
    ])



@app.route("/api/issues/region")
def api_issue_classification():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT state, district, mandal, village, issue, COUNT(*) as count
        FROM feedback
        GROUP BY state, district, mandal, village, issue
    """)

    rows = cur.fetchall()
    conn.close()

    table = []
    severity_rank = {"High": 3, "Medium": 2, "Low": 1}

    for r in rows:
        sev = severity_from_count(r["count"])
        table.append({
            "state": r["state"],
            "district": r["district"],
            "mandal": r["mandal"],
            "area": r["village"],
            "issue": r["issue"],
            "complaints": r["count"],
            "severity": sev
        })

    table.sort(
        key=lambda x: (severity_rank[x["severity"]], x["complaints"]),
        reverse=True
    )

    return jsonify(table)
@app.route("/api/issues/region-scheme")
def api_issue_classification_region_scheme():

    state = request.args.get("state")
    district = request.args.get("district")
    mandal = request.args.get("mandal")
    village = request.args.get("village")
    scheme = request.args.get("scheme")

    if not all([state, district, mandal, village, scheme]):
        return jsonify([])

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT issue, COUNT(*) as count
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
        GROUP BY issue
        ORDER BY count DESC
    """, (state, district, mandal, village, scheme))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        return jsonify([])

    total = sum(r["count"] for r in rows)

    result = []
    for r in rows:
        percent = round((r["count"] / total) * 100, 1)

        result.append({
            "issue": r["issue"],
            "complaints": r["count"],
            "impact_percent": percent,
            "severity": (
                "High" if percent >= 40 else
                "Medium" if percent >= 20 else
                "Low"
            )
        })

    return jsonify(result)

@app.route("/govt/feedback/view")
def govt_feedback_table():

    args = request.args

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT feedback, sentiment, issue, created_at
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
        ORDER BY created_at DESC
    """, (
        args.get("state"),
        args.get("district"),
        args.get("mandal"),
        args.get("village"),
        args.get("scheme")
    ))

    rows = cur.fetchall()
    conn.close()

    return render_template(
        "govt_feedback_view.html",
        feedbacks=rows,
        region=args
    )
@app.route("/api/public/notifications")
def api_public_notifications():

    # User is anonymous public → match by region & scheme
    state = request.args.get("state")
    district = request.args.get("district")
    mandal = request.args.get("mandal")
    village = request.args.get("village")
    scheme = request.args.get("scheme")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(*) as cnt
        FROM feedback
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
          AND notify=1
    """, (state, district, mandal, village, scheme))

    row = cur.fetchone()

    # 🔥 CLEAR notification AFTER FETCH (one-time)
    

    conn.commit()
    conn.close()

    if row["cnt"] > 0:
        return jsonify({
            "message": f'Your feedback for "{scheme}" was reviewed by officials.'
        })

    return jsonify({})
@app.route("/api/public/notifications/auto")
def api_public_notifications_auto():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT scheme
        FROM feedback
        WHERE notify = 1
        ORDER BY viewed_at DESC
        LIMIT 1
    """)

    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({})

    scheme = row["scheme"]

    # 🔔 Clear notification (one-time)
    cur.execute("""
        UPDATE feedback
        SET notify = 0
        WHERE scheme = ?
    """, (scheme,))

    conn.commit()
    conn.close()

    return jsonify({
        "message": f'Your feedback for "{scheme}" was reviewed by officials.'
    })

print("DATABASE PATH:", DB_PATH)
@app.route("/api/notifications")
def api_notifications():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT scheme
        FROM feedback
        WHERE notify = 1
        ORDER BY viewed_at DESC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({})

    return jsonify({
        "message": f'Your feedback for "{row["scheme"]}" was reviewed by officials.'
    })
@app.route("/api/notifications/clear", methods=["POST"])
def clear_notification():

    conn = get_db()
    cur = conn.cursor()

    cur.execute("UPDATE feedback SET notify = 0 WHERE notify = 1")

    conn.commit()
    conn.close()

    return jsonify({"status": "cleared"})
@app.route("/api/public/my-feedback")
def api_my_feedback():

    if "email" not in session:
        return jsonify([])

    args = request.args
    email = session["email"]

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT scheme, feedback, sentiment, issue, created_at, viewed
        FROM feedback
        WHERE user_email=?
          AND state=? AND district=? AND mandal=? AND village=?
        ORDER BY created_at DESC
    """, (
        email,
        args.get("state"),
        args.get("district"),
        args.get("mandal"),
        args.get("village")
    ))

    rows = cur.fetchall()
    conn.close()

    return jsonify([
        {
            "scheme": r["scheme"],
            "feedback": r["feedback"],
            "sentiment": r["sentiment"],
            "issue": r["issue"],
            "date": r["created_at"],
            "status": "Reviewed" if r["viewed"] else "Pending"
        }
        for r in rows
    ])
@app.route("/api/public/notifications/latest")
def api_public_notifications_latest():

    if "email" not in session:
        return jsonify({})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        SELECT scheme, state, district, mandal, village, viewed_at
        FROM feedback
        WHERE user_email=? AND notify=1
        ORDER BY viewed_at DESC
        LIMIT 1
    """, (session["email"],))

    row = cur.fetchone()

    if not row:
        conn.close()
        return jsonify({})

    # clear AFTER sending
    cur.execute("""
        UPDATE feedback SET notify=0
        WHERE user_email=? AND notify=1
    """, (session["email"],))

    conn.commit()
    conn.close()

    return jsonify({
        "message": f'Your feedback for "{row["scheme"]}" was reviewed by officials.',
        "scheme": row["scheme"],
        "region": f'{row["village"]}, {row["mandal"]}, {row["district"]}, {row["state"]}',
    })

# ================= DASHBOARDS =================
@app.route("/public/dashboard")
def public_dashboard():
    return render_template("public_dashboard.html")

@app.route("/govt/dashboard")
def govt_dashboard():
    return render_template("govt_dashboard.html")

@app.route("/govt/report")
def govt_report_view():

    args = request.args

    state = args.get("state")
    district = args.get("district")
    mandal = args.get("mandal")
    village = args.get("village")
    scheme = args.get("scheme")
    report_type = args.get("type")

    conn = get_db()
    cur = conn.cursor()

    # 🔔 STEP 1: MARK FEEDBACK AS VIEWED (FOR NOTIFICATION)
    cur.execute("""
        UPDATE feedback
        SET viewed = 1,
            notify = 1,
            viewed_at = DATE('now')
        WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
    """, (state, district, mandal, village, scheme))

    feedbacks = []
    
    # 📋 STEP 2: LOAD PUBLIC FEEDBACK IF SELECTED
    if report_type == "public_feedback":
        cur.execute("""
            SELECT feedback, sentiment, issue, created_at
            FROM feedback
            WHERE state=? AND district=? AND mandal=? AND village=? AND scheme=?
            ORDER BY created_at DESC
        """, (state, district, mandal, village, scheme))
        feedbacks = cur.fetchall()

    conn.commit()
    conn.close()

    return render_template(
        "govt_report_view.html",
        **args,
        feedbacks=feedbacks
    )
    return render_template("govt_report_view.html", **request.args)
# ================= FEEDBACK =================
@app.route("/feedback", methods=["GET", "POST"])
def feedback():
    if request.method == "POST":
        text = request.form.get("feedback", "").strip()

        if not text:
            return "Bad Request: Feedback missing", 400

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO feedback
            (user_email, state, district, mandal, village, scheme,
             feedback, sentiment, issue, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.get("email"),
            request.form.get("state"),
            request.form.get("district"),
            request.form.get("mandal"),
            request.form.get("village"),
            request.form.get("scheme"),
            text,
            analyze_sentiment(text),
            classify_issue_policy(text),
            datetime.date.today()
        ))

        conn.commit()
        conn.close()

        return redirect("/public/dashboard")

    return render_template("feedback.html", **request.args)


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)
