/* CreditCoach AI */
const SID='session_'+Date.now(),chat=document.getElementById('chat'),inner=document.getElementById('chatInner');
let cc=0,tt=null,lastMemberId=null;
marked.setOptions({breaks:true,gfm:true});
const md=t=>{try{return DOMPurify.sanitize(marked.parse(t||''),{USE_PROFILES:{html:true}})}catch{return(t||'').replace(/\n/g,'<br>')}};
const esc=t=>{const d=document.createElement('div');d.textContent=t;return d.innerHTML};
const sendSVG='<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
function showInput(){document.getElementById('inputBar').style.display='';document.getElementById('navBack').style.display=''}
function hideInput(){document.getElementById('inputBar').style.display='none';document.getElementById('navBack').style.display='none'}
function showNav(){document.querySelector('.nav').style.display=''}
function hideNav(){document.querySelector('.nav').style.display='none'}

/* ═══ DATA ═══ */
const J={
    new_to_credit:{title:"I'm New to Credit",color:'var(--green)',
        desc:'Perfect for students, immigrants, or anyone just starting out.',
        profiles:[{id:'M0034',name:'Fatima Hill',score:0,note:'No credit history yet'},{id:'M0007',name:'William Chen',score:416,note:'2 accounts, starting out'},{id:'M0105',name:'Marcus Brown',score:430,note:'2 accounts, 14mo'}],
        steps:[{a:'build',l:'How to start',d:'Avoid rejections, build from zero'},{a:'health',l:'See where you stand',d:'Get your credit grade'},{a:'plan',l:'Building plan',d:'Steps to establish credit'},{a:'timeline',l:'See your future',d:'3/6/12 month projections'},{a:'rights',l:'Know your rights',d:'Consumer protections (RAG)'}]},
    stuck_score:{title:"My Score Won't Budge",color:'var(--accent)',
        desc:'Stuck in the 600s? Let\'s find what\'s holding you back.',
        profiles:[{id:'M0042',name:'Hannah Moore',score:649,note:'Fair credit'},{id:'M0009',name:'Chris Nelson',score:645,note:'High util + late payments'},{id:'M0027',name:'Hannah Walker',score:659,note:'Multiple issues'}],
        steps:[{a:'profile',l:'Full diagnosis',d:'Every factor dragging your score'},{a:'health',l:'Health checkup',d:'Grade, strengths & weaknesses'},{a:'impact',l:'Simulate a fix',d:'Pay down a balance — see impact'},{a:'plan',l:'Breakthrough plan',d:'Prioritized steps'}]},
    optimize:{title:"I Want to Go Higher",color:'var(--purple)',
        desc:'Already strong? Push from 740 to 800+ for the best rates.',
        profiles:[{id:'M0001',name:'Chris Wright',score:748,note:'4 accounts'},{id:'M0002',name:'Grace Brown',score:824,note:'7 accounts'},{id:'M0006',name:'John Lee',score:759,note:'Util at 30%'}],
        steps:[{a:'profile',l:'Score deep-dive',d:'What\'s keeping you from 800+?'},{a:'timeline',l:'Path to 800+',d:'12-month trajectory'},{a:'plan',l:'Optimization',d:'Maximize every FICO factor'},{a:'impact',l:'What-if scenarios',d:'Open/close a card? Simulate'}]}
};
let cj=null,cjk=null,cm=null;

/* ═══════════════════════════════════
   PAGE 1: HERO LANDING (full screen)
   ═══════════════════════════════════ */
function showWelcome(){
    inner.innerHTML='';cj=cm=null;hideInput();hideNav();
    const d=document.createElement('div');d.className='welcome';d.id='welcome';
    d.innerHTML=`
    <div class="hero-full">
        <div class="hero-orb hero-orb-1"></div>
        <div class="hero-orb hero-orb-2"></div>
        <div class="hero-content">
            <div class="hero-badge">&#9889; IBM watsonx.ai &middot; Multi-Agent &middot; RAG</div>
            <h1>Take control of<br>your <span class="grad">credit score</span></h1>
            <p class="hero-sub">Three AI agents analyze your credit, simulate your future, and build a personalized plan — no jargon, no judgment.</p>
            <div class="hero-input">
                <div class="input-wrap">
                    <input id="heroInput" type="text" aria-label="Ask a credit question" placeholder="Ask anything — e.g. 'What's a good credit score?'" onkeydown="if(event.key==='Enter'){document.getElementById('msgInput').value=this.value;sendMessage();this.value=''}">
                    <button onclick="document.getElementById('msgInput').value=document.getElementById('heroInput').value;sendMessage();document.getElementById('heroInput').value=''">${sendSVG}</button>
                </div>
            </div>
            <div class="hero-stats">
                <div class="hs-item"><div class="hs-num" id="ct-p">200</div><div class="hs-label">Profiles</div></div>
                <div class="hs-item"><div class="hs-num">3</div><div class="hs-label">AI Agents</div></div>
                <div class="hs-item"><div class="hs-num">6</div><div class="hs-label">Tools</div></div>
                <div class="hs-item"><div class="hs-num" id="ct-r">153</div><div class="hs-label">RAG Chunks</div></div>
            </div>
            <button class="hero-cta" onclick="showPaths()">Choose Your Path <span>&#8595;</span></button>
        </div>
    </div>`;
    inner.appendChild(d);setAgents([]);document.getElementById('thinkingBar').innerHTML='';
    animateCounter('ct-p',0,200,800);animateCounter('ct-r',0,153,600);
}

