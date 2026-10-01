/* ============================================================
   AI Career Advisor · Frontend JavaScript
   - Animated particle background
   - Orb parallax on mouse move
   - Skill management (add, render)
   - AI match fetching (AJAX)
   ============================================================ */

(function () {
    'use strict';

    // ─────────────────────────────────────────
    // 1. PARTICLE BACKGROUND
    // ─────────────────────────────────────────
    const particleField = document.getElementById('particleField');
    if (particleField) {
        const PARTICLE_COUNT = 45;
        for (let i = 0; i < PARTICLE_COUNT; i++) {
            const particle = document.createElement('div');
            particle.classList.add('particle');

            const size = Math.random() * 4 + 2;
            particle.style.width = size + 'px';
            particle.style.height = size + 'px';
            particle.style.left = Math.random() * 100 + 'vw';
            particle.style.bottom = -(Math.random() * 20 + 5) + 'vh';

            const duration = Math.random() * 22 + 18;
            particle.style.animationDuration = duration + 's';
            particle.style.animationDelay = (Math.random() * -30) + 's';

            const opacity = Math.random() * 0.5 + 0.3;
            particle.style.opacity = opacity;
            particle.style.background = `radial-gradient(circle, rgba(200,220,255,${opacity + 0.2}) 0%, rgba(160,180,255,${opacity}) 100%)`;
            particle.style.boxShadow = `0 0 ${10 + Math.random() * 15}px rgba(130,170,255,0.7)`;

            particleField.appendChild(particle);
        }
    }

    // ─────────────────────────────────────────
    // 2. ORB PARALLAX
    // ─────────────────────────────────────────
    const orbs = document.querySelectorAll('.orb');
    if (orbs.length) {
        document.addEventListener('mousemove', (e) => {
            const x = (e.clientX / window.innerWidth - 0.5) * 2;
            const y = (e.clientY / window.innerHeight - 0.5) * 2;
            orbs.forEach((orb, index) => {
                const strength = (index + 1) * 4;
                orb.style.transform = `translate(${x * strength}px, ${y * strength}px) scale(1)`;
            });
        });

        document.addEventListener('mouseleave', () => {
            orbs.forEach((orb) => {
                orb.style.transform = 'translate(0,0) scale(1)';
            });
        });
    }

    // ─────────────────────────────────────────
    // 3. FLASH MESSAGE AUTO-DISMISS
    // ─────────────────────────────────────────
    document.querySelectorAll('.flash').forEach((flash) => {
        setTimeout(() => {
            flash.style.transition = 'opacity 0.4s, transform 0.4s';
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-15px)';
            setTimeout(() => flash.remove(), 400);
        }, 4000);
    });

    // ─────────────────────────────────────────
    // 4. SKILL MANAGEMENT (Dashboard only)
    // ─────────────────────────────────────────
    const skillForm = document.getElementById('skillForm');
    const skillInput = document.getElementById('skillInput');
    const skillTags = document.getElementById('skillTags');
    const matchesGrid = document.getElementById('matchesGrid');

    if (skillForm && skillInput && skillTags) {
        let currentSkills = Array.from(skillTags.querySelectorAll('.skill-tag'))
            .map(tag => tag.textContent.trim().replace(/^\s*/, ''));

        // ---- Add Skill ----
        window.addSkill = async function () {
            const skill = skillInput.value.trim();
            if (!skill) return;

            // Prevent duplicates (case-insensitive)
            if (currentSkills.some(s => s.toLowerCase() === skill.toLowerCase())) {
                skillInput.value = '';
                return;
            }

            // Optimistic UI
            const tag = document.createElement('span');
            tag.className = 'skill-tag';
            tag.innerHTML = `<i class="fas fa-check"></i> ${escapeHtml(skill)}`;
            skillTags.appendChild(tag);
            currentSkills.push(skill);
            skillInput.value = '';

            // Persist to backend
            try {
                await fetch('/api/skills', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skill })
                });
            } catch (err) {
                console.warn('Could not save skill:', err);
            }

            // Refresh AI matches
            refreshMatches(currentSkills);
        };

        // ---- Refresh Matches ----
        async function refreshMatches(skills) {
            if (!matchesGrid) return;
            matchesGrid.innerHTML = `<div class="empty-state"><i class="fas fa-spinner fa-spin"></i><p>Analyzing your skills...</p></div>`;

            try {
                const res = await fetch('/api/match', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ skills })
                });
                const data = await res.json();
                renderMatches(data.matches || [], skills);
            } catch (err) {
                matchesGrid.innerHTML = `<div class="empty-state"><i class="fas fa-exclamation-triangle"></i><p>Could not load matches. Try again.</p></div>`;
            }
        }

        // ---- Render Matches ----
        function renderMatches(matches, userSkills) {
            if (!matches.length) {
                matchesGrid.innerHTML = `<div class="empty-state"><i class="fas fa-lightbulb"></i><p>Add some skills above to see your AI-powered career matches!</p></div>`;
                return;
            }

            const userSkillsLower = userSkills.map(s => s.toLowerCase().trim());
            matchesGrid.innerHTML = matches.map(m => {
                const skillsHtml = (m.required_skills || '')
                    .split(',')
                    .map(s => s.trim())
                    .filter(Boolean)
                    .map(s => {
                        const matched = userSkillsLower.includes(s.toLowerCase());
                        return `<span class="skill-tag ${matched ? 'matched' : ''}">${escapeHtml(s)}</span>`;
                    }).join('');

                return `
                    <div class="match-card">
                        <div class="match-header">
                            <h3>${escapeHtml(m.title)}</h3>
                            <div class="match-score">
                                <span class="score-value">${m.match_score}%</span>
                                <span class="score-label">match</span>
                            </div>
                        </div>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: ${m.match_score}%;"></div>
                        </div>
                        <p class="match-desc">${escapeHtml(m.description || '')}</p>
                        <div class="match-meta">
                            <span><i class="fas fa-dollar-sign"></i> ${escapeHtml(m.avg_salary || '—')}</span>
                            <span><i class="fas fa-chart-line"></i> ${escapeHtml(m.growth_rate || '—')}</span>
                        </div>
                        <div class="match-skills">
                            <strong>Skills needed:</strong>
                            <div class="skill-tags small">${skillsHtml}</div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        // ---- XSS Protection ----
        function escapeHtml(str) {
            if (str === null || str === undefined) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }
    }

    // ─────────────────────────────────────────
    // 5. CONSOLE GREETING
    // ─────────────────────────────────────────
    console.log(
        '%c🚀 AI Career Advisor loaded',
        'color: #8aa4ff; font-weight: bold; font-size: 13px;'
    );
})();