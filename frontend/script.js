/**
 * CloudSage Premium Frontend Logic
 * Handles file uploads, API communication, DOM updates, and animations.
 */

document.addEventListener('DOMContentLoaded', () => {
    // === DOM Elements ===
    const navBtns = document.querySelectorAll('.nav-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    // Dashboard / Upload
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const analyzeBtn = document.getElementById('analyze-btn');
    const loader = document.getElementById('loader');
    const progressText = document.getElementById('loader-status');
    const errorMsg = document.getElementById('error-message');
    const errorText = document.getElementById('error-text');
    
    // Data Containers
    const kpiGrid = document.getElementById('summary-grid');
    const analysisNoData = document.getElementById('analysis-no-data');
    const analysisContent = document.getElementById('analysis-content');
    const forecastNoData = document.getElementById('forecast-no-data');
    const forecastContent = document.getElementById('forecast-content');
    const optimizerNoData = document.getElementById('optimizer-no-data');
    const optimizerContent = document.getElementById('optimizer-content');
    
    // ARIA
    const chatInput = document.getElementById('chat-input');
    const chatSendBtn = document.getElementById('chat-send-btn');
    const chatMessages = document.getElementById('chat-messages');
    const chatSuggestions = document.getElementById('chat-suggestions');
    const ariaProviderBadge = document.getElementById('aria-provider');
    const ariaNotif = document.getElementById('aria-notif');
    const llmStatus = document.getElementById('ctx-llm');
    const contextSidebar = document.getElementById('aria-context-sidebar');

    let uploadedFile = null;
    let analysisData = null; // Store for contextual use

    // === Navigation System ===
    navBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            tabContents.forEach(content => {
                content.classList.remove('active');
                if (content.id === `tab-${targetTab}`) {
                    content.classList.add('active');
                }
            });

            // Clear ARIA notification dot if navigating to ARIA
            if (targetTab === 'aria') {
                ariaNotif.classList.add('hidden');
            }
        });
    });

    // === File Upload System ===
    dropZone.addEventListener('click', () => fileInput.click());
    
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
    
    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            handleFileSelection(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) handleFileSelection(e.target.files[0]);
    });

    function handleFileSelection(file) {
        if (!file.name.endsWith('.csv')) {
            showError("Invalid file format. Please upload a .csv file.");
            return;
        }
        uploadedFile = file;
        hideError();
        dropZone.querySelector('h3').textContent = file.name;
        dropZone.querySelector('.upload-text').textContent = `${(file.size / 1024).toFixed(1)} KB`;
        analyzeBtn.disabled = false;
        
        // Add a subtle success pulse
        dropZone.classList.add('glow-green');
        setTimeout(() => dropZone.classList.remove('glow-green'), 1000);
    }

    // === API Communication & Pipeline ===
    analyzeBtn.addEventListener('click', async () => {
        if (!uploadedFile) return;

        const formData = new FormData();
        formData.append('file', uploadedFile);

        showLoader();
        hideError();
        kpiGrid.classList.add('hidden');

        try {
            // Simulated progress updates for UX
            simulateProgress();
            
            const response = await fetch('http://localhost:8000/api/v1/analyze', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Analysis failed. Please check your CSV format.');
            }

            analysisData = await response.json();
            
            // Populate all tabs immediately
            populateDashboard(analysisData.calculation, analysisData.optimization, analysisData.analysis);
            populateAnalysis(analysisData.analysis);
            populateForecast(analysisData.forecast);
            populateOptimizer(analysisData.optimization);
            
            // Unlock other tabs
            analysisNoData.classList.add('hidden');
            analysisContent.classList.remove('hidden');
            forecastNoData.classList.add('hidden');
            forecastContent.classList.remove('hidden');
            optimizerNoData.classList.add('hidden');
            optimizerContent.classList.remove('hidden');
            contextSidebar.classList.remove('hidden');
            
            // Notify user ARIA is ready
            ariaNotif.classList.remove('hidden');
            addChatMessage('ARIA', "I've successfully analyzed your new dataset. Do you want me to summarize the key findings or look into the anomalies?", 'assistant', ['Summarize findings', 'Explain anomalies']);
            llmStatus.textContent = 'Active (GPT/Gemini)';
            llmStatus.className = 'ctx-val success';

            hideLoader();
            kpiGrid.classList.remove('hidden');

        } catch (err) {
            hideLoader();
            showError(err.message);
        }
    });

    // === UI Populators ===
    function populateDashboard(calc, opt, analysis) {
        // Animate numbers
        animateValue('summary-total-cost', calc.total_cost, true);
        animateValue('summary-savings', opt.total_potential_savings_usd, true);
        
        document.getElementById('summary-savings-pct').textContent = `${opt.total_potential_savings_pct.toFixed(1)}% of total spend`;
        
        if (analysis.cost_velocity) {
            document.getElementById('summary-velocity').textContent = analysis.cost_velocity;
        }
        
        const anomaliesCount = analysis.anomalies ? analysis.anomalies.length : 0;
        animateValue('summary-anomalies', anomaliesCount, false);
        
        let sevText = 'System Normal';
        let sevClass = 'highlight-green';
        if (anomaliesCount > 0) {
            const hasCrit = analysis.anomalies.some(a => a.severity === 'critical');
            sevText = hasCrit ? 'Critical Attention Needed' : 'Review Suggested';
            sevClass = hasCrit ? 'highlight-red' : 'highlight-amber';
        }
        const anomEl = document.getElementById('summary-anomalies');
        anomEl.className = `kpi-value counter-val ${sevClass}`;
        document.getElementById('summary-anomalies-sev').textContent = sevText;
    }

    function populateAnalysis(analysis) {
        // Top Services Chart (Pure CSS/DOM)
        const chartContainer = document.getElementById('top-services-bars');
        chartContainer.innerHTML = '';
        
        if (analysis.top_services && analysis.top_services.length > 0) {
            const maxCost = Math.max(...analysis.top_services.map(s => s.cost));
            
            analysis.top_services.forEach(item => {
                const pct = Math.max(5, (item.cost / maxCost) * 100);
                const barHtml = `
                    <div class="chart-bar-container">
                        <div class="chart-bar" style="height: 0px;" data-target="${pct}%">
                            <div class="chart-tooltip">${item.service}: $${formatNumber(item.cost)}</div>
                        </div>
                        <div class="chart-label" title="${item.service}">${item.service}</div>
                    </div>
                `;
                chartContainer.insertAdjacentHTML('beforeend', barHtml);
            });
            
            // Trigger animation after render
            setTimeout(() => {
                document.querySelectorAll('.chart-bar').forEach(bar => {
                    bar.style.height = bar.getAttribute('data-target');
                });
            }, 100);
        }

        // Service Table
        const tbody = document.getElementById('service-breakdown-body');
        tbody.innerHTML = '';
        
        let sortedSvcs = Object.entries(analysis.service_breakdown)
            .sort((a, b) => b[1].cost - a[1].cost);
            
        sortedSvcs.forEach(([svc, data]) => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${svc}</strong></td>
                <td class="text-right value-mono">$${formatNumber(data.cost)}</td>
                <td class="text-right">${data.percentage.toFixed(1)}%</td>
                <td>
                    <div class="micro-bar-bg">
                        <div class="micro-bar-fill" style="width: 0%" data-target="${data.percentage}%"></div>
                    </div>
                </td>
            `;
            tbody.appendChild(tr);
        });
        
        setTimeout(() => {
            document.querySelectorAll('.micro-bar-fill').forEach(bar => {
                bar.style.width = bar.getAttribute('data-target');
            });
        }, 100);

        // Anomalies List
        const anomContainer = document.getElementById('anomalies-list');
        anomContainer.innerHTML = '';
        document.getElementById('anomaly-count-badge').textContent = analysis.anomalies.length;
        
        if (analysis.anomalies.length === 0) {
            anomContainer.innerHTML = '<p class="text-muted p-3">No major anomalies detected in the current dataset.</p>';
        } else {
            analysis.anomalies.forEach(anom => {
                const colorMap = {
                    'critical': 'var(--color-danger)',
                    'high': 'var(--color-warning)',
                    'medium': '#fbbf24',
                    'low': 'var(--color-info)'
                };
                const color = colorMap[anom.severity] || 'white';
                
                const html = `
                    <div class="rec-item">
                        <div class="kpi-icon" style="background: ${color}22; color: ${color}">
                            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
                        </div>
                        <div>
                            <h4 style="color: ${color}">${anom.service} Spike Detected</h4>
                            <p class="text-muted" style="font-size: 0.9rem">${anom.description}</p>
                        </div>
                        <div class="value-mono">${anom.cost > 0 ? '$'+formatNumber(anom.cost) : ''}</div>
                    </div>
                `;
                anomContainer.insertAdjacentHTML('beforeend', html);
            });
        }
    }

    function populateForecast(forecast) {
        document.getElementById('forecast-method').textContent = forecast.method.replace(/_/g, ' ').toUpperCase();
        document.getElementById('forecast-datapoints').textContent = forecast.data_points_used || 0;
        
        animateValue('forecast-7d', forecast.predicted_cost_next_7_days, true);
        animateValue('forecast-30d', forecast.predicted_cost_next_30_days, true);
        
        if (forecast.confidence_interval_7d) {
            document.getElementById('forecast-7d-ci').textContent = `Range: $${formatNumber(forecast.confidence_interval_7d.lower_bound)} - $${formatNumber(forecast.confidence_interval_7d.upper_bound)}`;
            document.getElementById('forecast-30d-ci').textContent = `Range: $${formatNumber(forecast.confidence_interval_30d.lower_bound)} - $${formatNumber(forecast.confidence_interval_30d.upper_bound)}`;
        }

        const trendEl = document.getElementById('forecast-trend');
        if (forecast.predicted_cost_next_7_days > 0) {
            trendEl.textContent = 'Upward Trajectory';
            trendEl.style.color = 'var(--color-danger)';
        }
    }

    function populateOptimizer(opt) {
        animateValue('opt-banner-usd', opt.total_potential_savings_usd, true);
        animateValue('opt-banner-pct', opt.total_potential_savings_pct, false);
        
        const list = document.getElementById('recommendations-list');
        list.innerHTML = '';
        
        if (!opt.recommendations || opt.recommendations.length === 0) {
            list.innerHTML = '<p class="text-muted">Infrastructure is highly optimized. No critical savings identified.</p>';
            return;
        }
        
        opt.recommendations.forEach(rec => {
            let iconSvg = '<circle cx="12" cy="12" r="3"></circle>';
            if (rec.category === 'rightsizing') iconSvg = '<path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7"></path>';
            else if (rec.category === 'idle_resources') iconSvg = '<circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline>';
            
            const html = `
                <div class="rec-item">
                    <div class="kpi-icon blue">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">${iconSvg}</svg>
                    </div>
                    <div>
                        <h4>${rec.service}: ${rec.category.replace('_', ' ').toUpperCase()}</h4>
                        <p class="text-muted" style="font-size: 0.9rem">${rec.suggestion}</p>
                        <div style="font-size: 0.8rem; margin-top: 4px; color: var(--color-warning)">Priority Score: ${rec.priority_score}/10</div>
                    </div>
                    <div class="value-mono" style="color: var(--color-success); font-size: 1.2rem; font-weight: 600;">
                        -$${formatNumber(rec.estimated_savings_usd)}
                    </div>
                </div>
            `;
            list.insertAdjacentHTML('beforeend', html);
        });
    }

    // === ARIA Chat System ===
    chatSendBtn.addEventListener('click', sendChatMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendChatMessage();
    });

    // Handle suggestion chips
    chatSuggestions.addEventListener('click', (e) => {
        if (e.target.classList.contains('suggestion-chip')) {
            chatInput.value = e.target.textContent;
            sendChatMessage();
        }
    });

    async function sendChatMessage() {
        const msg = chatInput.value.trim();
        if (!msg) return;

        addChatMessage('You', msg, 'user');
        chatInput.value = '';
        chatSuggestions.innerHTML = ''; // Clear suggestions
        chatSuggestions.classList.add('hidden');
        
        // Disable input while generating
        chatInput.disabled = true;
        
        // Add loading indicator
        const loadingId = 'aria-typing-' + Date.now();
        addChatMessage('ARIA', '<span class="animate-pulse">Analyzing architecture data...</span>', 'assistant', [], loadingId);

        try {
            const resp = await fetch('http://localhost:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: msg }) // Backend uses stored context
            });

            const typingEl = document.getElementById(loadingId);
            if (typingEl) typingEl.remove();

            if (!resp.ok) throw new Error('API Error');
            const data = await resp.json();
            
            // Format response (convert basic markdown to html for lists/bold)
            let formattedResp = data.response
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\n- /g, '<br>• ')
                .replace(/\n\n/g, '<br><br>');
                
            addChatMessage('ARIA', formattedResp, 'assistant', data.suggestions || []);
            
            ariaProviderBadge.textContent = 'Active (' + data.provider + ')';
            ariaProviderBadge.className = 'provider-badge highlight-green';

        } catch (err) {
            const typingEl = document.getElementById(loadingId);
            if (typingEl) typingEl.remove();
            addChatMessage('ARIA', 'I encountered an error connecting to my linguistic core. Please check the backend connection.', 'assistant');
        } finally {
            chatInput.disabled = false;
            chatInput.focus();
        }
    }

    function addChatMessage(name, text, role, suggestions = [], customId = null) {
        let avatarHtml = role === 'assistant' 
            ? '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>'
            : '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>';

        const idAttr = customId ? `id="${customId}"` : '';
        const html = `
            <div class="chat-message ${role} fade-in" ${idAttr}>
                <div class="msg-avatar">${avatarHtml}</div>
                <div class="msg-content glass-effect">
                    <p>${text}</p>
                </div>
            </div>
        `;
        chatMessages.insertAdjacentHTML('beforeend', html);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // Render suggestions if provided
        if (suggestions && suggestions.length > 0) {
            chatSuggestions.innerHTML = '';
            suggestions.forEach(s => {
                const btn = document.createElement('div');
                btn.className = 'suggestion-chip';
                btn.textContent = s;
                chatSuggestions.appendChild(btn);
            });
            chatSuggestions.classList.remove('hidden');
        }
    }

    // === Helpers ===
    function showLoader() {
        loader.classList.remove('hidden');
    }
    
    function hideLoader() {
        loader.classList.add('hidden');
    }

    function showError(msg) {
        errorText.textContent = msg;
        errorMsg.classList.remove('hidden');
    }

    function hideError() {
        errorMsg.classList.add('hidden');
    }

    function formatNumber(num) {
        return num.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function animateValue(id, endVal, isCurrency) {
        const obj = document.getElementById(id);
        if(!obj) return;
        
        let start = 0;
        const duration = 1500;
        let startTimestamp = null;
        
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            // Ease out cubic
            const easeOut = 1 - Math.pow(1 - progress, 3);
            const current = (endVal * easeOut);
            
            if (isCurrency) {
                obj.innerHTML = `$${formatNumber(current)}`;
            } else {
                obj.innerHTML = Math.floor(current);
            }
            
            if (progress < 1) {
                window.requestAnimationFrame(step);
            } else {
                if (isCurrency) obj.innerHTML = `$${formatNumber(endVal)}`;
                else obj.innerHTML = Math.round(endVal);
            }
        };
        window.requestAnimationFrame(step);
    }
    
    function simulateProgress() {
        const texts = ["Validating schema...", "Running regression models...", "Finding optimization paths...", "Generating summaries..."];
        let i = 0;
        const interval = setInterval(() => {
            if(i < texts.length) {
                progressText.textContent = texts[i];
                document.getElementById('progress-bar').style.width = `${(i+1)*25}%`;
                i++;
            } else {
                clearInterval(interval);
            }
        }, 600);
    }
});