function animateCounter(id,s,e,dur){
    const el=document.getElementById(id);if(!el)return;
    const t0=performance.now();
    function u(now){const p=Math.min((now-t0)/dur,1);el.textContent=Math.round(s+(e-s)*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(u)}
    requestAnimationFrame(u);
}
showWelcome();

/* ═══════════════════════════════════
   PAGE 2: CHOOSE YOUR PATH (4 cards)
   ═══════════════════════════════════ */
function showPaths(){
    inner.innerHTML='';hideInput();showNav();
    const d=document.createElement('div');d.className='paths-page';d.id='welcome';
    d.innerHTML=`
        <button class="back" onclick="showWelcome()">&#8592; Back to Home</button>
        <h2>Choose your path</h2>
        <p class="paths-desc">Select the journey that matches where you are today. Or enter your own credit details for a custom analysis.</p>
        <div class="paths-grid">
            <button class="pth pth-green" onclick="selJ('new_to_credit')">
                <div class="pth-icon">&#127793;</div>
                <h3>I'm New to Credit</h3>
                <div class="pth-sub" style="color:var(--green)">Build from zero</div>
                <p>First card, student, immigrant, or no score at all.</p>
                <div class="pth-tags"><span>Health Grade</span><span>Building Plan</span><span>Timeline</span></div>
            </button>
            <button class="pth pth-blue" onclick="selJ('stuck_score')">
                <div class="pth-icon">&#128275;</div>
                <h3>Score Won't Budge</h3>
                <div class="pth-sub" style="color:var(--accent)">Diagnose &amp; fix</div>
                <p>Stuck in the 600s? Find exactly what's holding you back.</p>
                <div class="pth-tags"><span>Full Diagnosis</span><span>Simulate Fix</span><span>Action Plan</span></div>
            </button>
            <button class="pth pth-purple" onclick="selJ('optimize')">
                <div class="pth-icon">&#128640;</div>
                <h3>I Want to Go Higher</h3>
                <div class="pth-sub" style="color:var(--purple)">Optimize for 800+</div>
                <p>Already strong? Fine-tune for the best rates everywhere.</p>
                <div class="pth-tags"><span>Deep-dive</span><span>Path to 800</span><span>What-if</span></div>
            </button>
            <button class="pth pth-orange" onclick="openCustomForm()">
                <div class="pth-icon">&#9998;</div>
                <h3>Analyze My Credit</h3>
                <div class="pth-sub" style="color:var(--orange)">Enter your own info</div>
                <p>Input your score, utilization, and history for a full AI-powered analysis.</p>
                <div class="pth-tags"><span>Health Checkup</span><span>Action Plan</span><span>12mo Timeline</span></div>
            </button>
        </div>
        <div class="features-row">
            <div class="feature"><span class="fdot" style="background:var(--accent)"></span>Score Simulation</div>
            <div class="feature"><span class="fdot" style="background:var(--green)"></span>Personalized Plans</div>
            <div class="feature"><span class="fdot" style="background:var(--purple)"></span>Rights &amp; Disputes (RAG)</div>
            <div class="feature"><span class="fdot" style="background:var(--orange)"></span>Timeline Charts</div>
        </div>`;
    inner.appendChild(d);
}

/* ═══ CUSTOM FORM MODAL ═══ */
let cfAcctCount=0;
function cfAddAccount(type,limit,balance,status){
    cfAcctCount++;
    const n=cfAcctCount;
    const row=document.createElement('div');
    row.className='cf-acct-row';row.id=`cf-acct-${n}`;
    row.innerHTML=`
        <div class="cf-acct-num">${n}</div>
        <div class="cf-acct-fields">
            <div class="cf-field"><label>Type</label>
                <select id="cf-atype-${n}">
                    <option value="credit_card"${type==='credit_card'?' selected':''}>Credit Card</option>
                    <option value="auto_loan"${type==='auto_loan'?' selected':''}>Auto Loan</option>
                    <option value="student_loan"${type==='student_loan'?' selected':''}>Student Loan</option>
                    <option value="mortgage"${type==='mortgage'?' selected':''}>Mortgage</option>
                    <option value="personal_loan"${type==='personal_loan'?' selected':''}>Personal Loan</option>
                </select>
            </div>
            <div class="cf-field"><label>Limit / Original</label><input id="cf-alimit-${n}" type="number" min="0" placeholder="e.g. 5000" value="${limit||''}"></div>
            <div class="cf-field"><label>Balance</label><input id="cf-abal-${n}" type="number" min="0" placeholder="e.g. 2300" value="${balance||''}"></div>
            <div class="cf-field"><label>Payment Status</label>
                <select id="cf-astatus-${n}">
                    <option value="current"${!status||status==='current'?' selected':''}>Current</option>
                    <option value="30_late"${status==='30_late'?' selected':''}>30 Days Late</option>
                    <option value="60_late"${status==='60_late'?' selected':''}>60 Days Late</option>
                    <option value="90_late"${status==='90_late'?' selected':''}>90+ Days Late</option>
                    <option value="collection"${status==='collection'?' selected':''}>In Collections</option>
                </select>
            </div>
        </div>
        <button class="cf-acct-rm" onclick="document.getElementById('cf-acct-${n}').remove();cfRenum()" title="Remove">&times;</button>
    `;
    document.getElementById('cf-acct-list').appendChild(row);
}
function cfRenum(){
    const rows=document.querySelectorAll('.cf-acct-row');
    rows.forEach((r,i)=>{r.querySelector('.cf-acct-num').textContent=i+1});
}
function openCustomForm(){
    cfAcctCount=0;
    const o=document.createElement('div');o.className='overlay';o.id='overlay';
    o.onclick=e=>{if(e.target===o)o.remove()};
    o.innerHTML=`<div class="modal modal-wide">
        <h3>&#9998; Analyze My Credit</h3>
        <p class="mdesc">Enter your details and accounts. Our AI agents will reason about your real numbers to give you a personalized health checkup, action plan, and 12-month projection.</p>
        <div class="cf-section">
            <div class="cf-section-label">Overview</div>
            <div class="cf-grid" role="group" aria-label="Credit profile overview">
                <div class="cf-field"><label for="cf-score">Credit Score (300-850)</label><input id="cf-score" type="number" min="300" max="850" placeholder="e.g. 650"></div>
                <div class="cf-field"><label for="cf-pay">On-time Payment %</label><input id="cf-pay" type="number" min="0" max="100" placeholder="e.g. 92"></div>
                <div class="cf-field"><label for="cf-late">Late Payments (2yr)</label><input id="cf-late" type="number" min="0" placeholder="0" value="0"></div>
                <div class="cf-field"><label for="cf-inq">Hard Inquiries (12mo)</label><input id="cf-inq" type="number" min="0" placeholder="0" value="0"></div>
            </div>
        </div>
        <div class="cf-section">
            <div class="cf-section-hdr">
                <div class="cf-section-label">Accounts</div>
                <button class="cf-add-btn" onclick="cfAddAccount()">+ Add Account</button>
            </div>
            <div id="cf-acct-list" class="cf-acct-list"></div>
            <div id="cf-acct-empty" class="cf-acct-empty">Click <strong>+ Add Account</strong> to enter your credit cards, loans, and other accounts.</div>
        </div>
        <div class="cf-section">
            <div class="cf-grid" role="group">
                <div class="cf-field cf-notes"><label for="cf-notes">Anything else?</label><input id="cf-notes" type="text" placeholder="e.g. student, recently immigrated, saving for mortgage"></div>
            </div>
        </div>
        <div class="modal-actions">
            <button class="cancel" onclick="document.getElementById('overlay').remove()">Cancel</button>
            <button class="go" onclick="submitCustom()">Analyze My Profile &#8594;</button>
        </div>
    </div>`;
    document.body.appendChild(o);
    // Auto-hide empty state when accounts exist
    const observer=new MutationObserver(()=>{
        const list=document.getElementById('cf-acct-list');
        const empty=document.getElementById('cf-acct-empty');
        if(list&&empty) empty.style.display=list.children.length?'none':'block';
    });
    const list=document.getElementById('cf-acct-list');
    if(list) observer.observe(list,{childList:true});
    setTimeout(()=>document.getElementById('cf-score').focus(),50);
}
async function submitCustom(){
    const v=id=>{const el=document.getElementById(id);return el?el.value:''};
    const score=parseInt(v('cf-score'));
    if(v('cf-score')&&(score<300||score>850)){alert('Credit score must be between 300 and 850.');return}
    // Gather accounts
    const rows=document.querySelectorAll('.cf-acct-row');
    const accounts=[];
    rows.forEach(r=>{
        const id=r.id.split('-')[2];
        const type=v(`cf-atype-${id}`);
        const limit=parseFloat(v(`cf-alimit-${id}`))||0;
        const bal=parseFloat(v(`cf-abal-${id}`))||0;
        const status=v(`cf-astatus-${id}`);
        if(limit>0||bal>0){
            accounts.push({type,limit,balance:bal,status});
        }
    });
    document.getElementById('overlay')?.remove();
    // Show user message summary
    let summary='Analyze my credit profile';
    if(v('cf-score')) summary+=` (Score: ${v('cf-score')}`;
    if(accounts.length) summary+=`, ${accounts.length} account${accounts.length>1?'s':''}`;
    if(v('cf-score')) summary+=')';
    addMsg('user',esc(summary));
    const btn=document.getElementById('sendBtn');
    btn.disabled=true;btn.innerHTML='<span class="spinner"></span>';
    showThinking();document.querySelectorAll('.agent-pill').forEach(a=>a.classList.add('on'));
    try{
        const r=await fetch('/analyze',{method:'POST',headers:{'Content-Type':'application/json'},
            body:JSON.stringify({
                score:v('cf-score')||null, payment_pct:v('cf-pay')||null,
                late_payments:v('cf-late')||0, inquiries:v('cf-inq')||0,
                accounts, notes:v('cf-notes')||'', session_id:SID
            })});
        const data=await r.json();
        hideThinking();setAgents(data.agents_used);
        if(data.member_id) lastMemberId=data.member_id;
        addMsg('assistant',md(data.reply),data.agents_used,data.visualizations,data.delegation_trace);
    }catch(e){hideThinking();setAgents([]);addMsg('assistant','Connection error.')}
    btn.disabled=false;btn.innerHTML=sendSVG;document.getElementById('msgInput').focus();
}

/* ═══ STEP 2: PICK PROFILE ═══ */
function selJ(k){
    cjk=k;cj=J[k];inner.innerHTML='';hideInput();showNav();
    const d=document.createElement('div');d.className='screen';d.id='welcome';
    d.innerHTML=`<button class="back" onclick="showPaths()">&#8592; Back</button>
        <h2>${cj.title}</h2><p class="sdesc">${cj.desc}</p>
        <div class="profiles">${cj.profiles.map(p=>
            `<button class="pcard" onclick="selM('${p.id}','${esc(p.name)}')">
                <div class="pscore" style="color:${p.score===0?'var(--text3)':cj.color}${p.score===0?';font-size:28px':''}">${p.score===0?'No Score':p.score}</div>
                <div class="pname">${esc(p.name)}</div><div class="pnote">${esc(p.note)}</div>
            </button>`).join('')}</div>
        <div class="custom-alt">Or type any ID (M0001–M0200) in chat, or <a onclick="openCustomForm()">enter your own details</a>.</div>`;
    inner.appendChild(d);
}

/* ═══ STEP 3: GUIDED STEPS ═══ */
function selM(id,name){
    cm={id,name};lastMemberId=id;inner.innerHTML='';hideInput();showNav();
    const d=document.createElement('div');d.className='screen';d.id='welcome';
    d.innerHTML=`<button class="back" onclick="selJ('${cjk}')">&#8592; Back</button>
        <div style="text-align:center">
            <div class="member-badge"><div class="mid" style="color:${cj.color}">${id}</div><div style="text-align:left"><div style="font-weight:600">${esc(name)}</div><div style="font-size:12px;color:var(--text3)">Selected</div></div></div>
            <h2>Your guided path</h2><p class="sdesc">Follow in order or jump to any step.</p>
        </div>
        <div class="steps-grid">${cj.steps.map((s,i)=>
            `<button class="scard" onclick="runStep('${s.a}','${id}')">
                <div class="snum" style="background:${cj.color}">${i+1}</div>
                <div><h4>${s.l}</h4><p>${s.d}</p></div>
            </button>`).join('')}</div>`;
    inner.appendChild(d);
}

function runStep(a,id){
    lastMemberId=id;
    const P={profile:i=>'Show me the full credit profile for '+i+' — break down every factor and flag specific issues.',
        health:i=>'Give me a thorough credit health checkup for '+i+'. Grade them, list strengths and weaknesses, give top tip.',
        plan:i=>'Create a detailed personalized action plan for '+i+'. Prioritize by impact. Reference their specific accounts.',
        timeline:i=>'Show 12-month projection for '+i+'. Good path vs bad path side by side.',
        impact:i=>'What happens to '+i+'\'s score if they miss their next payment? Simulate and explain.',
        build:()=>'I have no credit history at all — zero score. Walk me through exactly how to build credit from scratch without getting rejected. What kind of card should I apply for first? Should I get a secured card? How do I avoid common mistakes that get people rejected? Give me a realistic month-by-month timeline to build a 670+ score.',
        rights:()=>'What are my rights if I find an error on my credit report? Walk me through FCRA dispute process.'};
    document.getElementById('msgInput').value=(a==='rights'||a==='build')?P[a]():P[a](id);sendMessage();
}

function cleanupChat(){
    hideThinking();
    const btn=document.getElementById('sendBtn');
    if(btn){btn.disabled=false;btn.innerHTML=sendSVG}
    document.getElementById('msgInput').value='';
    setAgents([]);
}
function goHome(){fetch('/reset',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:SID})});cleanupChat();showWelcome()}
function goBack(){cleanupChat();showPaths()}

