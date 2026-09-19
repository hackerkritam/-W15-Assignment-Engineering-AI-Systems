const messages = document.querySelector('#messages');
const form = document.querySelector('#chat-form');
const input = document.querySelector('#message');
const status = document.querySelector('#status');

function addMessage(text, role, sources = [], toolCalls = []) {
  const node = document.createElement('div'); node.className = `message ${role}`;
  const sourceHtml = sources.length ? `<div class="sources">${sources.map(s => `<strong>${s.title}</strong><br>${s.content.slice(0, 220)}${s.content.length > 220 ? '...' : ''}`).join('<hr>')}</div>` : '';
  const tools = toolCalls.length ? `<small>Tools: ${toolCalls.join(', ')}</small>` : '';
  node.innerHTML = role === 'assistant' ? `<span class="avatar">CP</span><div><p>${text.replaceAll('<','&lt;')}</p>${sourceHtml}${tools}</div>` : `<div><p>${text.replaceAll('<','&lt;')}</p></div>`;
  messages.appendChild(node); node.scrollIntoView({behavior:'smooth'});
}
form.addEventListener('submit', async (event) => { event.preventDefault(); const text = input.value.trim(); if (!text) return; addMessage(text, 'user'); input.value = ''; status.textContent = 'thinking...'; try { const response = await fetch('/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:text})}); const data = await response.json(); if (!response.ok) throw new Error(data.detail || 'Request failed'); addMessage(data.answer, 'assistant', data.sources, data.tool_calls); } catch (error) { addMessage(error.message, 'assistant'); } finally { status.textContent = 'online'; } });
document.querySelector('#ingest-form').addEventListener('submit', async (event) => { event.preventDefault(); const title = document.querySelector('#title').value; const content = document.querySelector('#content').value; const response = await fetch('/ingest', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,content})}); if (response.ok) { event.target.reset(); alert('Document indexed.'); } });
fetch('/health').then(r=>r.json()).then(data=>status.textContent = data.status === 'ok' ? 'online' : 'degraded').catch(()=>status.textContent='offline');
