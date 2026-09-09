# Signature Management Route - Add this to web_admin.py

@app.route("/signatures", methods=["GET", "POST"])
def signatures():
    if not session.get("admin"):
        return redirect(url_for("login"))
    
    msg = ""
    if request.method == "POST":
        user_id = request.form.get("user_id")
        signature = request.form.get("signature", "")
        
        if user_id:
            with get_db() as conn:
                # Check if user is VIP
                row = conn.execute("SELECT is_vip FROM users WHERE user_id = ?", (user_id,)).fetchone()
                if row and row['is_vip']:
                    conn.execute("UPDATE users SET signature = ? WHERE user_id = ?", (signature, user_id))
                    conn.commit()
                    msg = f"✅ Signature updated for user {user_id}"
                else:
                    msg = f"❌ User {user_id} is not VIP or doesn't exist"
    
    # Get all VIP users with their signatures
    with get_db() as conn:
        vip_users = conn.execute("""
            SELECT user_id, username, signature 
            FROM users 
            WHERE is_vip = 1
            ORDER BY user_id
        """).fetchall()
    
    return render_template_string("""
<!doctype html>
<html>
<head>
    <title>VIP Signatures</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="icon" type="image/png" href="{{ url_for('logo') }}">
    <style>
        body { background: #f8f9fa; }
        .signature-card {
            background: #fff;
            border-radius: 1rem;
            box-shadow: 0 2px 12px #0001;
            padding: 1.5rem;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
<div class="container mt-4">
    <div class="d-flex align-items-center mb-4">
        <img src="{{ url_for('logo') }}" alt="Logo" style="height: 48px; width: 48px; border-radius: 50%; margin-right: 16px;">
        <h2 class="mb-0">✍️ VIP Signatures</h2>
    </div>
    
    {% if msg %}
    <div class="alert alert-info">{{ msg }}</div>
    {% endif %}
    
    <div class="signature-card">
        <h4>Manage Signatures</h4>
        <p class="text-muted">VIP users can have custom signatures automatically appended to their emails.</p>
        
        {% for user in vip_users %}
        <div class="card mb-3">
            <div class="card-body">
                <h5 class="card-title">
                    User {{ user['user_id'] }}
                    {% if user['username'] %}(@{{ user['username'] }}){% endif %}
                </h5>
                <form method="post">
                    <input type="hidden" name="user_id" value="{{ user['user_id'] }}">
                    <div class="mb-3">
                        <label class="form-label">Signature</label>
                        <textarea name="signature" class="form-control" rows="3" placeholder="Enter signature...">{{ user['signature'] or '' }}</textarea>
                    </div>
                    <button type="submit" class="btn btn-primary">Save Signature</button>
                </form>
            </div>
        </div>
        {% endfor %}
        
        {% if not vip_users %}
        <div class="alert alert-warning">No VIP users found.</div>
        {% endif %}
    </div>
    
    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary mt-3">← Back to Dashboard</a>
</div>
</body>
</html>
""", vip_users=vip_users, msg=msg)