/* ═══ AGENTS ═══ */
function setAgents(agents){
    ['ap-score','ap-action','ap-policy'].forEach(id=>document.getElementById(id).classList.remove('on'));
    if(!agents||!agents.length)return;
    agents.forEach(a=>{const l=a.toLowerCase();
        if(l.includes('score'))document.getElementById('ap-score').classList.add('on');
        if(l.includes('action'))document.getElementById('ap-action').classList.add('on');
        if(l.includes('policy'))document.getElementById('ap-policy').classList.add('on');
    });
}

/* ═══ MESSAGES ═══ */
function addMsg(role,html,agents,viz,trace){
    const w=document.getElementById('welcome');if(w)w.remove();
    showInput();showNav();
    const d=document.createElement('div');
    if(role==='user'){d.className='msg-user';d.innerHTML='<div class="msg-user-label">You</div><div class="msg-user-text">'+html+'</div>'}
    else{d.className='msg-ai';let tags='';
        if(agents&&agents.length)tags='<div class="msg-ai-agents">'+agents.map(a=>'<span class="tag '+(a.toLowerCase().includes('score')?'tag-blue':a.toLowerCase().includes('action')?'tag-green':'tag-purple')+'">'+esc(a)+'</span>').join('')+'</div>';
        const vid='v-'+(++cc);
        let traceHtml='';
        if(trace&&trace.length){
            const steps=trace.map(t=>{
                if(t.from) return `<span class="trace-step"><span class="trace-agent">${esc(t.from.replace('You are CreditCoach','ScoreSimulator'))}</span> <span class="trace-arrow">&#8594;</span> <span class="trace-agent">${esc(t.to)}</span></span>`;
                return `<span class="trace-step trace-tool">${esc(t.tool)}</span>`;
            }).join('');
            traceHtml=`<details class="agent-trace"><summary class="trace-toggle">Agent Reasoning Trace (${trace.length} step${trace.length>1?'s':''})</summary><div class="trace-flow">${steps}</div></details>`;
        }
        d.innerHTML='<div class="msg-ai-header"><div class="msg-ai-avatar">AI</div><div class="msg-ai-name">CreditCoach</div>'+tags+'</div>'+traceHtml+'<div class="msg-ai-body">'+html+'</div>'+(viz&&viz.length?'<div class="viz-wrap" id="'+vid+'"></div>':'')+buildFollowups()}
    inner.appendChild(d);chat.scrollTop=chat.scrollHeight;
    if(role==='assistant'&&viz&&viz.length){const vc=document.getElementById('v-'+cc);viz.forEach(v=>renderViz(v,vc));requestAnimationFrame(()=>{chat.scrollTop=chat.scrollHeight})}
}
function buildFollowups(){
    const id=lastMemberId;if(!id)return'';
    return`<div class="followups">
        <button class="followup" onclick="send('Show 12-month timeline for ${id}')">&#128200; Timeline</button>
        <button class="followup" onclick="send('Create action plan for ${id}')">&#128221; Action Plan</button>
        <button class="followup" onclick="send('What if ${id} pays down their highest card by $500?')">&#9888; Simulate</button>
        <button class="followup" onclick="send('Show transaction history for ${id}')">&#128196; Transactions</button>
        <button class="followup" onclick="send('What are my credit rights?')">&#9878; My Rights</button>
    </div>`;
}

