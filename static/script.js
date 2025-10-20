// API Base URL
const API_BASE = window.location.origin;

// State
let currentRecap = null;
let currentWeek = null;

// DOM Elements
const weekInput = document.getElementById('weekInput');
const generateBtn = document.getElementById('generateBtn');
const generateStatus = document.getElementById('generateStatus');
const recapDisplay = document.getElementById('recapDisplay');
const recapWeek = document.getElementById('recapWeek');
const recapContent = document.getElementById('recapContent');
const historyList = document.getElementById('historyList');
const toast = document.getElementById('toast');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
    await loadLeagueInfo();
    await loadHistory();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    generateBtn.addEventListener('click', generateRecap);
    document.getElementById('copySlackBtn').addEventListener('click', copyForSlack);
    
    weekInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            generateRecap();
        }
    });
}

// Load league info to get current week
async function loadLeagueInfo() {
    try {
        const response = await fetch(`${API_BASE}/api/league`);
        if (response.ok) {
            const data = await response.json();
            weekInput.value = data.current_week || 1;
        }
    } catch (error) {
        console.error('Failed to load league info:', error);
    }
}

// Load recap history
async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/api/recaps/history`);
        if (!response.ok) {
            throw new Error('Failed to load history');
        }
        
        const data = await response.json();
        displayHistory(data.recaps || []);
    } catch (error) {
        console.error('Failed to load history:', error);
        historyList.innerHTML = '<p class="no-history">No recaps generated yet. Create your first one above!</p>';
    }
}

// Display history
function displayHistory(recaps) {
    if (recaps.length === 0) {
        historyList.innerHTML = '<p class="no-history">No recaps generated yet. Create your first one above!</p>';
        return;
    }

    // Sort by week descending
    recaps.sort((a, b) => b.week - a.week);

    historyList.innerHTML = recaps.map(recap => {
        const date = new Date(recap.date);
        const formattedDate = date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });

        // Extract first line as headline
        const headline = recap.recap.split('\n')[0].replace(/^#+ /, '').substring(0, 60);

        return `
            <div class="history-item" onclick="loadRecap(${recap.week})">
                <div class="history-item-info">
                    <div class="history-item-week">Week ${recap.week}</div>
                    <div class="history-item-date">${formattedDate}</div>
                    <div class="history-item-headline">${headline}...</div>
                </div>
                <div class="history-item-action">View →</div>
            </div>
        `;
    }).join('');
}

// Load a specific recap
async function loadRecap(week) {
    try {
        const response = await fetch(`${API_BASE}/api/recaps/${week}`);
        if (!response.ok) {
            throw new Error(`Recap for week ${week} not found`);
        }

        const data = await response.json();
        displayRecap(week, data.recap);
        showToast(`Loaded Week ${week} recap`, 'success');
        
        // Scroll to recap
        recapDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
    } catch (error) {
        console.error('Failed to load recap:', error);
        showToast(`Failed to load Week ${week} recap`, 'error');
    }
}

// Generate new recap
async function generateRecap() {
    const week = parseInt(weekInput.value);
    
    if (!week || week < 1 || week > 18) {
        showStatus('Please enter a valid week number (1-18)', 'error');
        return;
    }

    // Disable button and show loading
    setGenerating(true);
    showStatus('Generating recap... This may take 30-60 seconds ⏳', 'loading');

    try {
        const response = await fetch(`${API_BASE}/api/recaps/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ week })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to generate recap');
        }

        const data = await response.json();
        
        // Display the recap
        displayRecap(week, data.recap);
        showStatus('✅ Recap generated successfully!', 'success');
        showToast('Recap generated successfully!', 'success');
        
        // Reload history
        await loadHistory();
        
        // Scroll to recap
        setTimeout(() => {
            recapDisplay.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);

    } catch (error) {
        console.error('Generation error:', error);
        showStatus(`❌ Error: ${error.message}`, 'error');
        showToast(`Failed to generate recap: ${error.message}`, 'error');
    } finally {
        setGenerating(false);
    }
}

// Display recap (show Slack format in preview)
function displayRecap(week, content) {
    currentRecap = content;
    currentWeek = week;
    
    recapWeek.textContent = `Week ${week}`;
    
    // Display the Slack-formatted version in the preview
    const slackFormatted = convertToSlackFormat(content);
    recapContent.textContent = slackFormatted;
    
    recapDisplay.style.display = 'block';
}

