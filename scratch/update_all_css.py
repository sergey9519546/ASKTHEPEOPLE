import re

def update_css(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace background colors to glassmorphism
    content = re.sub(r'background:\s*var\(--paper-strong\);', r'background: rgba(30, 41, 59, 0.4); backdrop-filter: blur(12px);', content)
    content = re.sub(r'background:\s*var\(--paper\);', r'background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(12px);', content)
    content = re.sub(r'background:\s*var\(--ink(-deep)?\);', r'background: rgba(15, 23, 42, 0.8); backdrop-filter: blur(16px);', content)

    # Replace solid brutalist borders with delicate glassmorphic borders
    content = re.sub(r'border:\s*[0-9.]+px\s+solid\s+var\(--ink\);', r'border: 1px solid rgba(255, 255, 255, 0.1);', content)
    content = re.sub(r'border-([a-z]+):\s*[0-9.]+px\s+solid\s+var\(--ink\);', r'border-\1: 1px solid rgba(255, 255, 255, 0.1);', content)

    content = re.sub(r'border:\s*[0-9.]+px\s+solid\s+var\(--signal\);', r'border: 1px solid rgba(99, 102, 241, 0.5);', content)
    content = re.sub(r'border-([a-z]+):\s*[0-9.]+px\s+solid\s+var\(--signal\);', r'border-\1: 1px solid rgba(99, 102, 241, 0.5);', content)

    # Remove zero border radius (brutalist) and add soft curves
    content = re.sub(r'border-radius:\s*0;', r'border-radius: var(--radius-md);', content)

    # Replace solid offset shadows with soft drop shadows
    content = re.sub(r'box-shadow:\s*[0-9a-z.\s]+var\(--line-light\);', r'box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);', content)
    content = re.sub(r'box-shadow:\s*[0-9a-z.\s]+var\(--paper-strong\);', r'box-shadow: 0 8px 25px rgba(0, 0, 0, 0.4);', content)

    # Invert text colors from light theme to dark theme
    content = re.sub(r'color:\s*var\(--ink\);', r'color: var(--paper);', content)
    content = re.sub(r'color:\s*var\(--ink-muted\);', r'color: var(--paper-muted);', content)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step3Simulation.vue")
update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/Step3RunWayfinder.vue")
update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/OpinionMap.vue")
update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/HistoryDatabase.vue")
update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/GraphPanel.vue")
update_css("C:/Users/serge/OneDrive/Documents/GitHub/ASKTHEPEOPLE/frontend/src/components/CommandPalette.vue")
