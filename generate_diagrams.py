import matplotlib.pyplot as plt
import matplotlib.patches as patches
from pathlib import Path

# Create output dir
out_dir = Path("/home/adithya/scratch/DBMS_Lab/docs/images")
out_dir.mkdir(parents=True, exist_ok=True)

# Use clean classic academic font
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']

# =============================================================================
# Figure 1: 2NF Normalization (Textbook Elmasri & Navathe Black & White Style)
# =============================================================================
fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 8.5)
ax.axis("off")

# Figure Label
ax.text(0.5, 8.1, "(a)", fontsize=11, fontweight="bold")
ax.text(0.5, 7.8, "DEV_PROJECT_ASSIGNMENT", fontsize=10.5, fontweight="bold")

# Main table attributes
col_names = ["project_id", "user_id", "hours_logged", "project_name", "repo_url", "user_name", "user_email"]
col_widths = [1.3, 1.2, 1.3, 1.5, 1.2, 1.4, 1.5]
start_x = 0.5
y_main = 7.1
h = 0.42

curr_x = start_x
centers = {}
for i, name in enumerate(col_names):
    w = col_widths[i]
    is_pk = (i < 2)
    # Textbook style: Light gray fill for prime attributes, white for non-prime
    bg_color = "#E5E5E5" if is_pk else "#FFFFFF"
    rect = patches.Rectangle((curr_x, y_main), w, h, linewidth=1.2, edgecolor="#000000", facecolor=bg_color)
    ax.add_patch(rect)
    
    # Text
    ax.text(curr_x + w/2, y_main + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if is_pk else "normal")
    centers[name] = curr_x + w/2
    curr_x += w

# Right Side: Prime box (Textbook style)
ax.text(9.4, 7.8, "Prime = { project_id, user_id }", fontsize=9.5, fontweight="bold")
prime_outer = patches.Rectangle((9.4, 5.8), 2.2, 1.8, linewidth=1.2, edgecolor="#000000", facecolor="#FFFFFF")
ax.add_patch(prime_outer)

p1_box = patches.Rectangle((9.7, 6.8), 1.6, 0.4, linewidth=1.0, edgecolor="#000000", facecolor="#FFFFFF")
ax.add_patch(p1_box)
ax.text(10.5, 7.0, "project_id", ha="center", va="center", fontsize=8.5)

p2_box = patches.Rectangle((9.7, 6.1), 1.6, 0.4, linewidth=1.0, edgecolor="#000000", facecolor="#FFFFFF")
ax.add_patch(p2_box)
ax.text(10.5, 6.3, "user_id", ha="center", va="center", fontsize=8.5)

# Dependent boxes on right side
dep_y = [7.3, 6.6, 5.9]
dep_labels = ["hours_logged", "project_name\nrepo_url", "user_name\nuser_email"]
for y_pos, lbl in zip(dep_y, dep_labels):
    d_box = patches.Rectangle((11.9, y_pos - 0.25), 1.4, 0.45 if "\n" in lbl else 0.35, linewidth=1.0, edgecolor="#000000", facecolor="#FFFFFF")
    # arrow from prime box
    pass

# FD Arrows on Main Table (Classic Elmasri style below the table)
# FD1: {project_id, user_id} -> hours_logged
ax.plot([centers["project_id"], centers["project_id"]], [y_main, y_main - 0.3], color="black", lw=1.0)
ax.plot([centers["user_id"], centers["user_id"]], [y_main, y_main - 0.3], color="black", lw=1.0)
ax.plot([centers["project_id"], centers["user_id"]], [y_main - 0.3, y_main - 0.3], color="black", lw=1.0)
mid_pk = (centers["project_id"] + centers["user_id"]) / 2
ax.plot([mid_pk, mid_pk], [y_main - 0.3, y_main - 0.45], color="black", lw=1.0)
ax.plot([mid_pk, centers["hours_logged"]], [y_main - 0.45, y_main - 0.45], color="black", lw=1.0)
ax.annotate("", xy=(centers["hours_logged"], y_main), xytext=(centers["hours_logged"], y_main - 0.45),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.3, y_main - 0.45, "FD1", fontsize=8.5, fontweight="bold", va="center")

