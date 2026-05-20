let positions = [];
let current = 0;

async function loadGame() {
    const response = await fetch('static/analysis.json');
    positions = await response.json();
    
    const movesDiv = document.getElementById('moves');
    positions.slice(1).forEach((pos, idx) => {
        const btn = document.createElement('button');
        btn.className = 'move-btn';
        btn.textContent = `${idx + 1}. ${pos.move}`;
        btn.onclick = () => showPosition(idx + 1);
        movesDiv.appendChild(btn);
    });
    
    showPosition(0);
}

function showPosition(n) {
    current = n;
    const pos = positions[n];
    
    document.getElementById('board').src = 'static/' + pos.svg;
    document.getElementById('info').textContent = 
        pos.move !== 'start' ? `Move ${n}: ${pos.move}` : 'Starting Position';
    
    updateEvalBar(pos.score);
    document.getElementById('best-move').textContent = 
        pos.best !== '?' ? `Best: ${pos.best}` : '';
    
    document.getElementById('fen-display').textContent = pos.fen;
    
    document.getElementById('prev-btn').disabled = n === 0;
    document.getElementById('next-btn').disabled = n === positions.length - 1;
    
    document.querySelectorAll('.move-btn').forEach((btn, idx) => {
        btn.classList.toggle('current', idx === n - 1);
    });
}

function updateEvalBar(scoreStr) {
    const evalFill = document.getElementById('eval-fill');
    const evalText = document.getElementById('eval-text');
    
    evalText.textContent = scoreStr;
    
    if (scoreStr === '?') {
        evalFill.style.height = '50%';
        return;
    }
    
    if (scoreStr.startsWith('M')) {
        const mateNum = parseInt(scoreStr.substring(1));
        evalFill.style.height = mateNum > 0 ? '100%' : '0%';
        return;
    }
    
    const score = parseFloat(scoreStr);
    const clamped = Math.max(-10, Math.min(10, score));
    const percentage = ((clamped + 10) / 20) * 100;
    
    evalFill.style.height = percentage + '%';
}

function firstMove() { showPosition(0); }
function lastMove() { showPosition(positions.length - 1); }
function nextMove() { 
    if (current < positions.length - 1) showPosition(current + 1); 
}
function prevMove() { 
    if (current > 0) showPosition(current - 1); 
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') nextMove();
    if (e.key === 'ArrowLeft') prevMove();
});

loadGame();