/* ═══ THINKING ═══ */
function showThinking(){
    hideThinking();
    const d=document.createElement('div');d.className='msg-thinking';d.id='thinking';
    d.innerHTML='<div class="msg-ai-header"><div class="msg-ai-avatar">AI</div><div class="msg-ai-name">CreditCoach</div></div><div class="msg-thinking-inner"><div class="msg-thinking-dots"><span></span><span></span><span></span></div><div class="msg-thinking-label">Analyzing with multi-agent system...</div></div>';
    inner.appendChild(d);chat.scrollTop=chat.scrollHeight;
    document.getElementById('thinkingBar').innerHTML='<div class="thinking-bar"><div class="tdots"><span></span><span></span><span></span></div>Thinking...</div>';
    tt=setTimeout(()=>{hideThinking();addMsg('assistant','Taking longer than expected.');document.getElementById('sendBtn').disabled=false;document.getElementById('sendBtn').innerHTML=sendSVG},60000);
}
function hideThinking(){if(tt){clearTimeout(tt);tt=null}const e=document.getElementById('thinking');if(e)e.remove();document.getElementById('thinkingBar').innerHTML=''}

/* ═══ SEND ═══ */
function send(text){document.getElementById('msgInput').value=text;sendMessage()}
async function sendMessage(){
    const inp=document.getElementById('msgInput'),btn=document.getElementById('sendBtn');
    const msg=inp.value.trim();if(!msg||btn.disabled)return;
    const m=msg.match(/M\d{4}/i);if(m)lastMemberId=m[0].toUpperCase();
    addMsg('user',esc(msg));inp.value='';btn.disabled=true;btn.innerHTML='<span class="spinner"></span>';
    showThinking();document.querySelectorAll('.agent-pill').forEach(a=>a.classList.add('on'));
    try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,session_id:SID})});
        const data=await r.json();hideThinking();setAgents(data.agents_used);addMsg('assistant',md(data.reply),data.agents_used,data.visualizations,data.delegation_trace)}
    catch(e){hideThinking();setAgents([]);addMsg('assistant','Connection error.')}
    btn.disabled=false;btn.innerHTML=sendSVG;inp.focus();
}