// Convert markdown to Slack format
function convertToSlackFormat(markdown) {
    let slack = markdown;
    
    // Convert main heading (H1) to bold with emojis
    slack = slack.replace(/^# (.+)$/gm, '🏈 *$1* 🏈');
    
    // Convert H2 to bold (no italics)
    slack = slack.replace(/^## (.+)$/gm, '\n*$1*');
    
    // Convert H3 to just bold (not italic - too many underscores!)
    slack = slack.replace(/^### (.+)$/gm, '\n*$1*');
    
    // Add dividers for better visual separation
    slack = slack.replace(/^---+$/gm, '━━━━━━━━━━━━━━━━━━━━━━━━━━');
    
    // Add emoji bullets to make lists pop
    slack = slack.replace(/^- /gm, '  • ');
    slack = slack.replace(/^\* /gm, '  • ');
    
    // Convert bold - Markdown uses **text** or __text__, Slack uses *text*
    slack = slack.replace(/\*\*(.+?)\*\*/g, '*$1*');
    slack = slack.replace(/__(.+?)__/g, '*$1*');
    
    // DON'T convert single asterisks to underscores - causes too many underscores!
    // Just remove single asterisks if they exist
    // slack = slack.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '$1');
    
    // Add fire emoji for roasts
    slack = slack.replace(/\broast\b/gi, 'roast 🔥');
    slack = slack.replace(/\broasted\b/gi, 'roasted 🔥');
    slack = slack.replace(/\bterrible\b/gi, 'terrible 😬');
    slack = slack.replace(/\bdisaster\b/gi, 'disaster 💥');
    
    // Add bench emoji - but be careful not to double-add
    if (!slack.includes('bench 🪑')) {
        slack = slack.replace(/\bbench(?:ed)?\b/gi, 'bench 🪑');
    }
    
    // Add trophy emoji for winners
    slack = slack.replace(/\bwinner\b/gi, 'winner 🏆');
    slack = slack.replace(/\bchampion\b/gi, 'champion 👑');
    
    // Add stats emoji for points
    slack = slack.replace(/(\d+\.?\d*) points/gi, '$1 pts 📊');
    
    return slack;
}

// Copy to clipboard (Slack format - this is the only copy function now)
async function copyForSlack() {
    if (!currentRecap) return;

    // Convert original markdown to Slack format
    const slackFormatted = convertToSlackFormat(currentRecap);

    try {
        await navigator.clipboard.writeText(slackFormatted);
        showToast('✅ Copied! Ready to paste in Slack', 'success');
    } catch (error) {
        console.error('Failed to copy:', error);
        
        // Fallback method
        const textArea = document.createElement('textarea');
        textArea.value = slackFormatted;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        document.body.appendChild(textArea);
        textArea.select();
        
        try {
            document.execCommand('copy');
            showToast('✅ Copied! Ready to paste in Slack', 'success');
        } catch (err) {
            showToast('❌ Failed to copy to clipboard', 'error');
        }
        
        document.body.removeChild(textArea);
    }
}

// Download recap as markdown file (original format)
function downloadRecap() {
    if (!currentRecap || !currentWeek) return;

    // Download the original markdown version
    const blob = new Blob([currentRecap], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `week-${currentWeek}-recap.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showToast(`💾 Downloaded week-${currentWeek}-recap.md`, 'success');
}

// UI Helper Functions
function setGenerating(isGenerating) {
    generateBtn.disabled = isGenerating;
    const btnText = generateBtn.querySelector('.btn-text');
    const spinner = generateBtn.querySelector('.spinner');
    
    if (isGenerating) {
        btnText.textContent = 'Generating...';
        spinner.style.display = 'inline-block';
    } else {
        btnText.textContent = 'Generate Recap';
        spinner.style.display = 'none';
    }
}

function showStatus(message, type) {
    generateStatus.textContent = message;
    generateStatus.className = `status-message ${type} show`;
    
    if (type === 'success' || type === 'error') {
        setTimeout(() => {
            generateStatus.classList.remove('show');
        }, 5000);
    }
}

function showToast(message, type = '') {
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3000);
}

// Make functions available globally
window.loadRecap = loadRecap;
window.copyForSlack = copyForSlack;