# FD2: project_id -> {project_name, repo_url} (Partial dependency)
ax.plot([centers["project_id"], centers["project_id"]], [y_main - 0.3, y_main - 0.75], color="black", lw=1.0)
ax.plot([centers["project_id"], centers["repo_url"]], [y_main - 0.75, y_main - 0.75], color="black", lw=1.0)
ax.annotate("", xy=(centers["project_name"], y_main), xytext=(centers["project_name"], y_main - 0.75),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.annotate("", xy=(centers["repo_url"], y_main), xytext=(centers["repo_url"], y_main - 0.75),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.3, y_main - 0.75, "FD2", fontsize=8.5, fontweight="bold", va="center")

# FD3: user_id -> {user_name, user_email} (Partial dependency)
ax.plot([centers["user_id"], centers["user_id"]], [y_main - 0.3, y_main - 1.05], color="black", lw=1.0)
ax.plot([centers["user_id"], centers["user_email"]], [y_main - 1.05, y_main - 1.05], color="black", lw=1.0)
ax.annotate("", xy=(centers["user_name"], y_main), xytext=(centers["user_name"], y_main - 1.05),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.annotate("", xy=(centers["user_email"], y_main), xytext=(centers["user_email"], y_main - 1.05),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.3, y_main - 1.05, "FD3", fontsize=8.5, fontweight="bold", va="center")

# 2NF Normalization Label & Downward Arrow
ax.text(0.5, 5.5, "2NF Normalization", fontsize=10.5, fontweight="bold")
ax.annotate("", xy=(1.5, 4.6), xytext=(1.5, 5.3),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

# 2NF Decomposed Relations: R1, R2, R3
# R1: PROJECT_MEMBER (FD1)
y_r1 = 4.0
ax.text(0.5, y_r1 + 0.5, "R1 (PROJECT_MEMBER)", fontsize=9.5, fontweight="bold")
r1_cols = ["project_id", "user_id", "hours_logged"]
r1_w = [1.3, 1.2, 1.3]
cx = 0.5
for i, name in enumerate(r1_cols):
    rect = patches.Rectangle((cx, y_r1), r1_w[i], h, linewidth=1.2, edgecolor="#000000", facecolor="#E5E5E5" if i < 2 else "#FFFFFF")
    ax.add_patch(rect)
    ax.text(cx + r1_w[i]/2, y_r1 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if i < 2 else "normal")
    cx += r1_w[i]
# Arrow FD1 on R1
ax.plot([0.5 + 0.65, 0.5 + 0.65], [y_r1, y_r1 - 0.25], color="black", lw=1.0)
ax.plot([0.5 + 1.3 + 0.6, 0.5 + 1.3 + 0.6], [y_r1, y_r1 - 0.25], color="black", lw=1.0)
ax.plot([0.5 + 0.65, 0.5 + 1.3 + 0.6], [y_r1 - 0.25, y_r1 - 0.25], color="black", lw=1.0)
mid_r1 = (0.5 + 0.65 + 0.5 + 1.3 + 0.6) / 2
ax.plot([mid_r1, 0.5 + 2.5 + 0.65], [y_r1 - 0.25, y_r1 - 0.25], color="black", lw=1.0)
ax.annotate("", xy=(0.5 + 2.5 + 0.65, y_r1), xytext=(0.5 + 2.5 + 0.65, y_r1 - 0.25),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.2, y_r1 - 0.25, "FD1", fontsize=8, fontweight="bold", va="center")

# R2: PROJECT (FD2)
cx = 4.8
ax.text(cx, y_r1 + 0.5, "R2 (PROJECT)", fontsize=9.5, fontweight="bold")
r2_cols = ["project_id", "project_name", "repo_url"]
r2_w = [1.3, 1.5, 1.2]
for i, name in enumerate(r2_cols):
    rect = patches.Rectangle((cx, y_r1), r2_w[i], h, linewidth=1.2, edgecolor="#000000", facecolor="#E5E5E5" if i == 0 else "#FFFFFF")
    ax.add_patch(rect)
    ax.text(cx + r2_w[i]/2, y_r1 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if i == 0 else "normal")
    cx += r2_w[i]
# Arrow FD2 on R2
ax.plot([4.8 + 0.65, 4.8 + 0.65], [y_r1, y_r1 - 0.25], color="black", lw=1.0)
ax.plot([4.8 + 0.65, 4.8 + 1.3 + 1.5 + 0.6], [y_r1 - 0.25, y_r1 - 0.25], color="black", lw=1.0)
ax.annotate("", xy=(4.8 + 1.3 + 0.75, y_r1), xytext=(4.8 + 1.3 + 0.75, y_r1 - 0.25),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.annotate("", xy=(4.8 + 1.3 + 1.5 + 0.6, y_r1), xytext=(4.8 + 1.3 + 1.5 + 0.6, y_r1 - 0.25),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(4.5, y_r1 - 0.25, "FD2", fontsize=8, fontweight="bold", va="center")

# R3: APP_USER (FD3)
y_r3 = 2.4
ax.text(0.5, y_r3 + 0.5, "R3 (APP_USER)", fontsize=9.5, fontweight="bold")
r3_cols = ["user_id", "user_name", "user_email"]
r3_w = [1.2, 1.4, 1.6]
cx = 0.5
for i, name in enumerate(r3_cols):
    rect = patches.Rectangle((cx, y_r3), r3_w[i], h, linewidth=1.2, edgecolor="#000000", facecolor="#E5E5E5" if i == 0 else "#FFFFFF")
    ax.add_patch(rect)
    ax.text(cx + r3_w[i]/2, y_r3 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if i == 0 else "normal")
    cx += r3_w[i]
# Arrow FD3 on R3
ax.plot([0.5 + 0.6, 0.5 + 0.6], [y_r3, y_r3 - 0.25], color="black", lw=1.0)
ax.plot([0.5 + 0.6, 0.5 + 1.2 + 1.4 + 0.8], [y_r3 - 0.25, y_r3 - 0.25], color="black", lw=1.0)
ax.annotate("", xy=(0.5 + 1.2 + 0.7, y_r3), xytext=(0.5 + 1.2 + 0.7, y_r3 - 0.25),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.annotate("", xy=(0.5 + 1.2 + 1.4 + 0.8, y_r3), xytext=(0.5 + 1.2 + 1.4 + 0.8, y_r3 - 0.25),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.2, y_r3 - 0.25, "FD3", fontsize=8, fontweight="bold", va="center")

plt.tight_layout()
fig.savefig(out_dir / "figure_1_2nf_normalization.png", bbox_inches="tight")
plt.close(fig)

# =============================================================================
# Figure 2: 3NF Normalization (Textbook Elmasri & Navathe Black & White Style)
# =============================================================================
fig, ax = plt.subplots(figsize=(12, 7.5), dpi=300)
ax.set_xlim(0, 12)
ax.set_ylim(0, 8.5)
ax.axis("off")

# Figure Label
ax.text(0.5, 8.1, "(b)", fontsize=11, fontweight="bold")
ax.text(0.5, 7.8, "DECISION_AI_CONTEXT", fontsize=10.5, fontweight="bold")

# Main table attributes
col_names_3 = ["decision_id", "project_id", "title", "decision_type", "interaction_id", "tool_name", "prompt", "response"]
col_widths_3 = [1.3, 1.2, 1.4, 1.3, 1.4, 1.2, 1.4, 1.4]
start_x = 0.5
y_main_3 = 7.1
h = 0.42

curr_x = start_x
centers_3 = {}
for i, name in enumerate(col_names_3):
    w = col_widths_3[i]
    is_pk = (i == 0)
    bg_color = "#E5E5E5" if is_pk else "#FFFFFF"
    rect = patches.Rectangle((curr_x, y_main_3), w, h, linewidth=1.2, edgecolor="#000000", facecolor=bg_color)
    ax.add_patch(rect)
    
    ax.text(curr_x + w/2, y_main_3 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if is_pk else "normal")
    centers_3[name] = curr_x + w/2
    curr_x += w

# Right Side: Prime box (Textbook style)
ax.text(9.4, 7.8, "Prime = { decision_id }", fontsize=9.5, fontweight="bold")
p_box_3 = patches.Rectangle((9.4, 6.2), 2.2, 1.4, linewidth=1.2, edgecolor="#000000", facecolor="#FFFFFF")
ax.add_patch(p_box_3)

pk_inner = patches.Rectangle((9.7, 6.9), 1.6, 0.4, linewidth=1.0, edgecolor="#000000", facecolor="#E5E5E5")
ax.add_patch(pk_inner)
ax.text(10.5, 7.1, "decision_id", ha="center", va="center", fontsize=8.5, fontweight="bold")

# Arrows on Main Table
# FD1: decision_id -> {project_id, title, decision_type, interaction_id}
ax.plot([centers_3["decision_id"], centers_3["decision_id"]], [y_main_3, y_main_3 - 0.35], color="black", lw=1.0)
ax.plot([centers_3["decision_id"], centers_3["interaction_id"]], [y_main_3 - 0.35, y_main_3 - 0.35], color="black", lw=1.0)
for col in ["project_id", "title", "decision_type", "interaction_id"]:
    ax.annotate("", xy=(centers_3[col], y_main_3), xytext=(centers_3[col], y_main_3 - 0.35),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.3, y_main_3 - 0.35, "FD1", fontsize=8.5, fontweight="bold", va="center")

# FD2: interaction_id -> {tool_name, prompt, response} (Transitive Dependency)
ax.plot([centers_3["interaction_id"], centers_3["interaction_id"]], [y_main_3, y_main_3 - 0.75], color="black", lw=1.0)
ax.plot([centers_3["interaction_id"], centers_3["response"]], [y_main_3 - 0.75, y_main_3 - 0.75], color="black", lw=1.0)
for col in ["tool_name", "prompt", "response"]:
    ax.annotate("", xy=(centers_3[col], y_main_3), xytext=(centers_3[col], y_main_3 - 0.75),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(centers_3["interaction_id"] - 0.45, y_main_3 - 0.75, "FD2", fontsize=8.5, fontweight="bold", va="center")

# 3NF Normalization Label & Downward Arrow
ax.text(0.5, 5.5, "3NF Normalization", fontsize=10.5, fontweight="bold")
ax.annotate("", xy=(1.5, 4.6), xytext=(1.5, 5.3),
            arrowprops=dict(arrowstyle="->", color="black", lw=1.2))

# 3NF Decomposed Relations: ED1, ED2
# ED1: DECISION (FD1 non-transitive attributes)
y_ed1 = 4.0
ax.text(0.5, y_ed1 + 0.5, "ED1 (DECISION)", fontsize=9.5, fontweight="bold")
ed1_cols = ["decision_id", "project_id", "title", "decision_type", "interaction_id"]
ed1_w = [1.3, 1.2, 1.4, 1.3, 1.4]
cx = 0.5
for i, name in enumerate(ed1_cols):
    rect = patches.Rectangle((cx, y_ed1), ed1_w[i], h, linewidth=1.2, edgecolor="#000000", facecolor="#E5E5E5" if i == 0 else "#FFFFFF")
    ax.add_patch(rect)
    ax.text(cx + ed1_w[i]/2, y_ed1 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if i == 0 else "normal")
    cx += ed1_w[i]
# Arrow FD1 on ED1
ax.plot([0.5 + 0.65, 0.5 + 0.65], [y_ed1, y_ed1 - 0.25], color="black", lw=1.0)
ax.plot([0.5 + 0.65, 0.5 + 1.3 + 1.2 + 1.4 + 1.3 + 0.7], [y_ed1 - 0.25, y_ed1 - 0.25], color="black", lw=1.0)
for w_offset in [1.3 + 0.6, 1.3 + 1.2 + 0.7, 1.3 + 1.2 + 1.4 + 0.65, 1.3 + 1.2 + 1.4 + 1.3 + 0.7]:
    ax.annotate("", xy=(0.5 + w_offset, y_ed1), xytext=(0.5 + w_offset, y_ed1 - 0.25),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.2, y_ed1 - 0.25, "FD1", fontsize=8, fontweight="bold", va="center")

# ED2: AI_INTERACTION (Isolated transitive attributes where interaction_id is PK)
y_ed2 = 2.4
ax.text(0.5, y_ed2 + 0.5, "ED2 (AI_INTERACTION)", fontsize=9.5, fontweight="bold")
ed2_cols = ["interaction_id", "project_id", "tool_name", "prompt", "response"]
ed2_w = [1.4, 1.2, 1.3, 1.5, 1.5]
cx = 0.5
for i, name in enumerate(ed2_cols):
    rect = patches.Rectangle((cx, y_ed2), ed2_w[i], h, linewidth=1.2, edgecolor="#000000", facecolor="#E5E5E5" if i == 0 else "#FFFFFF")
    ax.add_patch(rect)
    ax.text(cx + ed2_w[i]/2, y_ed2 + h/2, name, ha="center", va="center", fontsize=8.5, fontweight="bold" if i == 0 else "normal")
    cx += ed2_w[i]
# Arrow FD2 on ED2
ax.plot([0.5 + 0.7, 0.5 + 0.7], [y_ed2, y_ed2 - 0.25], color="black", lw=1.0)
ax.plot([0.5 + 0.7, 0.5 + 1.4 + 1.2 + 1.3 + 1.5 + 0.75], [y_ed2 - 0.25, y_ed2 - 0.25], color="black", lw=1.0)
for w_offset in [1.4 + 0.6, 1.4 + 1.2 + 0.65, 1.4 + 1.2 + 1.3 + 0.75, 1.4 + 1.2 + 1.3 + 1.5 + 0.75]:
    ax.annotate("", xy=(0.5 + w_offset, y_ed2), xytext=(0.5 + w_offset, y_ed2 - 0.25),
                arrowprops=dict(arrowstyle="->", color="black", lw=1.0))
ax.text(0.2, y_ed2 - 0.25, "FD2", fontsize=8, fontweight="bold", va="center")

plt.tight_layout()
fig.savefig(out_dir / "figure_2_3nf_normalization.png", bbox_inches="tight")
plt.close(fig)

print("Textbook black & white diagrams generated successfully!")