/* ═══ VIZ ═══ */
function renderViz(v,c){if(!v||!v.data||v.data.error)return;try{({timeline:rTL,profile:rPR,health:rHL,action_plan:rAP,impact:rIM,rag_sources:rRAG,account_breakdown:rAB})[v.type]?.(v.data,c)}catch(e){console.error(e)}}
function rTL(d,c){const el=document.createElement('div');el.className='viz';const id='c'+(++cc),gp=d.good_path||{},bp=d.bad_path||{},cs=d.current_score||600;el.innerHTML='<h4><span class="viz-dot" style="background:var(--accent)"></span>Payment Impact Timeline</h4><canvas id="'+id+'" height="260"></canvas><div style="text-align:center;margin-top:10px;font-size:13px;color:var(--text3)">12-month gap: <strong style="color:var(--accent)">'+(d.difference_at_12mo||0)+' pts</strong></div>';c.appendChild(el);const all=[cs,gp['3mo']||cs,gp['6mo']||cs,gp['12mo']||cs,bp['3mo']||cs,bp['6mo']||cs,bp['12mo']||cs];new Chart(document.getElementById(id),{type:'line',data:{labels:['Now','3 mo','6 mo','12 mo'],datasets:[{label:'Good Path',data:[cs,gp['3mo'],gp['6mo'],gp['12mo']],borderColor:'#16a34a',backgroundColor:'rgba(22,163,74,.06)',fill:true,tension:.35,borderWidth:2.5,pointRadius:5,pointBackgroundColor:'#16a34a',pointBorderColor:'#fff',pointBorderWidth:2},{label:'Bad Path',data:[cs,bp['3mo'],bp['6mo'],bp['12mo']],borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.06)',fill:true,tension:.35,borderWidth:2.5,pointRadius:5,pointBackgroundColor:'#dc2626',pointBorderColor:'#fff',pointBorderWidth:2}]},options:{responsive:true,plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:16,font:{family:"'IBM Plex Sans'",size:12}}}},scales:{y:{min:Math.max(300,Math.min(...all)-40),max:Math.min(850,Math.max(...all)+40),grid:{color:'rgba(0,0,0,.04)'}},x:{grid:{display:false}}}}})}
function rPR(d,c){const el=document.createElement('div');el.className='viz';const gid='c'+(++cc),fid='c'+(++cc);const s=d.estimated_fico_score||0,pay=d.payment_history_ontime_pct||0,util=d.credit_utilization_pct||0,age=d.avg_account_age_months||0,mix=d.credit_mix||'',inq=d.hard_inquiries_last_12mo||0;const ps=pay,us=Math.max(0,Math.min(100,100-util*1.5)),as_=Math.min(100,age/1.2),ms=mix==='full_mix'?90:mix==='credit_card_and_loan'?65:35,is_=Math.max(0,100-inq*25);const vc=(v,g,b)=>v>=g?'good':v<=b?'bad':'warn';const scoreLabel=s===0?'N/A':s;const tierLabel=s===0?'no score yet':(d.credit_tier||'').replace(/_/g,' ');el.innerHTML='<h4><span class="viz-dot" style="background:var(--accent)"></span>Credit Profile — '+esc(d.member_name||'')+'</h4><div class="gauge-row"><div class="gauge-box"><div class="gauge-wrap"><canvas id="'+gid+'"></canvas><div class="gauge-num"'+(s===0?' style="font-size:22px;color:var(--text3)"':'')+'>'+scoreLabel+'</div></div><div class="gauge-tier">'+tierLabel+'</div></div><div class="stats-grid"><div class="stat"><div class="lbl">Payment</div><div class="val '+vc(pay,95,80)+'">'+pay+'%</div></div><div class="stat"><div class="lbl">Utilization</div><div class="val '+vc(100-util,70,50)+'">'+util+'%</div></div><div class="stat"><div class="lbl">Avg Age</div><div class="val">'+(age/12).toFixed(1)+'yr</div></div><div class="stat"><div class="lbl">Accounts</div><div class="val">'+(d.number_of_accounts||0)+'</div></div><div class="stat"><div class="lbl">Inquiries</div><div class="val '+vc(4-inq,2,0)+'">'+inq+'</div></div><div class="stat"><div class="lbl">Debt</div><div class="val">$'+(d.total_debt||0).toLocaleString()+'</div></div></div></div><div style="margin-top:16px"><h4><span class="viz-dot" style="background:var(--green)"></span>FICO Factors</h4><canvas id="'+fid+'" height="140"></canvas></div>';c.appendChild(el);const gc=s>=740?'#16a34a':s>=670?'#22c55e':s>=580?'#ca8a04':s>=500?'#ea580c':'#dc2626';new Chart(document.getElementById(gid),{type:'doughnut',data:{datasets:[{data:[s-300,850-s],backgroundColor:[gc,'#e5e5e5'],borderWidth:0}]},options:{rotation:-90,circumference:180,cutout:'78%',plugins:{legend:{display:false},tooltip:{enabled:false}},responsive:true,maintainAspectRatio:false}});const sc=[ps,us,as_,ms,is_],co=sc.map(v=>v>=70?'#16a34a':v>=40?'#ca8a04':'#dc2626');new Chart(document.getElementById(fid),{type:'bar',data:{labels:['Payment 35%','Utilization 30%','Age 15%','Mix 10%','Inquiries 10%'],datasets:[{data:sc,backgroundColor:co,borderRadius:4,barThickness:20}]},options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false}},scales:{x:{max:100,grid:{color:'rgba(0,0,0,.04)'}},y:{grid:{display:false}}}}})}
function rIM(d,c){const el=document.createElement('div');el.className='viz';const delta=d.point_change||0,cls=delta>=0?'pos':'neg',sign=delta>=0?'+':'';el.innerHTML='<h4><span class="viz-dot" style="background:'+(delta>=0?'var(--green)':'var(--red)')+'"></span>Score Impact</h4><div class="impact-row"><div class="impact-box before"><div class="num">'+(d.current_score||0)+'</div><div class="lbl">Current</div></div><div style="font-size:24px;color:#cbd5e1">&#8594;</div><div class="impact-box after-'+cls+'"><div class="num">'+(d.projected_score||0)+'</div><div class="lbl">Projected</div></div><div class="impact-delta '+cls+'">'+sign+delta+'</div></div><div style="text-align:center;margin-top:10px;font-size:13px;color:var(--text3)"><strong>'+esc(d.factor||'')+'</strong> — '+esc(d.explanation||'')+'</div>';c.appendChild(el)}
function rHL(d,c){const el=document.createElement('div');el.className='viz';const g=d.grade||'?';const gradeClass=g==='N/A'?'grade-NA':'grade-'+g;const scoreDisplay=d.score===0?'No Score':d.score;el.innerHTML='<h4><span class="viz-dot" style="background:var(--green)"></span>Health Checkup — '+esc(d.member_name||'')+'</h4><div class="health-row"><div style="text-align:center"><div class="grade-circle '+gradeClass+'">'+g+'</div><div style="margin-top:8px;font-size:20px;font-weight:700">'+scoreDisplay+'</div></div><div class="health-lists"><h5 style="color:var(--green)">Strengths</h5><ul>'+(d.strengths||[]).map(s=>'<li class="str">'+esc(s)+'</li>').join('')+'</ul><h5 style="color:var(--red)">Weaknesses</h5><ul>'+(d.weaknesses||[]).map(w=>'<li class="wk">'+esc(w)+'</li>').join('')+'</ul></div></div><div class="tip"><strong>Tip:</strong> '+esc(d.top_tip||'')+'</div>';c.appendChild(el)}
function rAP(d,c){const el=document.createElement('div');el.className='viz';el.innerHTML='<h4><span class="viz-dot" style="background:var(--green)"></span>Action Plan — '+esc(d.member_name||'')+' ('+(d.current_score||'?')+' &#8594; '+(d.target_score||'?')+')</h4><div class="plan-steps">'+(d.steps||[]).map((s,i)=>'<div class="step"><div class="step-n">'+(i+1)+'</div><div><div class="step-action">'+esc(s.action||'')+'<span class="step-impact">'+esc(s.impact||'')+'</span></div><div class="step-meta">'+esc(s.why||'')+'</div></div></div>').join('')+'</div>';c.appendChild(el)}
function rRAG(d,c){if(!d||!d.length)return;const el=document.createElement('div');el.className='viz';el.innerHTML='<h4><span class="viz-dot" style="background:var(--purple)"></span>RAG Sources</h4><div class="rag-sources">'+d.map(s=>'<div class="rag-src"><strong>'+esc(s.source||'')+'</strong> — '+esc(s.header||'')+'<span class="rel">'+((s.relevance||0)*100).toFixed(0)+'%</span></div>').join('')+'</div>';c.appendChild(el)}
function rAB(d,c){if(!d||!d.length)return;const el=document.createElement('div');el.className='viz';const id='c'+(++cc);el.innerHTML='<h4><span class="viz-dot" style="background:var(--orange)"></span>Per-Account Utilization</h4><canvas id="'+id+'" height="'+(60+d.length*40)+'"></canvas><div class="ab-legend">'+d.map(a=>'<div class="ab-item"><span class="ab-name">'+esc(a.name)+'</span><span class="ab-vals">$'+a.balance.toLocaleString()+' / $'+a.limit.toLocaleString()+' <strong class="'+(a.utilization>70?'bad':a.utilization>30?'warn':'good')+'">'+a.utilization+'%</strong></span></div>').join('')+'</div>';c.appendChild(el);const colors=d.map(a=>a.utilization>70?'#dc2626':a.utilization>30?'#ca8a04':'#16a34a');new Chart(document.getElementById(id),{type:'bar',data:{labels:d.map(a=>a.name),datasets:[{label:'Utilization %',data:d.map(a=>a.utilization),backgroundColor:colors,borderRadius:4,barThickness:24}]},options:{indexAxis:'y',responsive:true,plugins:{legend:{display:false},annotation:{}},scales:{x:{max:100,grid:{color:'rgba(0,0,0,.04)'},ticks:{callback:v=>v+'%'}},y:{grid:{display:false}}}}});
    // Draw 30% threshold line
    const ctx=document.getElementById(id).getContext('2d');const chart=Chart.getChart(id);if(chart){const xScale=chart.scales.x;const yScale=chart.scales.y;const x30=xScale.getPixelForValue(30);ctx.save();ctx.strokeStyle='#dc2626';ctx.lineWidth=1.5;ctx.setLineDash([6,4]);ctx.beginPath();ctx.moveTo(x30,yScale.top);ctx.lineTo(x30,yScale.bottom);ctx.stroke();ctx.fillStyle='#dc2626';ctx.font='11px IBM Plex Sans';ctx.fillText('30%',x30+4,yScale.top+12);ctx.restore()}}
